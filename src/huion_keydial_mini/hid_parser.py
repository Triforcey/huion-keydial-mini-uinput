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

    def parse(self, data: bytearray) -> List[InputEvent]:
        """Parse HID data and return input events."""
        events = []

        try:
            # Log raw data for debugging
            if self.debug_mode:
                logger.debug(f"Parsing HID data: {data.hex()} (length: {len(data)})")

            if len(data) < 1:
                logger.warning(f"Received empty HID report")
                return events

            # Try different parsing strategies
            parsed_events = []

            # Strategy 1: Try known Huion Keydial Mini format
            parsed_events = self._parse_huion_format(data)
            if parsed_events:
                events.extend(parsed_events)
                return events

            # Strategy 2: Try standard HID report format
            parsed_events = self._parse_standard_hid(data)
            if parsed_events:
                events.extend(parsed_events)
                return events

            # Strategy 3: Generic change detection
            parsed_events = self._parse_generic_report(data)
            if parsed_events:
                events.extend(parsed_events)

        except Exception as e:
            logger.error(f"Error parsing HID data: {e}")
            if self.debug_mode:
                import traceback
                logger.debug(traceback.format_exc())

        return events

    def _parse_huion_format(self, data: bytearray) -> List[InputEvent]:
        """Parse using known Huion Keydial Mini format."""
        events = []

        # Based on reverse engineering, Huion Keydial Mini typically sends:
        # - Button reports: [0x01, button_state, 0x00, 0x00, ...]
        # - Dial reports: [0x02, dial_delta_low, dial_delta_high, dial_click, ...]

        if len(data) < 2:
            return events

        report_type = data[0]

        if report_type == 0x01 and len(data) >= 2:
            # Button report
            events.extend(self._parse_button_report(data))
        elif report_type == 0x02 and len(data) >= 4:
            # Dial report
            events.extend(self._parse_dial_report(data))
        elif report_type == 0x00 and len(data) >= 8:
            # Combined report (buttons + dial)
            events.extend(self._parse_combined_report(data))

        return events

    def _parse_standard_hid(self, data: bytearray) -> List[InputEvent]:
        """Parse using standard HID report format."""
        events = []

        if len(data) < 2:
            return events

        # Standard HID reports often have:
        # - Report ID in first byte
        # - Button state in subsequent bytes
        # - Usage data for dial/scroll

        report_id = data[0]

        # Look for button state in common positions
        button_positions = [1, 2, 3]  # Common button state positions

        for pos in button_positions:
            if pos < len(data):
                button_state = data[pos]
                if button_state != 0:  # Non-zero button state
                    events.extend(self._parse_button_state(button_state, pos))

        # Look for dial data (often in bytes 4-5 or 6-7)
        if len(data) >= 6:
            # Try different positions for dial data
            dial_positions = [(4, 5), (6, 7), (2, 3)]

            for low_pos, high_pos in dial_positions:
                if high_pos < len(data):
                    try:
                        dial_delta = struct.unpack('<h', data[low_pos:high_pos+1])[0]
                        if dial_delta != 0:
                            events.extend(self._parse_dial_delta(dial_delta))
                            break
                    except struct.error:
                        continue

        return events

    def _parse_button_report(self, data: bytearray) -> List[InputEvent]:
        """Parse button press/release events."""
        events = []

        if len(data) < 2:
            return events

        button_state = data[1]
        previous_button_state = self.previous_state.get('buttons', 0)

        # Check each button bit (Huion Keydial Mini has 8 buttons)
        for i in range(8):
            mask = 1 << i
            current_pressed = bool(button_state & mask)
            previous_pressed = bool(previous_button_state & mask)

            if current_pressed != previous_pressed:
                button_name = f'button_{i + 1}'
                key_code = self.config.key_mappings.get(button_name)

                if key_code:
                    event_type = EventType.KEY_PRESS if current_pressed else EventType.KEY_RELEASE
                    events.append(InputEvent(
                        event_type=event_type,
                        key_code=key_code,
                        raw_data=data
                    ))
                    logger.debug(f"Button {i + 1}: {'pressed' if current_pressed else 'released'}")

        self.previous_state['buttons'] = button_state
        return events

    def _parse_dial_report(self, data: bytearray) -> List[InputEvent]:
        """Parse dial rotation and click events."""
        events = []

        if len(data) < 4:
            return events

        # Dial delta (signed 16-bit, little-endian)
        dial_delta = struct.unpack('<h', data[1:3])[0]

        # Dial click state (bit 0 of byte 3)
        dial_click = bool(data[3] & 0x01)

        # Handle dial rotation
        if dial_delta != 0:
            events.extend(self._parse_dial_delta(dial_delta))

        # Handle dial click
        previous_dial_click = self.previous_state.get('dial_click', False)
        if dial_click != previous_dial_click:
            if dial_click:
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
                logger.debug("Dial clicked")

        self.previous_state['dial_click'] = dial_click
        return events

    def _parse_combined_report(self, data: bytearray) -> List[InputEvent]:
        """Parse combined button and dial report."""
        events = []

        # Combined format: [0x00, buttons_low, buttons_high, dial_delta_low, dial_delta_high, dial_click, ...]
        if len(data) < 6:
            return events

        # Parse buttons (16-bit, but we only use first 8 bits)
        button_state = data[1]
        events.extend(self._parse_button_report(bytearray([0x01, button_state])))

        # Parse dial
        dial_delta = struct.unpack('<h', data[3:5])[0]
        if dial_delta != 0:
            events.extend(self._parse_dial_delta(dial_delta))

        # Parse dial click
        dial_click = bool(data[5] & 0x01)
        previous_dial_click = self.previous_state.get('dial_click', False)
        if dial_click != previous_dial_click:
            if dial_click:
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

        self.previous_state['dial_click'] = dial_click
        return events

    def _parse_button_state(self, button_state: int, position: int) -> List[InputEvent]:
        """Parse button state from a specific position."""
        events = []
        previous_state = self.previous_state.get(f'buttons_pos_{position}', 0)

        # Only process if there's an actual change
        if button_state == previous_state:
            return events

        for i in range(8):
            mask = 1 << i
            current_pressed = bool(button_state & mask)
            previous_pressed = bool(previous_state & mask)

            if current_pressed != previous_pressed:
                button_name = f'button_{i + 1}'
                key_code = self.config.key_mappings.get(button_name)

                if key_code:
                    event_type = EventType.KEY_PRESS if current_pressed else EventType.KEY_RELEASE
                    events.append(InputEvent(
                        event_type=event_type,
                        key_code=key_code
                    ))

        self.previous_state[f'buttons_pos_{position}'] = button_state
        return events

    def _parse_dial_delta(self, dial_delta: int) -> List[InputEvent]:
        """Parse dial rotation delta."""
        events = []

        # Normalize rotation direction
        direction = 1 if dial_delta > 0 else -1

        # Generate rotation events based on sensitivity
        sensitivity = self.config.dial_settings.get('sensitivity', 1.0)
        # Limit the number of steps to prevent excessive events
        steps = min(max(1, int(abs(dial_delta) * sensitivity)), 10)  # Max 10 steps

        for _ in range(steps):
            if direction > 0:
                key_code = self.config.dial_settings.get('clockwise_key', 'KEY_VOLUMEUP')
            else:
                key_code = self.config.dial_settings.get('counterclockwise_key', 'KEY_VOLUMEDOWN')

            events.append(InputEvent(
                event_type=EventType.KEY_PRESS,
                key_code=key_code,
                direction=direction,
                value=dial_delta
            ))
            events.append(InputEvent(
                event_type=EventType.KEY_RELEASE,
                key_code=key_code,
                direction=direction,
                value=dial_delta
            ))

        logger.debug(f"Dial rotated: {dial_delta} ({direction}) - {steps} steps")
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
