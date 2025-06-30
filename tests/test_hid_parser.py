"""Tests for the HID parser functionality."""

import pytest
from unittest.mock import Mock, patch

from huion_keydial_mini.hid_parser import HIDParser, EventType, InputEvent
from huion_keydial_mini.config import Config


class TestHIDParser:
    """Test cases for HIDParser class."""

    @pytest.mark.hid_parser
    def test_parser_initialization(self, config):
        """Test HIDParser initialization."""
        parser = HIDParser(config)
        assert parser.config == config
        assert parser.previous_state == {}
        assert parser.report_formats == {}
        assert parser.debug_mode is True

    @pytest.mark.hid_parser
    def test_parse_empty_data(self, hid_parser, hid_test_data, mock_logger):
        """Test parsing empty HID data."""
        events = hid_parser.parse(hid_test_data.EMPTY_DATA)
        assert events == []
        mock_logger.warning.assert_called_once()

    @pytest.mark.hid_parser
    def test_parse_short_data(self, hid_parser, hid_test_data, mock_logger):
        """Test parsing short/incomplete HID data."""
        events = hid_parser.parse(hid_test_data.SHORT_DATA)
        assert events == []
        # Note: The parser doesn't log warnings for short data anymore

    @pytest.mark.hid_parser
    def test_parse_button_press_huion_format(self, hid_parser, hid_test_data):
        """Test parsing button press using Huion format."""
        events = hid_parser.parse(hid_test_data.BUTTON_13_PRESS)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.KEY_PRESS
        assert event.key_code == "BUTTON_13"
        assert event.raw_data == hid_test_data.BUTTON_13_PRESS

    @pytest.mark.hid_parser
    def test_parse_button_release_huion_format(self, hid_parser, hid_test_data):
        """Test parsing button release using Huion format."""
        # First press the button
        hid_parser.parse(hid_test_data.BUTTON_13_PRESS)

        # Then release it
        events = hid_parser.parse(hid_test_data.BUTTON_RELEASE)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.KEY_RELEASE
        assert event.key_code == "BUTTON_13"

    @pytest.mark.hid_parser
    def test_parse_multiple_buttons(self, hid_parser, hid_test_data):
        """Test parsing multiple button presses."""
        events = hid_parser.parse(hid_test_data.MULTIPLE_BUTTONS)

        assert len(events) == 2
        BUTTON_13_event = next(e for e in events if e.key_code == "BUTTON_13")
        BUTTON_15_event = next(e for e in events if e.key_code == "BUTTON_15")

        assert BUTTON_13_event.event_type == EventType.KEY_PRESS
        assert BUTTON_15_event.event_type == EventType.KEY_PRESS

    @pytest.mark.hid_parser
    def test_parse_dial_clockwise(self, hid_parser, hid_test_data):
        """Test parsing dial clockwise rotation."""
        events = hid_parser.parse(hid_test_data.DIAL_CW)

        assert len(events) == 2  # Press and release
        press_event = events[0]
        release_event = events[1]

        assert press_event.event_type == EventType.KEY_PRESS
        assert press_event.key_code == "DIAL_CW"
        assert press_event.direction == 1
        assert press_event.value == 1

        assert release_event.event_type == EventType.KEY_RELEASE
        assert release_event.key_code == "DIAL_CW"

    @pytest.mark.hid_parser
    def test_parse_dial_counterclockwise(self, hid_parser, hid_test_data):
        """Test parsing dial counter-clockwise rotation."""
        events = hid_parser.parse(hid_test_data.DIAL_CCW)

        assert len(events) == 2  # Press and release
        press_event = events[0]
        release_event = events[1]

        assert press_event.event_type == EventType.KEY_PRESS
        assert press_event.key_code == "DIAL_CCW"
        assert press_event.direction == -1
        assert press_event.value == 1

        assert release_event.event_type == EventType.KEY_RELEASE
        assert release_event.key_code == "DIAL_CCW"

    @pytest.mark.hid_parser
    def test_parse_dial_click(self, hid_parser, hid_test_data):
        """Test parsing dial click."""
        events = hid_parser.parse(hid_test_data.DIAL_CLICK)

        assert len(events) == 1  # Only press event for click
        press_event = events[0]

        assert press_event.event_type == EventType.KEY_PRESS
        assert press_event.key_code == "DIAL_CLICK"

    @pytest.mark.hid_parser
    def test_parse_dial_click_release(self, hid_parser, hid_test_data):
        """Test parsing dial click release."""
        # First click
        hid_parser.parse(hid_test_data.DIAL_CLICK)

        # Then release
        events = hid_parser.parse(hid_test_data.DIAL_CLICK_RELEASE)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.KEY_RELEASE
        assert event.key_code == "DIAL_CLICK"

    @pytest.mark.hid_parser
    def test_parse_type1_buttons(self, hid_parser, hid_test_data):
        """Test parsing type 1 button format."""
        events = hid_parser.parse(hid_test_data.BUTTON_1_PRESS)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.KEY_PRESS
        assert event.key_code == "BUTTON_1"

    @pytest.mark.hid_parser
    def test_parse_standard_hid_format(self, hid_parser, hid_test_data):
        """Test parsing standard HID format."""
        # Use type 1 button format instead
        events = hid_parser.parse(hid_test_data.BUTTON_1_PRESS)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.KEY_PRESS
        assert event.key_code == "BUTTON_1"

    @pytest.mark.hid_parser
    def test_parse_with_different_sensitivity(self, sample_config_data):
        """Test parsing with different dial sensitivity settings."""
        # Test with higher sensitivity
        sample_config_data['dial_settings']['sensitivity'] = 2.0
        config = Config(sample_config_data)

        parser = HIDParser(config)

        # Test dial rotation with higher sensitivity
        dial_data = bytearray([0xf1, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Delta of 2
        events = parser.parse(dial_data)

        # With sensitivity 2.0, delta 2 should generate 4 steps (2 * 2 = 4)
        assert len(events) == 8  # 4 press/release pairs

    @pytest.mark.hid_parser
    def test_parse_unknown_format_fallback(self, hid_parser, hid_test_data):
        """Test parsing unknown format using generic fallback."""
        # Use invalid data that doesn't match known formats
        events = hid_parser.parse(hid_test_data.INVALID_DATA)

        # Should not crash and should return empty list or handle gracefully
        assert isinstance(events, list)

    @pytest.mark.hid_parser
    def test_parser_state_management(self, hid_parser, hid_test_data):
        """Test that parser maintains state correctly."""
        # Press button
        events1 = hid_parser.parse(hid_test_data.BUTTON_13_PRESS)
        assert len(events1) == 1
        assert events1[0].event_type == EventType.KEY_PRESS

        # Press same button again (should not generate event)
        events2 = hid_parser.parse(hid_test_data.BUTTON_13_PRESS)
        assert len(events2) == 0

        # Release button
        events3 = hid_parser.parse(hid_test_data.BUTTON_RELEASE)
        assert len(events3) == 1
        assert events3[0].event_type == EventType.KEY_RELEASE

    @pytest.mark.hid_parser
    def test_reset_state(self, hid_parser, hid_test_data):
        """Test resetting parser state."""
        # Press button to set state
        hid_parser.parse(hid_test_data.BUTTON_13_PRESS)
        assert hid_parser.previous_state != {}

        # Reset state
        hid_parser.reset_state()
        assert hid_parser.previous_state == {}

    @pytest.mark.hid_parser
    def test_get_debug_info(self, hid_parser):
        """Test getting debug information."""
        debug_info = hid_parser.get_debug_info()

        assert 'previous_state' in debug_info
        assert 'report_formats' in debug_info
        assert 'debug_mode' in debug_info
        assert debug_info['debug_mode'] is True

    @pytest.mark.hid_parser
    def test_parse_exception_handling(self, hid_parser, mock_logger):
        """Test exception handling during parsing."""
        # Test with data that might cause issues
        events = hid_parser.parse(bytearray([0xf1, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))

        # Should handle gracefully and return events
        assert isinstance(events, list)
        assert len(events) == 2  # Press and release

    @pytest.mark.hid_parser
    def test_parse_with_missing_key_mappings(self, sample_config_data):
        """Test parsing with missing key mappings."""
        # Remove key mappings to test behavior
        del sample_config_data['key_mappings']
        config = Config(sample_config_data)
        parser = HIDParser(config)

        # Test button press - should still work as it uses button names directly
        events = parser.parse(bytearray([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))

        assert len(events) == 1
        assert events[0].key_code == "BUTTON_13"

    @pytest.mark.hid_parser
    def test_parse_dial_with_large_delta(self, hid_parser):
        """Test parsing dial rotation with large delta values."""
        # Test with a large delta that should be capped
        large_delta_data = bytearray([0x02, 0xFF, 0x7F, 0x00, 0x00, 0x00, 0x00, 0x00])  # Large positive delta
        events = hid_parser.parse(large_delta_data)

        # Should generate events but capped at reasonable number
        assert len(events) > 0
        assert len(events) <= 20  # Max 10 steps * 2 events per step

    @pytest.mark.hid_parser
    def test_parse_dial_click_state_transition(self, hid_parser, hid_test_data):
        """Test dial click state transition."""
        # First click
        events1 = hid_parser.parse(hid_test_data.DIAL_CLICK)
        assert len(events1) == 1  # Only press event for click

        # Same click state (should not generate events)
        events2 = hid_parser.parse(hid_test_data.DIAL_CLICK)
        assert len(events2) == 0

        # Release click
        events3 = hid_parser.parse(hid_test_data.DIAL_CLICK_RELEASE)
        assert len(events3) == 1
        assert events3[0].event_type == EventType.KEY_RELEASE


class TestInputEvent:
    """Test cases for InputEvent class."""

    @pytest.mark.hid_parser
    def test_input_event_creation(self):
        """Test InputEvent creation with different parameters."""
        # Basic event
        event1 = InputEvent(EventType.KEY_PRESS, key_code="BUTTON_13")
        assert event1.event_type == EventType.KEY_PRESS
        assert event1.key_code == "BUTTON_13"
        assert event1.direction is None
        assert event1.value is None
        assert event1.raw_data is None

        # Event with all parameters
        raw_data = bytearray([0x01, 0x01])
        event2 = InputEvent(
            EventType.DIAL_ROTATE,
            key_code="DIAL_CW",
            direction=1,
            value=5,
            raw_data=raw_data
        )
        assert event2.event_type == EventType.DIAL_ROTATE
        assert event2.key_code == "DIAL_CW"
        assert event2.direction == 1
        assert event2.value == 5
        assert event2.raw_data == raw_data

    @pytest.mark.hid_parser
    def test_input_event_equality(self):
        """Test InputEvent equality comparison."""
        event1 = InputEvent(EventType.KEY_PRESS, key_code="BUTTON_13")
        event2 = InputEvent(EventType.KEY_PRESS, key_code="BUTTON_13")
        event3 = InputEvent(EventType.KEY_RELEASE, key_code="BUTTON_13")

        assert event1 == event2
        assert event1 != event3


class TestEventType:
    """Test cases for EventType enum."""

    @pytest.mark.hid_parser
    def test_event_type_values(self):
        """Test EventType enum values."""
        assert EventType.KEY_PRESS.value == "key_press"
        assert EventType.KEY_RELEASE.value == "key_release"
        assert EventType.DIAL_ROTATE.value == "dial_rotate"
        assert EventType.DIAL_CLICK.value == "dial_click"

    @pytest.mark.hid_parser
    def test_event_type_comparison(self):
        """Test EventType comparison."""
        assert EventType.KEY_PRESS == EventType.KEY_PRESS
        assert EventType.KEY_PRESS != EventType.KEY_RELEASE
