"""Command-line utility for managing Huion Keydial Mini configuration."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import click
import yaml

from .config import Config
from .uinput_handler import UInputHandler
from .keybind_manager import send_command, KeybindAction, EventType


logger = logging.getLogger(__name__)


def get_socket_path() -> str:
    """Get the default socket path for the user-level service."""
    socket_dir = Path.home() / ".local" / "share" / "huion-keydial-mini"
    return str(socket_dir / "control.sock")


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
@click.argument('action_id', type=click.Choice([
    'BUTTON_1', 'BUTTON_2', 'BUTTON_3', 'BUTTON_4',
    'BUTTON_5', 'BUTTON_6', 'BUTTON_7', 'BUTTON_8',
    'DIAL_CW', 'DIAL_CCW', 'DIAL_CLICK'
]))
@click.argument('key_data')
@click.pass_context
def bind(ctx, action_id: str, key_data: str):
    """Bind a keyboard action to a button or dial event.

    ACTION_ID: Action identifier (BUTTON_1-8, DIAL_CW, DIAL_CCW, DIAL_CLICK)
    KEY_DATA: Key data (e.g., "KEY_F1", "KEY_CTRL+KEY_C")

    Note: You can also configure actions in the config file using the new format:

    BUTTON_1:
      type: "keyboard"
      keys: ["KEY_F1"]
      description: "Button 1 -> F1"

    BUTTON_2:
      type: "keyboard"
      keys: ["KEY_LEFTCTRL", "KEY_C"]
      description: "Button 2 -> Copy"
    """
    async def do_bind():
        socket_path = get_socket_path()

        # Parse key data
        keys = [k.strip() for k in key_data.split('+')]
        action = {
            'type': 'keyboard',
            'keys': keys,
            'description': f"{action_id} -> {key_data}"
        }

        command = {
            'command': 'set_binding',
            'action_id': action_id,
            'action': action
        }

        response = await send_command(socket_path, command)

        if response['status'] == 'success':
            click.echo(f"Bound {action_id} to {key_data}")
        else:
            click.echo(f"Error: {response['message']}", err=True)
            sys.exit(1)

    asyncio.run(do_bind())


@cli.command()
@click.argument('action_id', type=click.Choice([
    'BUTTON_1', 'BUTTON_2', 'BUTTON_3', 'BUTTON_4',
    'BUTTON_5', 'BUTTON_6', 'BUTTON_7', 'BUTTON_8',
    'BUTTON_9', 'BUTTON_10', 'BUTTON_11', 'BUTTON_12',
    'BUTTON_13', 'BUTTON_14', 'BUTTON_15', 'BUTTON_16',
    'BUTTON_17', 'BUTTON_18',
    'DIAL_CW', 'DIAL_CCW', 'DIAL_CLICK'
]))
@click.pass_context
def unbind(ctx, action_id: str):
    """Remove binding for an action.

    ACTION_ID: Action identifier (BUTTON_1-8, dial_clockwise, etc.)
    """
    async def do_unbind():
        socket_path = get_socket_path()

        command = {
            'command': 'remove_binding',
            'action_id': action_id
        }

        response = await send_command(socket_path, command)

        if response['status'] == 'success':
            click.echo(f"Removed binding for {action_id}")
        else:
            click.echo(f"Error: {response['message']}", err=True)
            sys.exit(1)

    asyncio.run(do_unbind())


@cli.command()
@click.pass_context
def list_bindings(ctx):
    """List current key bindings."""
    async def do_list():
        socket_path = get_socket_path()

        command = {
            'command': 'get_bindings'
        }

        response = await send_command(socket_path, command)

        if response['status'] == 'success':
            bindings = response['bindings']

            if not bindings:
                click.echo("No bindings configured")
                return

            click.echo("Current bindings:")
            click.echo()

            for action_id, action_data in bindings.items():
                action_type = action_data['type']
                description = action_data.get('description', 'No description')

                if action_type == 'keyboard':
                    keys = '+'.join(action_data['keys']) if action_data['keys'] else 'none'
                    click.echo(f"  {action_id}: {keys} ({action_type})")
                elif action_type == 'mouse':
                    if action_data['mouse_action'] == 'scroll':
                        click.echo(f"  {action_id}: mouse scroll ({action_type})")
                    elif action_data['mouse_action'] == 'click':
                        button = action_data['mouse_button']
                        click.echo(f"  {action_id}: {button} click ({action_type})")
                else:
                    click.echo(f"  {action_id}: {description} ({action_type})")
        else:
            # Fallback to config file if service is not running
            click.echo(f"Service not running: {response['message']}")
            click.echo("Showing bindings from config file:")
            click.echo()

            config_path = ctx.obj.get('config_path')
            config = _load_config(config_path)

            # Show button mappings
            for button in ['BUTTON_1', 'BUTTON_2', 'BUTTON_3', 'BUTTON_4',
                          'BUTTON_5', 'BUTTON_6', 'BUTTON_7', 'BUTTON_8']:
                key = config.key_mappings.get(button, 'unbound')
                click.echo(f"  {button}: {key}")

            # Show dial settings
            dial_settings = config.dial_settings
            click.echo(f"  DIAL_CW: {dial_settings.get('DIAL_CW', 'unset')}")
            click.echo(f"  DIAL_CCW: {dial_settings.get('DIAL_CCW', 'unset')}")
            click.echo(f"  DIAL_CLICK: {dial_settings.get('DIAL_CLICK', 'unset')}")

            click.echo()
            click.echo("Note: Start the service to use runtime keybind management")

    asyncio.run(do_list())


@cli.command()
@click.pass_context
def list_keys(ctx):
    """List supported key codes."""
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)
    uinput = UInputHandler(config)
    supported_keys = uinput.get_supported_keys()

    click.echo("Supported key codes:")
    click.echo()

    # Group keys by category
    function_keys = [k for k in supported_keys if k.startswith('KEY_F')]
    modifier_keys = [k for k in supported_keys if 'CTRL' in k or 'SHIFT' in k or 'ALT' in k or 'META' in k]
    navigation_keys = [k for k in supported_keys if k in ['KEY_UP', 'KEY_DOWN', 'KEY_LEFT', 'KEY_RIGHT', 'KEY_HOME', 'KEY_END', 'KEY_PAGEUP', 'KEY_PAGEDOWN']]
    media_keys = [k for k in supported_keys if k in ['KEY_VOLUMEUP', 'KEY_VOLUMEDOWN', 'KEY_MUTE', 'KEY_PLAYPAUSE', 'KEY_NEXTSONG', 'KEY_PREVIOUSSONG']]
    letter_keys = [k for k in supported_keys if len(k) == 4 and k.startswith('KEY_') and k[4:].isalpha()]
    number_keys = [k for k in supported_keys if len(k) == 4 and k.startswith('KEY_') and k[4:].isdigit()]
    other_keys = [k for k in supported_keys if k not in function_keys + modifier_keys + navigation_keys + media_keys + letter_keys + number_keys]

    if function_keys:
        click.echo("Function keys:")
        for key in sorted(function_keys):
            click.echo(f"  {key}")
        click.echo()

    if modifier_keys:
        click.echo("Modifier keys:")
        for key in sorted(modifier_keys):
            click.echo(f"  {key}")
        click.echo()

    if navigation_keys:
        click.echo("Navigation keys:")
        for key in sorted(navigation_keys):
            click.echo(f"  {key}")
        click.echo()

    if media_keys:
        click.echo("Media keys:")
        for key in sorted(media_keys):
            click.echo(f"  {key}")
        click.echo()

    if letter_keys:
        click.echo("Letter keys:")
        for key in sorted(letter_keys):
            click.echo(f"  {key}")
        click.echo()

    if number_keys:
        click.echo("Number keys:")
        for key in sorted(number_keys):
            click.echo(f"  {key}")
        click.echo()

    if other_keys:
        click.echo("Other keys:")
        for key in sorted(other_keys):
            click.echo(f"  {key}")


@cli.command()
@click.argument('device_address')
@click.pass_context
def set_device(ctx, device_address: str):
    """Set the device address in configuration."""
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)

    # Validate device address format
    if not device_address or len(device_address) != 17:
        click.echo("Error: Invalid device address format", err=True)
        click.echo("Expected format: XX:XX:XX:XX:XX:XX")
        sys.exit(1)

    # Update configuration
    config.data['device_address'] = device_address

    # Save configuration
    config_file = _get_config_file(config_path)
    config.save(str(config_file))

    click.echo(f"Device address set to: {device_address}")
    click.echo(f"Configuration saved to: {config_file}")


@cli.command()
@click.pass_context
def clear_device(ctx):
    """Clear the device address from configuration."""
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)

    if 'device_address' in config.data:
        old_address = config.data['device_address']
        del config.data['device_address']

        # Save configuration
        config_file = _get_config_file(config_path)
        config.save(str(config_file))

        click.echo(f"Cleared device address (was: {old_address})")
        click.echo(f"Configuration saved to: {config_file}")
    else:
        click.echo("No device address configured")


@cli.command()
@click.pass_context
def reset(ctx):
    """Reset configuration to defaults."""
    config_path = ctx.obj.get('config_path')
    config = _load_config(config_path)

    # Create default configuration
    default_config = {
        'device_address': None,
        'key_mappings': {},
        'dial_settings': {
            'clockwise_key': 'KEY_VOLUMEUP',
            'counterclockwise_key': 'KEY_VOLUMEDOWN',
            'click_key': 'KEY_MUTE',
            'sensitivity': 1.0
        },
        'uinput_device_name': 'Huion Keydial Mini',
        'connection_timeout': 10.0,
        'debug_mode': False
    }

    config.data = default_config

    # Save configuration
    config_file = _get_config_file(config_path)
    config.save(str(config_file))

    click.echo("Configuration reset to defaults")
    click.echo(f"Configuration saved to: {config_file}")


def _load_config(config_path: Optional[str]) -> Config:
    """Load configuration from file."""
    return Config.load(config_path)


def _get_config_file(config_path: Optional[str]) -> Path:
    """Get configuration file path."""
    if config_path:
        return Path(config_path)
    else:
        return Path.home() / '.config' / 'huion-keydial-mini' / 'config.yaml'


if __name__ == '__main__':
    cli()
