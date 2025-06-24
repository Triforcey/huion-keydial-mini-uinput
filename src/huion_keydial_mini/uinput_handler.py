"""UInput handler for generating Linux input events."""

import asyncio
import logging
from typing import List, Optional, Dict
import evdev
from evdev import UInput, ecodes

from .config import Config
from .hid_parser import InputEvent, EventType


logger = logging.getLogger(__name__)


class UInputHandler:
    """Handles creation of virtual input device and event generation."""

    # Mapping of key names to evdev key codes
    KEY_MAPPING = {
        'KEY_F1': ecodes.KEY_F1,
        'KEY_F2': ecodes.KEY_F2,
        'KEY_F3': ecodes.KEY_F3,
        'KEY_F4': ecodes.KEY_F4,
        'KEY_F5': ecodes.KEY_F5,
        'KEY_F6': ecodes.KEY_F6,
        'KEY_F7': ecodes.KEY_F7,
        'KEY_F8': ecodes.KEY_F8,
        'KEY_F9': ecodes.KEY_F9,
        'KEY_F10': ecodes.KEY_F10,
        'KEY_F11': ecodes.KEY_F11,
        'KEY_F12': ecodes.KEY_F12,
        'KEY_ENTER': ecodes.KEY_ENTER,
        'KEY_SPACE': ecodes.KEY_SPACE,
        'KEY_ESC': ecodes.KEY_ESC,
        'KEY_TAB': ecodes.KEY_TAB,
        'KEY_BACKSPACE': ecodes.KEY_BACKSPACE,
        'KEY_DELETE': ecodes.KEY_DELETE,
        'KEY_HOME': ecodes.KEY_HOME,
        'KEY_END': ecodes.KEY_END,
        'KEY_PAGEUP': ecodes.KEY_PAGEUP,
        'KEY_PAGEDOWN': ecodes.KEY_PAGEDOWN,
        'KEY_UP': ecodes.KEY_UP,
        'KEY_DOWN': ecodes.KEY_DOWN,
        'KEY_LEFT': ecodes.KEY_LEFT,
        'KEY_RIGHT': ecodes.KEY_RIGHT,
        'KEY_VOLUMEUP': ecodes.KEY_VOLUMEUP,
        'KEY_VOLUMEDOWN': ecodes.KEY_VOLUMEDOWN,
        'KEY_MUTE': ecodes.KEY_MUTE,
        'KEY_PLAYPAUSE': ecodes.KEY_PLAYPAUSE,
        'KEY_NEXTSONG': ecodes.KEY_NEXTSONG,
        'KEY_PREVIOUSSONG': ecodes.KEY_PREVIOUSSONG,
        'KEY_LEFTCTRL': ecodes.KEY_LEFTCTRL,
        'KEY_RIGHTCTRL': ecodes.KEY_RIGHTCTRL,
        'KEY_LEFTSHIFT': ecodes.KEY_LEFTSHIFT,
        'KEY_RIGHTSHIFT': ecodes.KEY_RIGHTSHIFT,
        'KEY_LEFTALT': ecodes.KEY_LEFTALT,
        'KEY_RIGHTALT': ecodes.KEY_RIGHTALT,
        'KEY_LEFTMETA': ecodes.KEY_LEFTMETA,
        'KEY_RIGHTMETA': ecodes.KEY_RIGHTMETA,
    }

    def __init__(self, config: Config):
        self.config = config
        self.device: Optional[UInput] = None
        self.capabilities = self._build_capabilities()

    def _build_capabilities(self) -> Dict:
        """Build device capabilities based on configuration."""
        capabilities = {
            evdev.ecodes.EV_KEY: [],
        }

        # Add all possible keys that might be used
        for key_name in self.KEY_MAPPING.keys():
            key_code = self.KEY_MAPPING.get(key_name)
            if key_code and key_code not in capabilities[evdev.ecodes.EV_KEY]:
                capabilities[evdev.ecodes.EV_KEY].append(key_code)

        # Add keys from configuration
        for key_name in self.config.key_mappings.values():
            key_code = self.KEY_MAPPING.get(key_name)
            if key_code and key_code not in capabilities[evdev.ecodes.EV_KEY]:
                capabilities[evdev.ecodes.EV_KEY].append(key_code)

        # Add dial keys
        dial_keys = [
            self.config.dial_settings.get('clockwise_key'),
            self.config.dial_settings.get('counterclockwise_key'),
            self.config.dial_settings.get('click_key'),
        ]

        for key_name in dial_keys:
            if key_name:
                key_code = self.KEY_MAPPING.get(key_name)
                if key_code and key_code not in capabilities[evdev.ecodes.EV_KEY]:
                    capabilities[evdev.ecodes.EV_KEY].append(key_code)

        return capabilities

    async def create_device(self):
        """Create the virtual input device."""
        logger.info("Creating virtual input device...")

        try:
            self.device = UInput(
                events=self.capabilities,
                name=self.config.uinput_device_name,
                vendor=0x256c,  # Huion vendor ID
                product=0x006d,  # Generic product ID
                version=0x0001,
            )

            logger.info(f"Created virtual device: {self.config.uinput_device_name}")
            logger.debug(f"Device capabilities: {self.capabilities}")

        except Exception as e:
            logger.error(f"Failed to create virtual device: {e}")
            raise

    async def destroy_device(self):
        """Destroy the virtual input device."""
        if self.device:
            logger.info("Destroying virtual input device...")
            try:
                self.device.close()
                self.device = None
                logger.info("Virtual device destroyed")
            except Exception as e:
                logger.warning(f"Error destroying device: {e}")

    async def send_event(self, event: InputEvent):
        """Send an input event to the virtual device."""
        if not self.device:
            logger.warning("No virtual device available")
            return

        try:
            if event.event_type in [EventType.KEY_PRESS, EventType.KEY_RELEASE]:
                if not event.key_code:
                    logger.warning("Key event without key code")
                    return

                # Handle key combinations (e.g., "KEY_CTRL+KEY_C")
                key_parts = [k.strip() for k in event.key_code.split('+')]
                key_codes = []

                for key_name in key_parts:
                    key_code = self.KEY_MAPPING.get(key_name)
                    if not key_code:
                        logger.warning(f"Unknown key code: {key_name}")
                        return
                    key_codes.append(key_code)

                # Send key events
                value = 1 if event.event_type == EventType.KEY_PRESS else 0

                if value == 1:  # Press
                    # Press all keys in order
                    for key_code in key_codes:
                        self.device.write(evdev.ecodes.EV_KEY, key_code, 1)
                        self.device.syn()
                else:  # Release
                    # Release all keys in reverse order
                    for key_code in reversed(key_codes):
                        self.device.write(evdev.ecodes.EV_KEY, key_code, 0)
                        self.device.syn()

                logger.debug(f"Sent key event: {event.key_code} = {value}")

            else:
                logger.warning(f"Unsupported event type: {event.event_type}")

        except Exception as e:
            logger.error(f"Error sending event: {e}")

    def get_supported_keys(self) -> List[str]:
        """Get list of supported key names."""
        return list(self.KEY_MAPPING.keys())
