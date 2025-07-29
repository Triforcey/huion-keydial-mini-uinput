"""Main device driver for Huion Keydial Mini."""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List, NamedTuple, Union
import struct

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.characteristic import BleakGATTCharacteristic

from .config import Config
from .uinput_handler import UInputHandler
from .hid_parser import HIDParser
from .keybind_manager import KeybindManager
from .bluetooth_watcher import BluetoothWatcher


logger = logging.getLogger(__name__)


class DeviceInfo(NamedTuple):
    """Device information structure."""
    address: str
    name: str


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
        self.device_info: Optional[DeviceInfo] = None
        self.client: Optional[BleakClient] = None
        self.connected = False
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.debug_mode = getattr(config, 'debug_mode', False)
        self.auto_reconnect = getattr(config, 'auto_reconnect', True)

        # Initialize components
        self.keybind_manager = KeybindManager(config)
        self.hid_parser = HIDParser(config)
        self.uinput_handler = UInputHandler(config, self.keybind_manager)

        # Connect keybind manager to hid parser for sticky functionality
        self.hid_parser.set_keybind_manager(self.keybind_manager)

        # Initialize Bluetooth watcher for automatic connection detection
        self.bluetooth_watcher: Optional[BluetoothWatcher] = None
        self.watcher_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the device driver."""
        logger.info("Starting Huion Keydial Mini driver...")

        try:
            # Start the keybind manager socket server
            await self.keybind_manager.start_socket_server()

            # Start Bluetooth watcher for automatic connection detection
            if self.auto_reconnect:
                await self._start_bluetooth_watcher()

            # Try to attach to already connected devices
            await self._try_attach_to_existing_devices()

            self.running = True
            logger.info("Driver started successfully - waiting for device connections")

        except Exception as e:
            logger.error(f"Failed to start driver: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the device driver."""
        logger.info("Stopping driver...")

        self.running = False

        # Stop Bluetooth watcher
        if self.bluetooth_watcher:
            await self.bluetooth_watcher.stop()
            self.bluetooth_watcher = None

        if self.watcher_task and not self.watcher_task.done():
            self.watcher_task.cancel()
            try:
                await self.watcher_task
            except asyncio.CancelledError:
                pass

        if self.client and self.connected:
            try:
                await self.client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")

        if self.uinput_handler:
            pass

        if self.keybind_manager:
            await self.keybind_manager.stop_socket_server()

        self.connected = False
        logger.info("Driver stopped")

    async def _start_bluetooth_watcher(self):
        """Start the Bluetooth connection watcher."""
        try:
            # Create Bluetooth watcher with callbacks for device connections and disconnections
            self.bluetooth_watcher = BluetoothWatcher(
                target_mac=self.config.device_address,
                on_connect_callback=self._on_device_connected_via_dbus,
                on_disconnect_callback=self._on_device_disconnected_via_dbus
            )

            if self.debug_mode:
                self.bluetooth_watcher.set_debug_mode(True)

            await self.bluetooth_watcher.start()
            logger.info("Bluetooth connection watcher started")

        except Exception as e:
            logger.warning(f"Failed to start Bluetooth watcher: {e}")
            logger.info("Continuing without automatic connection detection")

    async def _on_device_connected_via_dbus(self, mac_address: str):
        """Handle device connection detected via DBus."""
        logger.info(f"Device {mac_address} connected (detected via DBus)")

        # If we have a specific target device, only handle that one
        if (self.config.device_address and
            mac_address.upper() != self.config.device_address.upper()):
            logger.debug(f"Ignoring connection for non-target device: {mac_address}")
            return

        # If we don't have a specific target, check if this is a Huion device by name
        if not self.config.device_address:
            try:
                # Get device info to check the name
                if self.bluetooth_watcher:
                    connected_devices = await self.bluetooth_watcher.get_connected_devices()
                    device_info = connected_devices.get(mac_address, {})
                    device_name = device_info.get('name', '')

                    if not self._is_huion_device_name(device_name):
                        logger.debug(f"Ignoring non-Huion device: {device_name} ({mac_address})")
                        return

                    logger.info(f"Found Huion device: {device_name} ({mac_address})")
                else:
                    logger.warning("Cannot check device name - BluetoothWatcher not available")
                    return
            except Exception as e:
                logger.warning(f"Failed to check device name for {mac_address}: {e}")
                return

        # If we're already connected to this device, ignore
        if (self.connected and self.device_info and
            self.device_info.address.upper() == mac_address.upper()):
            return

        # Try to attach to the newly connected device
        try:
            await self._attach_to_device_by_mac(mac_address)
        except Exception as e:
            logger.error(f"Failed to attach to device {mac_address}: {e}")

    async def _on_device_disconnected_via_dbus(self, mac_address: str):
        """Handle device disconnection detected via DBus."""
        logger.info(f"Device {mac_address} disconnected (detected via DBus)")

        # Only handle if this is our currently connected device
        if (self.connected and self.device_info and
            self.device_info.address.upper() == mac_address.upper()):

            logger.info(f"Detached from device {mac_address} - returning to wait mode")
            await self._detach_from_device()

    async def _try_attach_to_existing_devices(self):
        """Try to attach to already connected devices."""
        try:
            # Check if our target device is already connected
            if self.bluetooth_watcher:
                connected_devices = await self.bluetooth_watcher.get_connected_devices()

                if self.config.device_address:
                    # Check if our specific device is connected
                    if self.config.device_address in connected_devices:
                        logger.info(f"Target device {self.config.device_address} is already connected")
                        await self._attach_to_device_by_mac(self.config.device_address)
                        return
                else:
                    # Look for any Huion device that's connected
                    for mac, device_info in connected_devices.items():
                        if self._is_huion_device_name(device_info.get('name', '')):
                            logger.info(f"Found connected Huion device: {mac}")
                            await self._attach_to_device_by_mac(mac)
                            return

            # No devices are currently connected
            logger.info("No devices currently connected - waiting for connections...")

        except Exception as e:
            logger.warning(f"Failed to check for existing devices: {e}")
            if not self.auto_reconnect:
                raise

    async def _attach_to_device_by_mac(self, mac_address: str):
        """Attach to an already connected device by MAC address."""
        logger.info(f"Attaching to device {mac_address}...")

        try:
            # Create device info for the MAC address
            self.device_info = DeviceInfo(
                address=mac_address,
                name=f"Huion Device ({mac_address})"
            )

            # Connect immediately - no delays or extra steps
            await self._connect_with_retry()

            if not self.connected or not self.client:
                raise RuntimeError(f"Connection failed: connected={self.connected}, client_exists={self.client is not None}")

            await self._start_notifications()

            logger.info(f"Successfully attached to {mac_address}")

        except Exception as e:
            logger.error(f"Failed to attach to {mac_address}: {e}")
            self.device_info = None
            raise

    async def _detach_from_device(self):
        """Detach from the current device and return to wait mode."""
        logger.info("Detaching from device...")

        if self.client and self.connected:
            try:
                await self.client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")

        self.client = None
        self.connected = False
        self.device_info = None
        self.reconnect_attempts = 0

        logger.info("Detached from device - waiting for next connection")

    def _is_huion_device_name(self, device_name: Any) -> bool:
        """Check if a device name matches Huion device patterns."""
        if not device_name:
            return False

        # Handle potential Variant objects or other types defensively
        try:
            if hasattr(device_name, 'value'):
                device_name = device_name.value
            device_name = str(device_name)
        except Exception:
            logger.warning(f"Could not convert device name to string: {device_name}")
            return False

        device_name_lower = device_name.lower()
        huion_indicators = ['huion', 'keydial']
        return any(indicator in device_name_lower for indicator in huion_indicators)

    async def _connect_with_retry(self):
        """Connect to the device with retry logic."""
        max_quick_attempts = 3  # Fewer attempts but faster

        for attempt in range(max_quick_attempts):
            try:
                await self._connect()
                self.reconnect_attempts = 0  # Reset on successful connection
                return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")

                if attempt < max_quick_attempts - 1:
                    # Quick retry - only 1 second delay
                    await asyncio.sleep(1.0)
                else:
                    logger.error("Connection attempts failed")
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

            if self.client.is_connected:
                self.connected = True
                logger.info("Connected successfully")
                await self._log_services()
            else:
                raise RuntimeError("BleakClient reports not connected after connect() call")

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
                if self.uinput_handler and events:
                    for event in events:
                        try:
                            await self.uinput_handler.send_event(event)
                            if self.debug_mode:
                                logger.debug(f"Sent uinput event: {event.event_type} - {event.key_code}")
                        except Exception as e:
                            logger.error(f"Error sending uinput event: {e}")
                            if self.debug_mode:
                                import traceback
                                logger.debug(traceback.format_exc())

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
