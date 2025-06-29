import logging
import signal
import sys
import time
from evdev import UInput, ecodes
from huion_keydial_mini.uinput_handler import UInputHandler
from huion_keydial_mini.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("create_uinput_device")

def main():
    # Minimal valid config data
    config_data = {
        'device': {},
        'bluetooth': {},
        'uinput': {'device_name': 'huion-keydial-mini-uinput'},
        'key_mappings': {},
        'dial_settings': {},
    }
    config = Config(config_data)
    handler = UInputHandler(config)
    device = None

    def cleanup(signum, frame):
        logger.info("Received signal to terminate, cleaning up...")
        try:
            if handler.device:
                handler.device.close()
        except Exception as e:
            logger.warning(f"Error closing device: {e}")
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    try:
        logger.info(f"uinput device created: {config.uinput_device_name}")
        # Hold process
        while True:
            time.sleep(60)
    except Exception as e:
        logger.error(f"Failed to create uinput device: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

# Entry point for setuptools

def cli():
    main()
