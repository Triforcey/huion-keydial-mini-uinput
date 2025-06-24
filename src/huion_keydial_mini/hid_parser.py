"""HID data parser for the Huion Keydial Mini."""

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

            # Fallback to generic parsing
            events.extend(self._parse_generic_report(data))

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

        # Button format: [button_ids]00000000 (8 bytes)
        # Looking at the actual data: 0000002800000000
        # The button ID (28) is in the 4th byte position, not the first

        # Extract button identifiers from all non-zero bytes
        button_ids = []
        for i in range(8):
            if data[i] != 0:
                button_ids.append(data[i])

        # Get previous button state
        previous_ids = set(self.previous_state.get('button_ids', []))

        # Find pressed buttons (new buttons)
        pressed_buttons = set(button_ids) - previous_ids
        # Find released buttons (buttons that were pressed before)
        released_buttons = previous_ids - set(button_ids)

        # Generate events for pressed buttons
        for button_id in pressed_buttons:
            button_name = self._get_button_name_from_id(button_id)
            if button_name:
                key_code = self.config.key_mappings.get(button_name)
                if key_code:
                    events.append(InputEvent(
                        event_type=EventType.KEY_PRESS,
                        key_code=key_code,
                        raw_data=data
                    ))

        # Generate events for released buttons
        for button_id in released_buttons:
            button_name = self._get_button_name_from_id(button_id)
            if button_name:
                key_code = self.config.key_mappings.get(button_name)
                if key_code:
                    events.append(InputEvent(
                        event_type=EventType.KEY_RELEASE,
                        key_code=key_code,
                        raw_data=data
                    ))

        # Update state
        self.previous_state['button_ids'] = button_ids

        return events

    def _get_button_name_from_id(self, button_id: int) -> Optional[str]:
        """Map button ID to button name based on btmon analysis."""
        # Button ID mapping from btmon analysis
        button_mapping = {
            0x0e: 'button_1',
            0x0a: 'button_2',
            0x0f: 'button_3',
            0x4c: 'button_4',
            0x0c: 'button_5',
            0x07: 'button_6',
            0x05: 'button_7',
            0x08: 'button_8',
            0x16: 'button_9',
            0x1d: 'button_10',
            0x06: 'button_11',
            0x19: 'button_12',
            0x01: 'button_13',  # 0100000000000000
            0x04: 'button_14',  # 0400000000000000
            0x02: 'button_15',  # 0200000000000000
            0x28: 'button_16',  # 0000002800000000
            0x2c: 'button_17',  # 0000002c00000000
            0x11: 'button_18',  # 0000001100000000
        }

        return button_mapping.get(button_id)

    def _parse_dial_events(self, data: bytearray) -> List[InputEvent]:
        """Parse dial events from Handle 0x0034 format."""
        events = []

        if len(data) < 9:
            return events

        # Dial format: f100[count][direction]0000000000 (9 bytes)
        if data[0] == 0xf1 and data[1] == 0x00:
            if data[2] == 0x03 and data[3] == 0x00:
                # Dial click: f10300000000000000
                key_code = self.config.dial_settings.get('click_key', 'KEY_ENTER')
                events.append(InputEvent(
                    event_type=EventType.KEY_PRESS,
                    key_code=key_code,
                    raw_data=data
                ))
                events.append(InputEvent(
                    event_type=EventType.KEY_RELEASE,
                    key_code=key_code,
                    raw_data=data
                ))
            elif data[2] == 0x00 and data[3] == 0x00:
                # Dial release: f10000000000000000
                # No action needed for release
                pass
            else:
                # Dial rotation: f100[count][direction]0000000000
                count = data[2]
                direction_byte = data[3]

                # Determine direction
                if direction_byte == 0x00:
                    # Clockwise
                    direction = 1
                    key_code = self.config.dial_settings.get('clockwise_key', 'KEY_VOLUMEUP')
                elif direction_byte == 0xff:
                    # Counter-clockwise
                    direction = -1
                    key_code = self.config.dial_settings.get('counterclockwise_key', 'KEY_VOLUMEDOWN')
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

    def _parse_generic_report(self, data: bytearray) -> List[InputEvent]:
        """Parse generic HID report when format is unknown."""
        events = []

        # This is a fallback parser that tries to detect changes in the data
        # and map them to events. It's very basic and will need refinement.

        previous_data = self.previous_state.get('raw_data', bytearray())

        if len(previous_data) == len(data):
            # Look for changes in the data
            for i, (prev_byte, curr_byte) in enumerate(zip(previous_data, data)):
                if prev_byte != curr_byte:
                    if self.debug_mode:
                        logger.debug(f"Data change at byte {i}: {prev_byte:02x} -> {curr_byte:02x}")

                    # Try to interpret as button state
                    if i == 1:  # Assume byte 1 might be button state
                        changed_bits = prev_byte ^ curr_byte
                        for bit in range(8):
                            if changed_bits & (1 << bit):
                                button_name = f'button_{bit + 1}'
                                key_code = self.config.key_mappings.get(button_name)

                                if key_code:
                                    pressed = bool(curr_byte & (1 << bit))
                                    event_type = EventType.KEY_PRESS if pressed else EventType.KEY_RELEASE
                                    events.append(InputEvent(
                                        event_type=event_type,
                                        key_code=key_code,
                                        raw_data=data
                                    ))

        self.previous_state['raw_data'] = bytearray(data)
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
