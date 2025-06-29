#!/usr/bin/env python3
"""Test script for the wait-and-attach behavior of the device driver."""

import asyncio
import logging
import sys
from src.huion_keydial_mini.device import HuionKeydialMini
from src.huion_keydial_mini.config import Config

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def test_wait_and_attach():
    """Test the wait-and-attach behavior."""

    # Create a minimal config
    config_data = {
        'device': {},
        'bluetooth': {'auto_reconnect': True},
        'uinput': {'device_name': 'test-device'},
        'key_mappings': {},
        'dial_settings': {},
    }
    config = Config(config_data)

    # Create device driver
    device = HuionKeydialMini(config)

    try:
        logger.info("Starting device driver in wait mode...")
        await device.start()

        logger.info("Driver is now waiting for device connections...")
        logger.info("💡 Try connecting/disconnecting your Keydial Mini to see the behavior")

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await device.stop()
        logger.info("Device driver stopped")


if __name__ == "__main__":
    asyncio.run(test_wait_and_attach())
