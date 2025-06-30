import logging
import signal
import sys
import time
from evdev import UInput, ecodes
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

    # Create the uinput device directly
    capabilities = {
        ecodes.EV_KEY: list(range(1, 256)),  # All possible key codes
        ecodes.EV_ABS: [],
    }

    device = None

    def cleanup(signum, frame):
        logger.info("Received signal to terminate, cleaning up...")
        try:
            if device:
                device.close()
                logger.info("uinput device closed and destroyed")
        except Exception as e:
            logger.warning(f"Error closing device: {e}")
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    try:
        # Create the uinput device
        device = UInput(events=capabilities, name=config.uinput_device_name)
        logger.info(f"uinput device created successfully: {config.uinput_device_name}")

        # Keep the device open and process running
        while True:
            time.sleep(60)
            logger.debug("uinput device still active")

    except Exception as e:
        logger.error(f"Failed to create uinput device: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

# Entry point for setuptools
def cli():
    main()
