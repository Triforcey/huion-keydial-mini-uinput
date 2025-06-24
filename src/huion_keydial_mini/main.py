"""Main entry point for the Huion Keydial Mini driver."""

import asyncio
import logging
import signal
import sys
from typing import Optional

import click

from .device import HuionKeydialMini
from .config import Config


logger = logging.getLogger(__name__)


class DriverManager:
    """Manages the driver lifecycle."""

    def __init__(self, config: Config):
        self.config = config
        self.device: Optional[HuionKeydialMini] = None
        self.running = False

    async def start(self):
        """Start the driver."""
        logger.info("Starting Huion Keydial Mini driver...")

        try:
            # Initialize the device
            self.device = HuionKeydialMini(self.config)

            # Set up signal handlers
            loop = asyncio.get_event_loop()
            for sig in [signal.SIGINT, signal.SIGTERM]:
                loop.add_signal_handler(sig, self._signal_handler)

            # Start the device
            await self.device.start()
            self.running = True

            logger.info("Driver started successfully")

            # Keep the driver running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Failed to start driver: {e}")
            raise
        finally:
            await self.stop()

    def _signal_handler(self):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self.running = False

    async def stop(self):
        """Stop the driver."""
        logger.info("Stopping driver...")

        if self.device:
            await self.device.stop()
            self.device = None

        logger.info("Driver stopped")


@click.command()
@click.option('--config', '-c',
              type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--device-address', '-d',
              help='Bluetooth MAC address of the device')
@click.option('--log-level', '-l',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              default='INFO',
              help='Set the logging level')
@click.option('--scan', '-s',
              is_flag=True,
              help='Scan for available Huion devices')
def main(config: Optional[str], device_address: Optional[str], log_level: str, scan: bool):
    """Huion Keydial Mini driver main entry point."""

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # Load configuration
        app_config = Config.load(config, device_address)

        if scan:
            # Run device scan
            asyncio.run(scan_devices())
            return

        # Start the driver
        manager = DriverManager(app_config)
        asyncio.run(manager.start())

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Driver failed: {e}")
        sys.exit(1)


async def scan_devices():
    """Scan for available Huion devices."""
    from .scanner import DeviceScanner

    logger.info("Scanning for Huion devices...")
    # Enable debug mode to see all discovered devices
    scanner = DeviceScanner(debug_mode=True)
    devices = await scanner.scan()

    if devices:
        click.echo("Found Huion devices:")
        for device in devices:
            click.echo(f"  {device.address} - {device.name}")
    else:
        click.echo("No Huion devices found")
        click.echo("Check the debug output above to see all discovered devices")


async def run_driver_with_logger(event_logger, show_raw: bool = False, auto_connect: bool = True):
    """Run the driver with a custom event logger."""
    from .device import HuionKeydialMini

    # Set up clean logging
    logging.getLogger('bleak').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('dbus_fast').setLevel(logging.WARNING)

    try:
        # Initialize the device
        device = HuionKeydialMini(event_logger.config)

        # Override the device's notification handler to use our logger
        original_handler = device._handle_notification

        async def custom_notification_handler(sender, data: bytearray):
            if show_raw:
                event_logger.log_raw_data(data)
            event_logger.log_parser_events(data, characteristic_uuid=str(sender))
            # Still call the original handler for uinput events
            await original_handler(sender, data)

        device._handle_notification = custom_notification_handler

        # Start the device (includes connection)
        await device.start()

        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await device.stop()

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == '__main__':
    main()
