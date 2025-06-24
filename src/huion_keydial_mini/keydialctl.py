"""Command-line utility for managing Huion Keydial Mini configuration."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import click
import yaml

from .config import Config
from .scanner import DeviceScanner
from .uinput_handler import UInputHandler


logger = logging.getLogger(__name__)


@click.group()
@click.option('--config', '-c',
              type=click.Path(),
              help='Path to configuration file')
@click.pass_context
def cli(ctx, config: Optional[str]):
    """Huion Keydial Mini configuration utility."""
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config


@cli.command()
@click.pass_context
def scan(ctx):
    """Scan for available Huion devices."""
    click.echo("Scanning for Huion devices...")

    async def do_scan():
        scanner = DeviceScanner()
        devices = await scanner.scan()

        if devices:
            click.echo("Found devices:")
            for device in devices:
                click.echo(f"  {device.address} - {device.name} (RSSI: {device.rssi})")
        else:
            click.echo("No Huion devices found")

    asyncio.run(do_scan())


@cli.command()
@click.argument('button', type=click.Choice([
    'button_1', 'button_2', 'button_3', 'button_4',
    'button_5', 'button_6', 'button_7', 'button_8'
]))
@click.argument('key')
@click.pass_context
def bind(ctx, button: str, key: str):
    """Bind a button to a key.

    BUTTON: Button identifier (button_1 through button_8)
    KEY: Key code (e.g., KEY_F1, KEY_VOLUMEUP, KEY_CTRL+KEY_C)
    """
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)

    # Validate key code
    uinput = UInputHandler(config)
    supported_keys = uinput.get_supported_keys()

    # Handle key combinations
    keys = [k.strip() for k in key.split('+')]
    for k in keys:
        if k not in supported_keys:
            click.echo(f"Error: Unsupported key '{k}'", err=True)
            click.echo(f"Supported keys: {', '.join(sorted(supported_keys))}")
            sys.exit(1)

    # Update configuration
    config.data['key_mappings'][button] = key

    # Save configuration
    config_file = _get_config_file(config_path)
    config.save(str(config_file))

    click.echo(f"Bound {button} to {key}")
    click.echo(f"Configuration saved to: {config_file}")


@cli.command()
@click.argument('button', type=click.Choice([
    'button_1', 'button_2', 'button_3', 'button_4',
    'button_5', 'button_6', 'button_7', 'button_8'
]))
@click.pass_context
def unbind(ctx, button: str):
    """Remove binding for a button.

    BUTTON: Button identifier (button_1 through button_8)
    """
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)

    if button in config.data['key_mappings']:
        old_binding = config.data['key_mappings'][button]
        del config.data['key_mappings'][button]

        # Save configuration
        config_file = _get_config_file(config_path)
        config.save(str(config_file))

        click.echo(f"Removed binding for {button} (was: {old_binding})")
        click.echo(f"Configuration saved to: {config_file}")
    else:
        click.echo(f"No binding found for {button}")


@cli.command()
@click.option('--clockwise', help='Key for clockwise rotation')
@click.option('--counterclockwise', help='Key for counterclockwise rotation')
@click.option('--click', help='Key for dial click')
@click.option('--sensitivity', type=float, help='Dial sensitivity (default: 1.0)')
@click.pass_context
def dial(ctx, clockwise: Optional[str], counterclockwise: Optional[str],
         click_key: Optional[str], sensitivity: Optional[float]):
    """Configure dial settings."""
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)

    # Validate keys
    uinput = UInputHandler(config)
    supported_keys = uinput.get_supported_keys()

    updates = {}

    if clockwise:
        if clockwise not in supported_keys:
            click.echo(f"Error: Unsupported key '{clockwise}'", err=True)
            sys.exit(1)
        updates['clockwise_key'] = clockwise

    if counterclockwise:
        if counterclockwise not in supported_keys:
            click.echo(f"Error: Unsupported key '{counterclockwise}'", err=True)
            sys.exit(1)
        updates['counterclockwise_key'] = counterclockwise

    if click_key:
        if click_key not in supported_keys:
            click.echo(f"Error: Unsupported key '{click_key}'", err=True)
            sys.exit(1)
        updates['click_key'] = click_key

    if sensitivity is not None:
        if sensitivity <= 0:
            click.echo("Error: Sensitivity must be positive", err=True)
            sys.exit(1)
        updates['sensitivity'] = sensitivity

    if not updates:
        click.echo("No changes specified")
        return

    # Update configuration
    config.data['dial_settings'].update(updates)

    # Save configuration
    config_file = _get_config_file(config_path)
    config.save(str(config_file))

    click.echo("Dial settings updated:")
    for key, value in updates.items():
        click.echo(f"  {key}: {value}")
    click.echo(f"Configuration saved to: {config_file}")


@cli.command()
@click.pass_context
def list_bindings(ctx):
    """List current key bindings."""
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)

    click.echo("Current key bindings:")
    click.echo()

    # Button mappings
    click.echo("Buttons:")
    for button in ['button_1', 'button_2', 'button_3', 'button_4',
                   'button_5', 'button_6', 'button_7', 'button_8']:
        key = config.key_mappings.get(button, 'unbound')
        click.echo(f"  {button}: {key}")

    click.echo()

    # Dial settings
    click.echo("Dial:")
    dial_settings = config.dial_settings
    click.echo(f"  clockwise: {dial_settings.get('clockwise_key', 'unset')}")
    click.echo(f"  counterclockwise: {dial_settings.get('counterclockwise_key', 'unset')}")
    click.echo(f"  click: {dial_settings.get('click_key', 'unset')}")
    click.echo(f"  sensitivity: {dial_settings.get('sensitivity', 1.0)}")


@cli.command()
@click.pass_context
def list_keys(ctx):
    """List available key codes."""
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)

    uinput = UInputHandler(config)
    keys = sorted(uinput.get_supported_keys())

    click.echo("Available key codes:")
    click.echo()

    # Group keys by category
    categories = {
        'Function Keys': [k for k in keys if k.startswith('KEY_F')],
        'Volume/Media': [k for k in keys if any(x in k for x in ['VOLUME', 'PLAY', 'MUTE', 'SONG'])],
        'Navigation': [k for k in keys if any(x in k for x in ['UP', 'DOWN', 'LEFT', 'RIGHT', 'HOME', 'END', 'PAGE'])],
        'Modifiers': [k for k in keys if any(x in k for x in ['CTRL', 'SHIFT', 'ALT', 'META'])],
        'Other': [k for k in keys if not any(cat in k for cat in ['F', 'VOLUME', 'PLAY', 'MUTE', 'SONG', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'HOME', 'END', 'PAGE', 'CTRL', 'SHIFT', 'ALT', 'META'])]
    }

    for category, category_keys in categories.items():
        if category_keys:
            click.echo(f"{category}:")
            for i, key in enumerate(category_keys):
                if i % 3 == 0:
                    click.echo("  ", nl=False)
                click.echo(f"{key:<20}", nl=False)
                if (i + 1) % 3 == 0:
                    click.echo()
            if len(category_keys) % 3 != 0:
                click.echo()
            click.echo()


@cli.command()
@click.argument('device_address')
@click.pass_context
def set_device(ctx, device_address: str):
    """Set the device address to connect to.

    DEVICE_ADDRESS: Bluetooth MAC address (e.g., AA:BB:CC:DD:EE:FF)
    """
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)

    # Validate MAC address format
    import re
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    if not mac_pattern.match(device_address):
        click.echo("Error: Invalid MAC address format. Use AA:BB:CC:DD:EE:FF", err=True)
        sys.exit(1)

    # Update configuration
    config.data['device']['address'] = device_address.upper()

    # Save configuration
    config_file = _get_config_file(config_path)
    config.save(str(config_file))

    click.echo(f"Device address set to: {device_address.upper()}")
    click.echo(f"Configuration saved to: {config_file}")


@cli.command()
@click.pass_context
def clear_device(ctx):
    """Clear the device address (auto-discover mode)."""
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)

    # Update configuration
    config.data['device']['address'] = None

    # Save configuration
    config_file = _get_config_file(config_path)
    config.save(str(config_file))

    click.echo("Device address cleared (will auto-discover)")
    click.echo(f"Configuration saved to: {config_file}")


@cli.command()
@click.pass_context
def reset(ctx):
    """Reset configuration to defaults."""
    if not click.confirm("This will reset all configuration to defaults. Continue?"):
        click.echo("Cancelled")
        return

    config_path = ctx.obj.get('config_path')
    config_file = _get_config_file(config_path)

    # Create default configuration
    default_config = Config._get_default_config()

    # Save default configuration
    with open(config_file, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)

    click.echo("Configuration reset to defaults")
    click.echo(f"Configuration saved to: {config_file}")


def _load_config(config_path: Optional[str]) -> Config:
    """Load configuration from file."""
    try:
        return Config.load(config_path)
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)


def _get_config_file(config_path: Optional[str]) -> Path:
    """Get the configuration file path."""
    if config_path:
        return Path(config_path)

    # Use default locations
    candidates = [
        Path.cwd() / 'config.yaml',
        Path.home() / '.config' / 'huion-keydial-mini' / 'config.yaml',
        Path('/etc/huion-keydial-mini/config.yaml'),
    ]

    # Find existing config or use the user config location
    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Use user config location as default
    user_config = Path.home() / '.config' / 'huion-keydial-mini' / 'config.yaml'
    user_config.parent.mkdir(parents=True, exist_ok=True)
    return user_config


if __name__ == '__main__':
    cli()
