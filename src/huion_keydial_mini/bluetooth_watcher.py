"""DBus-based Bluetooth device connection watcher."""

import asyncio
import logging
import re
from typing import Optional, Callable
from dbus_next.constants import BusType, MessageType
from dbus_next.aio.message_bus import MessageBus
from dbus_next.message import Message

logger = logging.getLogger(__name__)


class BluetoothWatcher:
    """Watches for Bluetooth device connection/disconnection events using DBus."""

    def __init__(self, target_mac: Optional[str] = None, on_connect_callback: Optional[Callable] = None, on_disconnect_callback: Optional[Callable] = None):
        self.target_mac = self._normalize_mac(target_mac) if target_mac else None
        self.on_connect_callback = on_connect_callback
        self.on_disconnect_callback = on_disconnect_callback
        self.bus: Optional[MessageBus] = None
        self.running = False
        self.debug_mode = False

    def _normalize_mac(self, mac: str) -> str:
        """Convert MAC address to DBus path format."""
        # Convert XX:XX:XX:XX:XX:XX to XX_XX_XX_XX_XX_XX
        return mac.replace(':', '_').upper()

    def _mac_to_dbus_path(self, mac: str) -> str:
        """Convert MAC address to DBus object path."""
        normalized = self._normalize_mac(mac)
        return f"/org/bluez/hci0/dev_{normalized}"

    def _dbus_path_to_mac(self, path: str) -> str:
        """Convert DBus object path to MAC address."""
        # Extract MAC from path like /org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX
        match = re.search(r'/dev_([A-F0-9_]+)$', path)
        if match:
            # Convert XX_XX_XX_XX_XX_XX back to XX:XX:XX:XX:XX:XX
            return match.group(1).replace('_', ':')
        return ""

    async def start(self):
        """Start watching for Bluetooth connection events."""
        if self.running:
            logger.warning("Bluetooth watcher is already running")
            return

        logger.info("Starting Bluetooth connection watcher...")

        try:
            # Connect to system DBus
            self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
            self.running = True

            # Add message handler for PropertiesChanged signals
            if self.bus:
                self.bus.add_message_handler(self._handle_message)
                logger.info("Message handler added to DBus bus")

                # Subscribe to PropertiesChanged signals from BlueZ
                await self._subscribe_to_signals()

            logger.info("Bluetooth watcher started successfully")

        except Exception as e:
            logger.error(f"Failed to start Bluetooth watcher: {e}")
            self.running = False
            raise

    async def _subscribe_to_signals(self):
        """Subscribe to PropertiesChanged signals from BlueZ."""
        try:
            if not self.bus:
                raise RuntimeError("No DBus bus connection")

            # Add a match rule to receive PropertiesChanged signals from BlueZ
            # Use a simpler match rule first
            match_rule = "type='signal',interface='org.freedesktop.DBus.Properties',member='PropertiesChanged',sender='org.bluez'"

            await self.bus.call(
                Message(
                    destination="org.freedesktop.DBus",
                    path="/org/freedesktop/DBus",
                    interface="org.freedesktop.DBus",
                    member="AddMatch",
                    signature="s",
                    body=[match_rule]
                )
            )
            logger.info(f"Subscribed to BlueZ PropertiesChanged signals with rule: {match_rule}")
        except Exception as e:
            logger.error(f"Failed to subscribe to signals: {e}")
            raise

    async def stop(self):
        """Stop watching for Bluetooth connection events."""
        if not self.running:
            return

        logger.info("Stopping Bluetooth connection watcher...")

        self.running = False

        if self.bus:
            try:
                self.bus.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting from DBus: {e}")
            finally:
                self.bus = None

        logger.info("Bluetooth watcher stopped")

    def _handle_message(self, message: Message):
        """Handle incoming DBus messages."""
        # Log ALL messages for debugging
        if self.debug_mode:
            logger.debug(f"Received DBus message: {message.member} on {message.path} from {message.sender}")
            logger.debug(f"Message details: type={message.message_type}, interface={message.interface}, member={message.member}")

        if not self.running:
            return

        try:
            # Only handle PropertiesChanged signals
            if (message.message_type != MessageType.SIGNAL or
                message.interface != "org.freedesktop.DBus.Properties" or
                message.member != "PropertiesChanged"):
                if self.debug_mode:
                    logger.debug(f"Ignoring message: type={message.message_type}, interface={message.interface}, member={message.member}")
                return

            # Extract the object path (device path)
            object_path = message.path
            if not object_path or not object_path.startswith("/org/bluez/hci0/dev_"):
                if self.debug_mode:
                    logger.debug(f"Ignoring non-device path: {object_path}")
                return

            # Extract MAC address from path
            mac_address = self._dbus_path_to_mac(object_path)
            if not mac_address:
                if self.debug_mode:
                    logger.debug(f"Could not extract MAC from path: {object_path}")
                return

            if self.debug_mode:
                logger.debug(f"DBus signal: {message.member} on {object_path} (MAC: {mac_address})")

            # Check if this is our target device (if specified)
            if self.target_mac and mac_address.upper() != self.target_mac.upper():
                if self.debug_mode:
                    logger.debug(f"Ignoring signal for non-target device: {mac_address} (target: {self.target_mac})")
                return

            # Parse the PropertiesChanged signal
            if len(message.body) >= 2:
                interface_name = message.body[0]
                changed_properties = message.body[1]

                if self.debug_mode:
                    logger.debug(f"Interface: {interface_name}, Properties: {changed_properties}")

                # We're interested in the org.bluez.Device1 interface
                if interface_name == "org.bluez.Device1":
                    if self.debug_mode:
                        logger.debug(f"Processing Device1 property change for {mac_address}")
                    # Schedule the async handler
                    asyncio.create_task(self._handle_device_property_change(mac_address, changed_properties))
                elif self.debug_mode:
                    logger.debug(f"Ignoring signal for interface: {interface_name}")

        except Exception as e:
            logger.error(f"Error handling DBus message: {e}")
            if self.debug_mode:
                import traceback
                logger.debug(traceback.format_exc())

    async def _handle_device_property_change(self, mac_address: str, changed_properties: dict):
        """Handle device property changes."""
        try:
            # Only care about Connected property changes
            if "Connected" not in changed_properties:
                return

            connected_variant = changed_properties["Connected"]
            connected = connected_variant.value if hasattr(connected_variant, 'value') else connected_variant

            if self.debug_mode:
                logger.debug(f"Device {mac_address} connection state changed: {connected}")

            # Handle both connections and disconnections
            if connected:
                logger.info(f"Device {mac_address} connected")
                await self._on_device_connected(mac_address)
            else:
                logger.info(f"Device {mac_address} disconnected")
                await self._on_device_disconnected(mac_address)

        except Exception as e:
            logger.error(f"Error handling device property change: {e}")
            if self.debug_mode:
                import traceback
                logger.debug(traceback.format_exc())

    async def _on_device_connected(self, mac_address: str):
        """Handle device connection event."""
        if self.on_connect_callback:
            try:
                # Call the callback asynchronously
                if asyncio.iscoroutinefunction(self.on_connect_callback):
                    await self.on_connect_callback(mac_address)
                else:
                    # If it's a regular function, run it in executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.on_connect_callback, mac_address)
            except Exception as e:
                logger.error(f"Error in connection callback: {e}")

    async def _on_device_disconnected(self, mac_address: str):
        """Handle device disconnection event."""
        if self.on_disconnect_callback:
            try:
                # Call the callback asynchronously
                if asyncio.iscoroutinefunction(self.on_disconnect_callback):
                    await self.on_disconnect_callback(mac_address)
                else:
                    # If it's a regular function, run it in executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.on_disconnect_callback, mac_address)
            except Exception as e:
                logger.error(f"Error in disconnection callback: {e}")

    def set_debug_mode(self, enabled: bool):
        """Enable or disable debug mode."""
        self.debug_mode = enabled
        if enabled:
            logger.info("Bluetooth watcher debug mode enabled")
        else:
            logger.debug("Bluetooth watcher debug mode disabled")
