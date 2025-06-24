"""HID data parser for the Huion Keydial Mini."""

import logging
import struct
from typing import List, NamedTuple, Optional
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


class HIDParser:
    """Parser for HID data from the Huion Keydial Mini."""

    def __init__(self, config: Config):
        self.config = config
        self.previous_state = {}

    def parse(self, data: bytearray) -> List[InputEvent]:
        """Parse HID data and return input events."""
        events = []

        try:
            # Log raw data for debugging
            logger.debug(f"Parsing HID data: {data.hex()}")

            # The exact format will depend on the device's HID report descriptor
            # This is a basic implementation that needs to be adapted based on
            # actual device behavior

            if len(data) < 2:
                logger.warning(f"Received short HID report: {len(data)} bytes")
                return events

            # Basic parsing - this will need to be customized based on actual device
            report_id = data[0] if len(data) > 0 else 0

            if report_id == 0x01:  # Assuming button report
                events.extend(self._parse_button_report(data))
            elif report_id == 0x02:  # Assuming dial report
                events.extend(self._parse_dial_report(data))
            else:
                # Try to parse as generic report
                events.extend(self._parse_generic_report(data))

        except Exception as e:
            logger.error(f"Error parsing HID data: {e}")

        return events

    def _parse_button_report(self, data: bytearray) -> List[InputEvent]:
        """Parse button press/release events."""
        events = []

        if len(data) < 2:
            return events

        button_state = data[1]
        previous_button_state = self.previous_state.get('buttons', 0)

        # Check each button bit
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
                        key_code=key_code
                    ))
                    logger.debug(f"Button {i + 1}: {'pressed' if current_pressed else 'released'}")

        self.previous_state['buttons'] = button_state
        return events

    def _parse_dial_report(self, data: bytearray) -> List[InputEvent]:
        """Parse dial rotation and click events."""
        events = []

        if len(data) < 3:
            return events

        # Assuming dial data is in bytes 1-2
        dial_delta = struct.unpack('<h', data[1:3])[0]  # Signed 16-bit

        if dial_delta != 0:
            # Normalize rotation direction
            direction = 1 if dial_delta > 0 else -1

            # Generate rotation events based on sensitivity
            sensitivity = self.config.dial_settings.get('sensitivity', 1.0)
            steps = abs(dial_delta) * sensitivity

            for _ in range(int(steps)):
                if direction > 0:
                    key_code = self.config.dial_settings.get('clockwise_key', 'KEY_VOLUMEUP')
                else:
                    key_code = self.config.dial_settings.get('counterclockwise_key', 'KEY_VOLUMEDOWN')

                events.append(InputEvent(
                    event_type=EventType.KEY_PRESS,
                    key_code=key_code
                ))
                events.append(InputEvent(
                    event_type=EventType.KEY_RELEASE,
                    key_code=key_code
                ))

            logger.debug(f"Dial rotated: {dial_delta} ({direction})")

        # Check for dial click (assuming bit in data[3] if available)
        if len(data) > 3:
            dial_click = bool(data[3] & 0x01)
            previous_dial_click = self.previous_state.get('dial_click', False)

            if dial_click != previous_dial_click:
                if dial_click:
                    key_code = self.config.dial_settings.get('click_key', 'KEY_ENTER')
                    events.append(InputEvent(
                        event_type=EventType.KEY_PRESS,
                        key_code=key_code
                    ))
                    events.append(InputEvent(
                        event_type=EventType.KEY_RELEASE,
                        key_code=key_code
                    ))
                    logger.debug("Dial clicked")

            self.previous_state['dial_click'] = dial_click

        return events

    def _parse_generic_report(self, data: bytearray) -> List[InputEvent]:
        """Parse generic HID report when report ID is unknown."""
        events = []

        # This is a fallback parser that tries to detect changes in the data
        # and map them to events. It's very basic and will need refinement.

        previous_data = self.previous_state.get('raw_data', bytearray())

        if len(previous_data) == len(data):
            # Look for changes in the data
            for i, (prev_byte, curr_byte) in enumerate(zip(previous_data, data)):
                if prev_byte != curr_byte:
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
                                        key_code=key_code
                                    ))

        self.previous_state['raw_data'] = bytearray(data)
        return events
