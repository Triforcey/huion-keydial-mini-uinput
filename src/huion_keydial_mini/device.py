"""Main device driver for Huion Keydial Mini."""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any
import struct

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from .config import Config
from .uinput_handler import UInputHandler
from .hid_parser import HIDParser


logger = logging.getLogger(__name__)


class HuionKeydialMini:
    """Main driver class for the Huion Keydial Mini device."""

    # HID over GATT service and characteristic UUIDs (these may need to be discovered)
    HID_SERVICE_UUID = "00001812-0000-1000-8000-00805f9b34fb"  # Standard HID service
    HID_REPORT_CHAR_UUID = "00002a4d-0000-1000-8000-00805f9b34fb"  # HID Report characteristic

    def __init__(self, config: Config):
        self.config = config
        self.client: Optional[BleakClient] = None
        self.device: Optional[BLEDevice] = None
        self.uinput_handler: Optional[UInputHandler] = None
        self.hid_parser: Optional[HIDParser] = None
        self.connected = False
        self.running = False

    async def start(self):
        """Start the device driver."""
        logger.info("Starting Huion Keydial Mini driver...")

        try:
            # Find the device
            await self._find_device()

            # Initialize components
            self.uinput_handler = UInputHandler(self.config)
            self.hid_parser = HIDParser(self.config)

            # Create uinput device
            await self.uinput_handler.create_device()

            # Connect to the device
            await self._connect()

            # Start listening for data
            await self._start_notifications()

            self.running = True
            logger.info("Driver started successfully")

        except Exception as e:
            logger.error(f"Failed to start driver: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the device driver."""
        logger.info("Stopping driver...")

        self.running = False

        if self.client and self.connected:
            try:
                await self.client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")

        if self.uinput_handler:
            await self.uinput_handler.destroy_device()

        self.connected = False
        logger.info("Driver stopped")

    async def _find_device(self):
        """Find the target device."""
        logger.info("Searching for device...")

        if self.config.device_address:
            # Try to connect to specific address
            logger.info(f"Looking for device at {self.config.device_address}")
            devices = await BleakScanner.discover(timeout=self.config.scan_timeout)

            for device in devices:
                if device.address.lower() == self.config.device_address.lower():
                    self.device = device
                    logger.info(f"Found device: {device.address} - {device.name}")
                    return

            raise RuntimeError(f"Device {self.config.device_address} not found")

        else:
            # Scan for Huion devices
            from .scanner import DeviceScanner
            scanner = DeviceScanner(self.config.scan_timeout)
            devices = await scanner.scan()

            if not devices:
                raise RuntimeError("No Huion devices found")

            # Use the first device found
            target = devices[0]
            logger.info(f"Using device: {target.address} - {target.name}")

            # Get the BLEDevice object
            discovered = await BleakScanner.discover(timeout=5.0)
            for device in discovered:
                if device.address == target.address:
                    self.device = device
                    break

            if not self.device:
                raise RuntimeError(f"Could not get device object for {target.address}")

    async def _connect(self):
        """Connect to the device."""
        if not self.device:
            raise RuntimeError("No device to connect to")

        logger.info(f"Connecting to {self.device.address}...")

        self.client = BleakClient(
            self.device,
            timeout=self.config.connection_timeout
        )

        try:
            await self.client.connect()
            self.connected = True
            logger.info("Connected successfully")

            # Log available services and characteristics
            await self._log_services()

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise

    async def _log_services(self):
        """Log available services and characteristics."""
        if not self.client:
            return

        logger.debug("Available services:")
        for service in self.client.services:
            logger.debug(f"  Service: {service.uuid}")
            for char in service.characteristics:
                logger.debug(f"    Characteristic: {char.uuid} - {char.properties}")

    async def _start_notifications(self):
        """Start listening for HID notifications."""
        if not self.client:
            raise RuntimeError("Not connected")

        logger.info("Starting HID notifications...")

        try:
            # Find HID report characteristic
            hid_char = None
            for service in self.client.services:
                for char in service.characteristics:
                    # Look for HID report characteristic or notification-capable chars
                    if "notify" in char.properties:
                        logger.debug(f"Found notification characteristic: {char.uuid}")
                        hid_char = char
                        break
                if hid_char:
                    break

            if not hid_char:
                # Fallback: try the standard HID report characteristic
                try:
                    hid_char = self.client.services.get_characteristic(self.HID_REPORT_CHAR_UUID)
                except Exception:
                    pass

            if not hid_char:
                raise RuntimeError("Could not find HID report characteristic")

            logger.info(f"Using characteristic: {hid_char.uuid}")

            # Start notifications
            await self.client.start_notify(hid_char, self._handle_notification)
            logger.info("Notifications started")

        except Exception as e:
            logger.error(f"Failed to start notifications: {e}")
            raise

    async def _handle_notification(self, sender, data: bytearray):
        """Handle incoming HID data."""
        try:
            logger.debug(f"Received data: {data.hex()}")

            # Parse HID data
            if self.hid_parser:
                events = self.hid_parser.parse(data)

                # Send events to uinput
                if self.uinput_handler:
                    for event in events:
                        await self.uinput_handler.send_event(event)

        except Exception as e:
            logger.error(f"Error handling notification: {e}")
