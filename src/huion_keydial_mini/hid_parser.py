"""HID data parser for the Huion Keydial Mini."""

from ast import Continue
import logging
import struct
from typing import List, NamedTuple, Optional, Dict, Any
from enum import Enum

from .config import Config


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of input events."""
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    DIAL_ROTATE = "dial_rotate"
    DIAL_CLICK = "dial_click"


class InputEvent(NamedTuple):
    """Represents an input event."""
    event_type: EventType
    key_code: Optional[str] = None
    direction: Optional[int] = None  # For dial rotation: 1 = clockwise, -1 = counterclockwise
    value: Optional[int] = None
    raw_data: Optional[bytearray] = None  # Store raw data for debugging


class HIDParser:
    """Parser for HID data from the Huion Keydial Mini."""

    def __init__(self, config: Config):
        self.config = config
        self.previous_state = {}
        self.report_formats = {}  # Cache discovered report formats
        self.debug_mode = getattr(config, 'debug_mode', False)

    def parse(self, data: bytearray, characteristic_uuid: Optional[str] = None) -> List[InputEvent]:
        """Parse HID data and return input events."""
        events = []

        try:
            # Log raw data for debugging
            if self.debug_mode:
                logger.debug(f"Parsing HID data: {data.hex()} (length: {len(data)}) from characteristic: {characteristic_uuid}")

            if len(data) < 1:
                logger.warning(f"Received empty HID report")
                return events

            # Parse based on data format rather than characteristic UUID
            # The device is using standard HID over GATT, so we need to parse the data directly

            # Try to parse as dial events first (f100/f103 format)
            dial_events = self._parse_dial_events(data)
            if dial_events:
                events.extend(dial_events)
                return events

            # Try to parse as button events (button ID format)
            button_events = self._parse_button_events(data)
            if button_events:
                events.extend(button_events)
                return events

        except Exception as e:
            logger.error(f"Error parsing HID data: {e}")
            if self.debug_mode:
                import traceback
                logger.debug(traceback.format_exc())

        return events

    def _extract_handle_from_uuid(self, uuid: str) -> str:
        """Extract handle from characteristic UUID."""
        # UUID format: "0000001f-0000-1000-8000-00805f9b34fb"
        # Extract the handle part (last 2 digits before the first dash)
        parts = uuid.split('-')
        if parts and len(parts[0]) >= 8:
            return parts[0][-2:]  # Last 2 characters
        return ""

    def _parse_button_events(self, data: bytearray) -> List[InputEvent]:
        """Parse button events from Handle 0x001f format."""
        events = []

        if len(data) < 8:
            return events

        # Validate that this is actually button data (not dial data)
        # Button data should NOT start with 0xf1 (which is dial data)
        if data[0] == 0xf1:
            # Not button data
            return events

        # Get current button names from data
        current_button_names = self._get_button_names_from_data(data)

        # Get previous button state
        previous_button_names = set(self.previous_state.get('button_names', []))

        # Find pressed buttons (new buttons)
        pressed_buttons = set(current_button_names) - previous_button_names
        # Find released buttons (buttons that were pressed before)
        released_buttons = previous_button_names - set(current_button_names)

        # Generate events for pressed buttons
        for button_name in pressed_buttons:
            key_code = button_name
            if key_code:
                events.append(InputEvent(
                    event_type=EventType.KEY_PRESS,
                    key_code=key_code,
                    raw_data=data
                ))

        # Generate events for released buttons
        for button_name in released_buttons:
            key_code = button_name
            if key_code:
                events.append(InputEvent(
                    event_type=EventType.KEY_RELEASE,
                    key_code=key_code,
                    raw_data=data
                ))

        # Update state
        self.previous_state['button_names'] = current_button_names

        return events

    def _get_button_names_from_data(self, data: bytearray) -> List[str]:
        """ Get button names from data """
        button_names = []
        # There are 2 types of button signals going on
        # First we'll handle type 1. Type 1 button combo signals start at the 4th byte,
        # and signal up to 3 buttons in 3 bytes. Order is not preserved.
        # Some 4 button combos are possible, but not all so we'll just use the first 3.
        type1_button_mappings = {
            0x0e: 'BUTTON_1',
            0x0a: 'BUTTON_2',
            0x0f: 'BUTTON_3',
            0x4c: 'BUTTON_4',
            0x0c: 'BUTTON_5',
            0x07: 'BUTTON_6',
            0x05: 'BUTTON_7',
            0x08: 'BUTTON_8',
            0x16: 'BUTTON_9',
            0x1d: 'BUTTON_10',
            0x06: 'BUTTON_11',
            0x19: 'BUTTON_12',
            0x28: 'BUTTON_16',
            0x2c: 'BUTTON_17',
            0x11: 'BUTTON_18',
        }

        for i in range(3, 6):
            button_name = type1_button_mappings.get(data[i])
            if button_name:
                button_names.append(button_name)

        # Now for type 2. Type 2 button combo signals use only the first byte using bitmasking.
        # The bits are:
        # button 13: bit 0
        # button 14: bit 2
        # button 15: bit 1
        type2_button_mappings = {
            0x01: 'BUTTON_13',
            0x04: 'BUTTON_14',
            0x02: 'BUTTON_15',
        }
        for key, value in type2_button_mappings.items():
            if data[0] & key:
                button_names.append(value)

        return button_names

    def _parse_dial_events(self, data: bytearray) -> List[InputEvent]:
        """Parse dial events from Handle 0x0034 format."""
        events = []

        if len(data) < 8:
            return events

        # Dial format: f1[clicked][count][direction]0000000000 (9 bytes)
        if data[0] == 0xf1:
            if data[2] == 0x00:
                # Dial click: f10300000000000000
                key_code = 'DIAL_CLICK'
                if data[1] == 0x03 and not self.previous_state.get('dial_clicked', False):
                    events.append(InputEvent(
                        event_type=EventType.KEY_PRESS,
                        key_code=key_code,
                        raw_data=data
                    ))
                    self.previous_state['dial_clicked'] = True
                elif data[1] == 0x00 and self.previous_state.get('dial_clicked', False):
                    events.append(InputEvent(
                        event_type=EventType.KEY_RELEASE,
                        key_code=key_code,
                        raw_data=data
                    ))
                    self.previous_state['dial_clicked'] = False
            else:
                # Dial rotation: f100[count][direction]0000000000
                count = data[2]
                direction_byte = data[3]

                # Determine direction
                if direction_byte == 0x00:
                    # Clockwise
                    direction = 1
                    key_code = 'DIAL_CW'
                elif direction_byte == 0xff:
                    # Counter-clockwise
                    direction = -1
                    key_code = 'DIAL_CCW'
                else:
                    # Unknown direction
                    return events

                # Calculate movement amount
                if direction == 1:
                    # Clockwise: count is the movement amount
                    movement = count
                else:
                    # Counter-clockwise: convert from signed byte
                    movement = 256 - count if count > 0 else 0

                # Generate events based on sensitivity
                sensitivity = self.config.dial_settings.get('sensitivity', 1.0)
                steps = max(1, int(movement * sensitivity))

                for _ in range(steps):
                    events.append(InputEvent(
                        event_type=EventType.KEY_PRESS,
                        key_code=key_code,
                        direction=direction,
                        value=movement,
                        raw_data=data
                    ))
                    events.append(InputEvent(
                        event_type=EventType.KEY_RELEASE,
                        key_code=key_code,
                        direction=direction,
                        value=movement,
                        raw_data=data
                    ))

        return events

    def reset_state(self):
        """Reset the parser state."""
        self.previous_state = {}
        logger.debug("Parser state reset")

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the parser state."""
        return {
            'previous_state': self.previous_state,
            'report_formats': self.report_formats,
            'debug_mode': self.debug_mode
        }
