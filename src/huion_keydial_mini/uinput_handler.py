"""UInput handler for generating Linux input events."""

import asyncio
import logging
from typing import List, Optional, Dict
import evdev
from evdev import UInput, ecodes
import time

from .config import Config
from .hid_parser import InputEvent, EventType
from .keybind_manager import KeybindManager, KeybindAction, EventType as BindEventType


logger = logging.getLogger(__name__)


class UInputHandler:
    """Handles creation of virtual input device and event generation."""

    # Comprehensive mapping of key names to evdev key codes
    KEY_MAPPING = {
        # Function keys (F1-F24)
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
        'KEY_F13': ecodes.KEY_F13,
        'KEY_F14': ecodes.KEY_F14,
        'KEY_F15': ecodes.KEY_F15,
        'KEY_F16': ecodes.KEY_F16,
        'KEY_F17': ecodes.KEY_F17,
        'KEY_F18': ecodes.KEY_F18,
        'KEY_F19': ecodes.KEY_F19,
        'KEY_F20': ecodes.KEY_F20,
        'KEY_F21': ecodes.KEY_F21,
        'KEY_F22': ecodes.KEY_F22,
        'KEY_F23': ecodes.KEY_F23,
        'KEY_F24': ecodes.KEY_F24,

        # Letters (A-Z)
        'KEY_A': ecodes.KEY_A,
        'KEY_B': ecodes.KEY_B,
        'KEY_C': ecodes.KEY_C,
        'KEY_D': ecodes.KEY_D,
        'KEY_E': ecodes.KEY_E,
        'KEY_F': ecodes.KEY_F,
        'KEY_G': ecodes.KEY_G,
        'KEY_H': ecodes.KEY_H,
        'KEY_I': ecodes.KEY_I,
        'KEY_J': ecodes.KEY_J,
        'KEY_K': ecodes.KEY_K,
        'KEY_L': ecodes.KEY_L,
        'KEY_M': ecodes.KEY_M,
        'KEY_N': ecodes.KEY_N,
        'KEY_O': ecodes.KEY_O,
        'KEY_P': ecodes.KEY_P,
        'KEY_Q': ecodes.KEY_Q,
        'KEY_R': ecodes.KEY_R,
        'KEY_S': ecodes.KEY_S,
        'KEY_T': ecodes.KEY_T,
        'KEY_U': ecodes.KEY_U,
        'KEY_V': ecodes.KEY_V,
        'KEY_W': ecodes.KEY_W,
        'KEY_X': ecodes.KEY_X,
        'KEY_Y': ecodes.KEY_Y,
        'KEY_Z': ecodes.KEY_Z,

        # Numbers (0-9)
        'KEY_0': ecodes.KEY_0,
        'KEY_1': ecodes.KEY_1,
        'KEY_2': ecodes.KEY_2,
        'KEY_3': ecodes.KEY_3,
        'KEY_4': ecodes.KEY_4,
        'KEY_5': ecodes.KEY_5,
        'KEY_6': ecodes.KEY_6,
        'KEY_7': ecodes.KEY_7,
        'KEY_8': ecodes.KEY_8,
        'KEY_9': ecodes.KEY_9,

        # Modifier keys
        'KEY_LEFTCTRL': ecodes.KEY_LEFTCTRL,
        'KEY_RIGHTCTRL': ecodes.KEY_RIGHTCTRL,
        'KEY_LEFTSHIFT': ecodes.KEY_LEFTSHIFT,
        'KEY_RIGHTSHIFT': ecodes.KEY_RIGHTSHIFT,
        'KEY_LEFTALT': ecodes.KEY_LEFTALT,
        'KEY_RIGHTALT': ecodes.KEY_RIGHTALT,
        'KEY_LEFTMETA': ecodes.KEY_LEFTMETA,
        'KEY_RIGHTMETA': ecodes.KEY_RIGHTMETA,
        'KEY_CAPSLOCK': ecodes.KEY_CAPSLOCK,
        'KEY_NUMLOCK': ecodes.KEY_NUMLOCK,
        'KEY_SCROLLLOCK': ecodes.KEY_SCROLLLOCK,

        # Navigation keys
        'KEY_UP': ecodes.KEY_UP,
        'KEY_DOWN': ecodes.KEY_DOWN,
        'KEY_LEFT': ecodes.KEY_LEFT,
        'KEY_RIGHT': ecodes.KEY_RIGHT,
        'KEY_HOME': ecodes.KEY_HOME,
        'KEY_END': ecodes.KEY_END,
        'KEY_PAGEUP': ecodes.KEY_PAGEUP,
        'KEY_PAGEDOWN': ecodes.KEY_PAGEDOWN,
        'KEY_INSERT': ecodes.KEY_INSERT,
        'KEY_DELETE': ecodes.KEY_DELETE,

        # Special keys
        'KEY_ENTER': ecodes.KEY_ENTER,
        'KEY_SPACE': ecodes.KEY_SPACE,
        'KEY_TAB': ecodes.KEY_TAB,
        'KEY_BACKSPACE': ecodes.KEY_BACKSPACE,
        'KEY_ESC': ecodes.KEY_ESC,
        'KEY_PAUSE': ecodes.KEY_PAUSE,
        'KEY_PRINTSCREEN': ecodes.KEY_SYSRQ,
        'KEY_MENU': ecodes.KEY_MENU,

        # Punctuation keys
        'KEY_GRAVE': ecodes.KEY_GRAVE,
        'KEY_MINUS': ecodes.KEY_MINUS,
        'KEY_EQUAL': ecodes.KEY_EQUAL,
        'KEY_LEFTBRACE': ecodes.KEY_LEFTBRACE,
        'KEY_RIGHTBRACE': ecodes.KEY_RIGHTBRACE,
        'KEY_BACKSLASH': ecodes.KEY_BACKSLASH,
        'KEY_SEMICOLON': ecodes.KEY_SEMICOLON,
        'KEY_APOSTROPHE': ecodes.KEY_APOSTROPHE,
        'KEY_COMMA': ecodes.KEY_COMMA,
        'KEY_DOT': ecodes.KEY_DOT,
        'KEY_SLASH': ecodes.KEY_SLASH,

        # Numpad keys
        'KEY_KP0': ecodes.KEY_KP0,
        'KEY_KP1': ecodes.KEY_KP1,
        'KEY_KP2': ecodes.KEY_KP2,
        'KEY_KP3': ecodes.KEY_KP3,
        'KEY_KP4': ecodes.KEY_KP4,
        'KEY_KP5': ecodes.KEY_KP5,
        'KEY_KP6': ecodes.KEY_KP6,
        'KEY_KP7': ecodes.KEY_KP7,
        'KEY_KP8': ecodes.KEY_KP8,
        'KEY_KP9': ecodes.KEY_KP9,
        'KEY_KPDOT': ecodes.KEY_KPDOT,
        'KEY_KPENTER': ecodes.KEY_KPENTER,
        'KEY_KPPLUS': ecodes.KEY_KPPLUS,
        'KEY_KPMINUS': ecodes.KEY_KPMINUS,
        'KEY_KPASTERISK': ecodes.KEY_KPASTERISK,
        'KEY_KPSLASH': ecodes.KEY_KPSLASH,
        'KEY_KPEQUAL': ecodes.KEY_KPEQUAL,

        # Media keys
        'KEY_VOLUMEUP': ecodes.KEY_VOLUMEUP,
        'KEY_VOLUMEDOWN': ecodes.KEY_VOLUMEDOWN,
        'KEY_MUTE': ecodes.KEY_MUTE,
        'KEY_PLAYPAUSE': ecodes.KEY_PLAYPAUSE,
        'KEY_NEXTSONG': ecodes.KEY_NEXTSONG,
        'KEY_PREVIOUSSONG': ecodes.KEY_PREVIOUSSONG,
        'KEY_STOPCD': ecodes.KEY_STOPCD,
        'KEY_EJECTCD': ecodes.KEY_EJECTCD,
        'KEY_FASTFORWARD': ecodes.KEY_FASTFORWARD,
        'KEY_REWIND': ecodes.KEY_REWIND,
        'KEY_RECORD': ecodes.KEY_RECORD,

        # System keys
        'KEY_POWER': ecodes.KEY_POWER,
        'KEY_SLEEP': ecodes.KEY_SLEEP,
        'KEY_WAKEUP': ecodes.KEY_WAKEUP,
        'KEY_SUSPEND': ecodes.KEY_SUSPEND,
        'KEY_BRIGHTNESSUP': ecodes.KEY_BRIGHTNESSUP,
        'KEY_BRIGHTNESSDOWN': ecodes.KEY_BRIGHTNESSDOWN,
        'KEY_BRIGHTNESS_AUTO': ecodes.KEY_BRIGHTNESS_AUTO,
        'KEY_BRIGHTNESS_CYCLE': ecodes.KEY_BRIGHTNESS_CYCLE,
        'KEY_BRIGHTNESS_ZERO': ecodes.KEY_BRIGHTNESS_ZERO,
        'KEY_BRIGHTNESS_MAX': ecodes.KEY_BRIGHTNESS_MAX,
        'KEY_BRIGHTNESS_MIN': ecodes.KEY_BRIGHTNESS_MIN,
        'KEY_BRIGHTNESS_TOGGLE': ecodes.KEY_BRIGHTNESS_TOGGLE,

        # Connectivity keys
        'KEY_BLUETOOTH': ecodes.KEY_BLUETOOTH,
        'KEY_WLAN': ecodes.KEY_WLAN,
        'KEY_RFKILL': ecodes.KEY_RFKILL,

        # Additional common keys
        'KEY_CALCULATOR': ecodes.KEY_CALC,
        'KEY_MAIL': ecodes.KEY_MAIL,
        'KEY_COMPUTER': ecodes.KEY_COMPUTER,
        'KEY_HOMEPAGE': ecodes.KEY_HOMEPAGE,
        'KEY_BACK': ecodes.KEY_BACK,
        'KEY_FORWARD': ecodes.KEY_FORWARD,
        'KEY_REFRESH': ecodes.KEY_REFRESH,
        'KEY_SEARCH': ecodes.KEY_SEARCH,
        'KEY_BOOKMARKS': ecodes.KEY_BOOKMARKS,
        'KEY_BATTERY': ecodes.KEY_BATTERY,
        'KEY_CAMERA': ecodes.KEY_CAMERA,
        'KEY_PHONE': ecodes.KEY_PHONE,
        'KEY_MICMUTE': ecodes.KEY_MICMUTE,
        'KEY_TOUCHPAD_TOGGLE': ecodes.KEY_TOUCHPAD_TOGGLE,
        'KEY_TOUCHPAD_ON': ecodes.KEY_TOUCHPAD_ON,
        'KEY_TOUCHPAD_OFF': ecodes.KEY_TOUCHPAD_OFF,

        # Mouse buttons
        'BTN_LEFT': ecodes.BTN_LEFT,
        'BTN_RIGHT': ecodes.BTN_RIGHT,
        'BTN_MIDDLE': ecodes.BTN_MIDDLE,
        'BTN_SIDE': ecodes.BTN_SIDE,
        'BTN_EXTRA': ecodes.BTN_EXTRA,
        'BTN_FORWARD': ecodes.BTN_FORWARD,
        'BTN_BACK': ecodes.BTN_BACK,
        'BTN_TASK': ecodes.BTN_TASK,
    }

    def __init__(self, config: Config, keybind_manager: Optional[KeybindManager] = None):
        self.config = config
        self.keybind_manager = keybind_manager
        self.device: Optional[UInput] = None
        self.capabilities = self._build_capabilities()
        self._try_open_device()

    def _try_open_device(self):
        """Try to open the existing uinput device."""
        max_retries = 30  # Wait up to 30 seconds
        retry_delay = 1.0

        logger.info(f"Waiting for uinput device '{self.config.uinput_device_name}' to be available...")

        for attempt in range(max_retries):
            try:
                self.device = UInput(events=self.capabilities, name=self.config.uinput_device_name)
                logger.info(f"Successfully opened uinput device '{self.config.uinput_device_name}'")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.info(f"Waiting for uinput device... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to open uinput device '{self.config.uinput_device_name}' after {max_retries} attempts: {e}")
                    raise RuntimeError(f"uinput device not available after {max_retries} seconds")

    def _build_capabilities(self) -> Dict:
        """Build device capabilities based on configuration and keybind manager."""
        capabilities = {
            evdev.ecodes.EV_KEY: [],
            # Add mouse relative events for scroll and movement
            evdev.ecodes.EV_REL: [evdev.ecodes.REL_X, evdev.ecodes.REL_Y, evdev.ecodes.REL_WHEEL, evdev.ecodes.REL_HWHEEL],
        }

        # Add all possible keys that might be used
        for key_name in self.KEY_MAPPING.keys():
            key_code = self.KEY_MAPPING.get(key_name)
            if key_code and key_code not in capabilities[evdev.ecodes.EV_KEY]:
                capabilities[evdev.ecodes.EV_KEY].append(key_code)

        # Add keys from keybind manager if available
        if self.keybind_manager:
            for action in self.keybind_manager.get_all_actions().values():
                if action.keys:
                    for key_name in action.keys:
                        key_code = self.KEY_MAPPING.get(key_name)
                        if key_code and key_code not in capabilities[evdev.ecodes.EV_KEY]:
                            capabilities[evdev.ecodes.EV_KEY].append(key_code)

        return capabilities

    async def send_event(self, event: InputEvent):
        """Send an input event to the virtual device."""
        if not self.device:
            logger.warning("No virtual device available")
            return

        try:
            # Get the action ID from the event
            action_id = self._get_action_id_from_event(event)
            if not action_id:
                logger.debug(f"No action ID found for event: {event}")
                return

            # Get the keybind action from the manager
            if not self.keybind_manager:
                logger.warning("No keybind manager available")
                return

            action = self.keybind_manager.get_action(action_id)
            if not action:
                logger.debug(f"No binding found for action: {action_id}")
                return

            # Execute the action based on its type
            if action.type == BindEventType.KEYBOARD:
                await self._send_keyboard_action(action, event)
            else:
                logger.warning(f"Unknown action type: {action.type}")

        except Exception as e:
            logger.error(f"Error sending event: {e}")

    def _get_action_id_from_event(self, event: InputEvent) -> Optional[str]:
        if event.key_code != None:
            return event.key_code
        else:
            logger.warning(f"No keycode found for event: {event}")
        return None

    async def _send_keyboard_action(self, action: KeybindAction, event: InputEvent):
        """Send a keyboard action."""
        if not action.keys:
            logger.warning("Keyboard action has no keys defined")
            return

        if not self.device:
            logger.warning("No virtual device available")
            return

        # Determine if this is a press or release
        is_press = event.event_type == EventType.KEY_PRESS

        try:
            if is_press:
                # Press all keys in order
                for key_name in action.keys:
                    key_code = self.KEY_MAPPING.get(key_name)
                    if key_code:
                        self.device.write(evdev.ecodes.EV_KEY, key_code, 1)
                        self.device.syn()
                        logger.debug(f"Pressed key: {key_name}")
                    else:
                        logger.warning(f"Unknown key: {key_name}")
            else:
                # Release all keys in reverse order
                for key_name in reversed(action.keys):
                    key_code = self.KEY_MAPPING.get(key_name)
                    if key_code:
                        self.device.write(evdev.ecodes.EV_KEY, key_code, 0)
                        self.device.syn()
                        logger.debug(f"Released key: {key_name}")
                    else:
                        logger.warning(f"Unknown key: {key_name}")

        except Exception as e:
            logger.error(f"Error sending keyboard action: {e}")

    def get_supported_keys(self) -> List[str]:
        """Get list of supported key names."""
        return list(self.KEY_MAPPING.keys())

    def set_keybind_manager(self, keybind_manager: KeybindManager):
        """Set the keybind manager and rebuild capabilities."""
        self.keybind_manager = keybind_manager
        self.capabilities = self._build_capabilities()
        logger.info("Updated keybind manager and rebuilt capabilities")
