"""Main device driver for Huion Keydial Mini."""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List
import struct

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.characteristic import BleakGATTCharacteristic

from .config import Config
from .uinput_handler import UInputHandler
from .hid_parser import HIDParser
from .scanner import DeviceScanner


logger = logging.getLogger(__name__)


class HuionKeydialMini:
    """Main driver class for the Huion Keydial Mini device."""

    # HID over GATT service and characteristic UUIDs
    HID_SERVICE_UUID = "00001812-0000-1000-8000-00805f9b34fb"  # Standard HID service
    HID_REPORT_CHAR_UUID = "00002a4d-0000-1000-8000-00805f9b34fb"  # HID Report characteristic
    HID_REPORT_MAP_UUID = "00002a4b-0000-1000-8000-00805f9b34fb"  # HID Report Map
    HID_CONTROL_POINT_UUID = "00002a4c-0000-1000-8000-00805f9b34fb"  # HID Control Point

    # Alternative HID service UUIDs (some devices use different ones)
    ALTERNATIVE_HID_SERVICES = [
        "00001812-0000-1000-8000-00805f9b34fb",  # Standard HID
        "0000ff00-0000-1000-8000-00805f9b34fb",  # Some custom HID services
    ]

    def __init__(self, config: Config):
        self.config = config
        self.device: Optional[BLEDevice] = None
        self.device_info = None
        self.client: Optional[BleakClient] = None
        self.connected = False
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.debug_mode = getattr(config, 'debug_mode', False)

        # Initialize components
        self.hid_parser = HIDParser(config)
        self.uinput_handler = UInputHandler(config)

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
            await self._connect_with_retry()

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
        """Find and connect to the Huion device."""
        if self.config.device_address:
            # Use specific device address
            logger.info(f"Looking for device: {self.config.device_address}")
            scanner = DeviceScanner(debug_mode=self.debug_mode)
            target = await scanner.scan_specific_device(self.config.device_address)

            if not target:
                raise RuntimeError(f"Device {self.config.device_address} not found or not paired")
        else:
            # Scan for available devices
            logger.info("Searching for device...")
            scanner = DeviceScanner(debug_mode=self.debug_mode)
            devices = await scanner.scan()

            if not devices:
                raise RuntimeError("No Huion devices found")

            # Use the first device found
            target = devices[0]
            logger.info(f"Using device: {target.address} - {target.name}")

        # Store the discovered device info
        self.device_info = target
        logger.info(f"Found device: {target.address} - {target.name}")

    async def _connect_with_retry(self):
        """Connect to the device with retry logic."""
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                await self._connect()
                self.reconnect_attempts = 0  # Reset on successful connection
                return
            except Exception as e:
                self.reconnect_attempts += 1
                logger.warning(f"Connection attempt {self.reconnect_attempts} failed: {e}")

                if self.reconnect_attempts < self.max_reconnect_attempts:
                    wait_time = min(2 ** self.reconnect_attempts, 30)  # Exponential backoff, max 30s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max reconnection attempts reached")
                    raise

    async def _connect(self):
        """Connect to the device."""
        if not self.device_info:
            raise RuntimeError("No device to connect to")

        logger.info(f"Connecting to {self.device_info.address}...")

        self.client = BleakClient(
            self.device_info.address,
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
            self.connected = False
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
            # Find all notification-capable characteristics
            notification_chars = await self._find_notification_characteristics()

            if not notification_chars:
                raise RuntimeError("Could not find any notification characteristics")

            logger.info(f"Found {len(notification_chars)} notification characteristics")

            # Start notifications for all characteristics
            for char in notification_chars:
                await self.client.start_notify(char, self._handle_notification)
                logger.info(f"Started notifications for characteristic: {char.uuid}")

        except Exception as e:
            logger.error(f"Failed to start notifications: {e}")
            raise

    async def _find_notification_characteristics(self) -> List[BleakGATTCharacteristic]:
        """Find all notification-capable characteristics."""
        if not self.client:
            return []

        notification_chars = []

        for service in self.client.services:
            for char in service.characteristics:
                if "notify" in char.properties:
                    notification_chars.append(char)
                    logger.debug(f"Found notification characteristic: {char.uuid} in service {service.uuid}")

        return notification_chars

    async def _find_hid_characteristic(self) -> Optional[BleakGATTCharacteristic]:
        """Find the appropriate HID characteristic for notifications."""
        # This method is kept for backward compatibility but now delegates to _find_notification_characteristics
        chars = await self._find_notification_characteristics()
        return chars[0] if chars else None

    async def _handle_notification(self, sender, data: bytearray):
        """Handle incoming HID data."""
        try:
            if self.debug_mode:
                logger.debug(f"Received data from {sender}: {data.hex()}")

            # Parse HID data with characteristic information
            if self.hid_parser:
                events = self.hid_parser.parse(data, characteristic_uuid=str(sender))

                # Send events to uinput
                if self.uinput_handler:
                    for event in events:
                        await self.uinput_handler.send_event(event)

        except Exception as e:
            logger.error(f"Error handling notification: {e}")
            if self.debug_mode:
                import traceback
                logger.debug(traceback.format_exc())

    async def get_device_info(self) -> Dict[str, Any]:
        """Get information about the connected device."""
        if not self.device_info:
            return {}

        info = {
            'address': self.device_info.address,
            'name': self.device_info.name,
            'connected': self.connected,
            'running': self.running,
        }

        if self.client and self.connected:
            try:
                info['services'] = [service.uuid for service in self.client.services]
                info['characteristics'] = []

                for service in self.client.services:
                    for char in service.characteristics:
                        info['characteristics'].append({
                            'uuid': char.uuid,
                            'properties': list(char.properties),
                            'service': service.uuid
                        })
            except Exception as e:
                logger.warning(f"Error getting device info: {e}")

        return info

    async def reconnect(self):
        """Manually trigger a reconnection."""
        logger.info("Manual reconnection requested")

        if self.client and self.connected:
            try:
                await self.client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")

        self.connected = False
        self.reconnect_attempts = 0

        await self._connect_with_retry()
        await self._start_notifications()

    async def start_with_existing_connection(self):
        """Start the device driver assuming the device is already connected."""
        logger.info("Starting Huion Keydial Mini driver with existing connection...")

        try:
            # Find the device
            await self._find_device()

            # Initialize components
            self.uinput_handler = UInputHandler(self.config)
            self.hid_parser = HIDParser(self.config)

            # Create uinput device
            await self.uinput_handler.create_device()

            # Connect to the already connected device
            await self._connect_to_existing_device()

            # Start listening for data
            await self._start_notifications()

            self.running = True
            logger.info("Driver started successfully with existing connection")

        except Exception as e:
            logger.error(f"Failed to start driver: {e}")
            await self.stop()
            raise

    async def _connect_to_existing_device(self):
        """Connect to a device that's already connected via bluetoothctl."""
        if not self.device_info:
            raise RuntimeError("No device to connect to")

        logger.info(f"Connecting to already connected device: {self.device_info.address}...")

        # For already connected devices, we need to use a different approach
        # Try to connect with a shorter timeout and different strategy
        self.client = BleakClient(
            self.device_info.address,
            timeout=5.0  # Shorter timeout for already connected devices
        )

        try:
            # Try to connect - this might fail if device is already connected at system level
            await self.client.connect()
            self.connected = True
            logger.info("Connected successfully to existing device")

            # Log available services and characteristics
            await self._log_services()

        except Exception as e:
            logger.warning(f"Direct connection failed: {e}")
            logger.info("Trying alternative connection method...")

            # Try alternative approach - create client without connecting
            # and try to discover services directly
            try:
                self.client = BleakClient(self.device_info.address)
                # Don't call connect() - just try to access services
                await self.client.connect(timeout=2.0)
                self.connected = True
                logger.info("Connected using alternative method")
                await self._log_services()
            except Exception as e2:
                logger.error(f"Alternative connection also failed: {e2}")
                self.connected = False
                raise RuntimeError(f"Could not connect to already connected device: {e2}")
