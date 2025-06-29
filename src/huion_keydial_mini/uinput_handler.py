"""UInput handler for generating Linux input events."""

import asyncio
import logging
from typing import List, Optional, Dict
import evdev
from evdev import UInput, ecodes

from .config import Config
from .hid_parser import InputEvent, EventType
from .keybind_manager import KeybindManager, KeybindAction, EventType as BindEventType


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
        'KEY_1': ecodes.KEY_1,
        'KEY_2': ecodes.KEY_2,
        'KEY_3': ecodes.KEY_3,
        'KEY_4': ecodes.KEY_4,
        'KEY_5': ecodes.KEY_5,
        'KEY_6': ecodes.KEY_6,
        'KEY_7': ecodes.KEY_7,
        'KEY_8': ecodes.KEY_8,
        'KEY_9': ecodes.KEY_9,
        'KEY_0': ecodes.KEY_0,
    }

    def __init__(self, config: Config, keybind_manager: Optional[KeybindManager] = None):
        self.config = config
        self.keybind_manager = keybind_manager
        self.device: Optional[UInput] = None
        self.capabilities = self._build_capabilities()
        self._try_open_device()

    def _try_open_device(self):
        """Try to open the existing uinput device."""
        try:
            self.device = UInput(events=self.capabilities, name=self.config.uinput_device_name)
        except Exception as e:
            logger.warning(f"Could not open uinput device '{self.config.uinput_device_name}': {e}")
            self.device = None

    def _build_capabilities(self) -> Dict:
        """Build device capabilities based on configuration and keybind manager."""
        capabilities = {
            evdev.ecodes.EV_KEY: [],
            # Remove mouse and relative events for pure keyboard emulation
            # evdev.ecodes.EV_REL: [evdev.ecodes.REL_X, evdev.ecodes.REL_Y, evdev.ecodes.REL_WHEEL],
            evdev.ecodes.EV_ABS: [],
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
            elif action.type == BindEventType.MOUSE:
                await self._send_mouse_action(action, event)
            elif action.type == BindEventType.COMBO:
                await self._send_combo_action(action, event)
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

    async def _send_mouse_action(self, action: KeybindAction, event: InputEvent):
        """Send a mouse action."""
        if not action.mouse_action:
            logger.warning("Mouse action has no action defined")
            return

        if not self.device:
            logger.warning("No virtual device available")
            return

        try:
            if action.mouse_action == "scroll":
                # Handle scroll events
                if event.direction:
                    scroll_amount = event.direction * 3  # Adjust sensitivity
                    self.device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_WHEEL, scroll_amount)
                    self.device.syn()
                    logger.debug(f"Mouse scroll: {scroll_amount}")

            elif action.mouse_action == "click":
                # Handle mouse clicks
                if action.mouse_button == "left":
                    button_code = evdev.ecodes.BTN_LEFT
                elif action.mouse_button == "right":
                    button_code = evdev.ecodes.BTN_RIGHT
                elif action.mouse_button == "middle":
                    button_code = evdev.ecodes.BTN_MIDDLE
                else:
                    button_code = evdev.ecodes.BTN_LEFT  # Default to left

                is_press = event.event_type == EventType.KEY_PRESS
                value = 1 if is_press else 0

                self.device.write(evdev.ecodes.EV_KEY, button_code, value)
                self.device.syn()
                logger.debug(f"Mouse {action.mouse_button} click: {value}")

        except Exception as e:
            logger.error(f"Error sending mouse action: {e}")

    async def _send_combo_action(self, action: KeybindAction, event: InputEvent):
        """Send a combo action (keyboard + mouse)."""
        # For now, treat combo as keyboard action
        # This can be expanded later for true keyboard+mouse combos
        await self._send_keyboard_action(action, event)

    def get_supported_keys(self) -> List[str]:
        """Get list of supported key names."""
        return list(self.KEY_MAPPING.keys())

    def set_keybind_manager(self, keybind_manager: KeybindManager):
        """Set the keybind manager and rebuild capabilities."""
        self.keybind_manager = keybind_manager
        self.capabilities = self._build_capabilities()
        logger.info("Updated keybind manager and rebuilt capabilities")
