#!/usr/bin/env python3
"""Test script for Bluetooth watcher functionality."""

import asyncio
import logging
import sys
from src.huion_keydial_mini.bluetooth_watcher import BluetoothWatcher

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def test_bluetooth_watcher():
    """Test the Bluetooth watcher functionality."""

    def on_device_connected(mac_address: str):
        logger.info(f"🎉 Device connected: {mac_address}")

    # Create watcher
    watcher = BluetoothWatcher(on_connect_callback=on_device_connected)
    watcher.set_debug_mode(True)

    try:
        logger.info("Starting Bluetooth watcher...")
        await watcher.start()

        # Test the connection
        logger.info("Testing DBus connection...")
        if await watcher.test_connection():
            logger.info("✅ DBus connection working")
        else:
            logger.error("❌ DBus connection failed")
            return

        # Get currently connected devices
        logger.info("Checking currently connected devices...")
        connected_devices = await watcher.get_connected_devices()

        if connected_devices:
            logger.info("Currently connected devices:")
            for mac, info in connected_devices.items():
                logger.info(f"  {mac} - {info['name']} (paired: {info['paired']})")
        else:
            logger.info("No devices currently connected")

        logger.info("Waiting for device connections... (Press Ctrl+C to stop)")
        logger.info("💡 Try connecting a Bluetooth device to see signals")

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await watcher.stop()
        logger.info("Bluetooth watcher stopped")


async def test_wait_for_connection():
    """Test waiting for a specific device to connect."""

    target_mac = input("Enter MAC address to watch for (or press Enter to watch any device): ").strip()

    if not target_mac:
        target_mac = None

    watcher = BluetoothWatcher(target_mac=target_mac)
    watcher.set_debug_mode(True)

    try:
        logger.info("Waiting for device connection...")
        connected_mac = await watcher.wait_for_device_connection(timeout=60)

        if connected_mac:
            logger.info(f"✅ Device connected: {connected_mac}")
        else:
            logger.info("⏰ Timeout waiting for device connection")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await watcher.stop()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "wait":
        asyncio.run(test_wait_for_connection())
    else:
        asyncio.run(test_bluetooth_watcher())
