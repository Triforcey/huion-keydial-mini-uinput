"""Tests for button combo detection in HID parser."""

import pytest
from unittest.mock import Mock, patch

from huion_keydial_mini.hid_parser import HIDParser, EventType, InputEvent
from huion_keydial_mini.config import Config


class ComboHIDTestData:
    """Test data for combo functionality."""

    # Individual button presses (type 1 format - bytes 3-5)
    BUTTON_1_ONLY = bytearray([0x00, 0x00, 0x00, 0x0e, 0x00, 0x00, 0x00, 0x00])  # Button 1 only
    BUTTON_2_ONLY = bytearray([0x00, 0x00, 0x00, 0x0a, 0x00, 0x00, 0x00, 0x00])  # Button 2 only
    BUTTON_3_ONLY = bytearray([0x00, 0x00, 0x00, 0x0f, 0x00, 0x00, 0x00, 0x00])  # Button 3 only

    # Two-button combinations
    BUTTON_1_2 = bytearray([0x00, 0x00, 0x00, 0x0e, 0x0a, 0x00, 0x00, 0x00])     # Buttons 1+2
    BUTTON_1_3 = bytearray([0x00, 0x00, 0x00, 0x0e, 0x0f, 0x00, 0x00, 0x00])     # Buttons 1+3
    BUTTON_2_3 = bytearray([0x00, 0x00, 0x00, 0x0a, 0x0f, 0x00, 0x00, 0x00])     # Buttons 2+3

    # Three-button combinations
    BUTTON_1_2_3 = bytearray([0x00, 0x00, 0x00, 0x0e, 0x0a, 0x0f, 0x00, 0x00])  # Buttons 1+2+3

    # No buttons pressed
    NO_BUTTONS = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


@pytest.fixture
def combo_test_data():
    """Provide combo test data."""
    return ComboHIDTestData()


@pytest.fixture
def combo_config():
    """Create a config with combo mappings."""
    return Config({
        'key_mappings': {
            # Individual buttons
            'BUTTON_1': 'KEY_F1',
            'BUTTON_2': 'KEY_F2',
            'BUTTON_3': 'KEY_F3',

            # Button combos
            'BUTTON_1+BUTTON_2': 'KEY_CTRL+KEY_C',
            'BUTTON_1+BUTTON_3': 'KEY_CTRL+KEY_V',
            'BUTTON_2+BUTTON_3': 'KEY_CTRL+KEY_Z',
            'BUTTON_1+BUTTON_2+BUTTON_3': 'KEY_CTRL+KEY_SHIFT+KEY_Z',
        },
        'dial_settings': {},
        'debug_mode': True
    })


@pytest.fixture
def combo_parser(combo_config):
    """Create a HIDParser with combo support."""
    return HIDParser(combo_config)


class TestComboHIDParser:
    """Test cases for combo detection in HID parser."""

    @pytest.mark.combo
    def test_combo_parser_initialization(self, combo_parser):
        """Test combo parser initialization."""
        assert combo_parser.peak_buttons_this_session == set()
        assert combo_parser.key_event_triggered is False
        assert combo_parser.previous_state == {}

    @pytest.mark.combo
    def test_single_button_press_release(self, combo_parser, combo_test_data):
        """Test individual button press/release generates correct events."""
        # Press button 1
        events = combo_parser._parse_button_events(combo_test_data.BUTTON_1_ONLY)
        assert events == []  # No events on press
        assert combo_parser.peak_buttons_this_session == {'BUTTON_1'}
        assert combo_parser.key_event_triggered is False

        # Release button 1
        events = combo_parser._parse_button_events(combo_test_data.NO_BUTTONS)
        assert len(events) == 2  # Press + Release
        assert events[0].event_type == EventType.KEY_PRESS
        assert events[0].key_code == 'BUTTON_1'
        assert events[1].event_type == EventType.KEY_RELEASE
        assert events[1].key_code == 'BUTTON_1'
        assert combo_parser.key_event_triggered is True
        assert combo_parser.peak_buttons_this_session == set()

    @pytest.mark.combo
    def test_two_button_combo_sequence(self, combo_parser, combo_test_data):
        """Test two-button combo triggers correctly."""
        # Press button 1
        events = combo_parser._parse_button_events(combo_test_data.BUTTON_1_ONLY)
        assert events == []
        assert combo_parser.peak_buttons_this_session == {'BUTTON_1'}

        # Press button 2 (while 1 held)
        events = combo_parser._parse_button_events(combo_test_data.BUTTON_1_2)
        assert events == []
        assert combo_parser.peak_buttons_this_session == {'BUTTON_1', 'BUTTON_2'}
        assert combo_parser.key_event_triggered is False

        # Release button 1 (should trigger combo)
        events = combo_parser._parse_button_events(combo_test_data.BUTTON_2_ONLY)
        assert len(events) == 2  # Press + Release of combo
        assert events[0].event_type == EventType.KEY_PRESS
        assert events[0].key_code == 'BUTTON_1+BUTTON_2'
        assert events[1].event_type == EventType.KEY_RELEASE
        assert events[1].key_code == 'BUTTON_1+BUTTON_2'
        assert combo_parser.key_event_triggered is True

        # Release button 2 (should not trigger anything)
        events = combo_parser._parse_button_events(combo_test_data.NO_BUTTONS)
        assert events == []  # No events due to key_event_triggered flag

    @pytest.mark.combo
    def test_three_button_combo_sequence(self, combo_parser, combo_test_data):
        """Test three-button combo triggers correctly."""
        # Build up to three buttons
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_ONLY)
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_2)
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_2_3)

        assert combo_parser.peak_buttons_this_session == {'BUTTON_1', 'BUTTON_2', 'BUTTON_3'}

        # Release one button (should trigger 3-button combo)
        events = combo_parser._parse_button_events(combo_test_data.BUTTON_1_2)
        assert len(events) == 2
        assert events[0].key_code == 'BUTTON_1+BUTTON_2+BUTTON_3'

    @pytest.mark.combo
    def test_combo_id_generation(self, combo_parser):
        """Test combo ID generation and normalization."""
        # Test sorted combo ID generation
        result = combo_parser._generate_combo_id({'BUTTON_3', 'BUTTON_1', 'BUTTON_2'})
        assert result == 'BUTTON_1+BUTTON_2+BUTTON_3'

        # Test empty set
        result = combo_parser._generate_combo_id(set())
        assert result == ''

        # Test single button (not really a combo)
        result = combo_parser._generate_combo_id({'BUTTON_1'})
        assert result == 'BUTTON_1'

    @pytest.mark.combo
    def test_rapid_fire_combos(self, combo_parser, combo_test_data):
        """Test rapid-fire combo scenario (hold button 1, tap others)."""
        # Press button 1
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_ONLY)

        # Press button 2, release button 2 (should trigger BUTTON_1+BUTTON_2)
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_2)
        events = combo_parser._parse_button_events(combo_test_data.BUTTON_1_ONLY)
        assert len(events) == 2
        assert events[0].key_code == 'BUTTON_1+BUTTON_2'

        # Now press button 3, release button 3 (should trigger BUTTON_1+BUTTON_3)
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_3)
        events = combo_parser._parse_button_events(combo_test_data.BUTTON_1_ONLY)
        assert len(events) == 2
        assert events[0].key_code == 'BUTTON_1+BUTTON_3'

        # Release button 1 (session ends, no more events)
        events = combo_parser._parse_button_events(combo_test_data.NO_BUTTONS)
        assert events == []

    @pytest.mark.combo
    def test_key_event_triggered_reset_on_new_button(self, combo_parser, combo_test_data):
        """Test that key_event_triggered resets when new buttons are pressed."""
        # Trigger a combo first
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_ONLY)
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_2)
        combo_parser._parse_button_events(combo_test_data.BUTTON_2_ONLY)  # Triggers combo
        assert combo_parser.key_event_triggered is True

        # Press a new button (should reset flag)
        combo_parser._parse_button_events(combo_test_data.BUTTON_2_3)
        assert combo_parser.key_event_triggered is False

    @pytest.mark.combo
    def test_peak_button_tracking_with_different_combinations(self, combo_parser, combo_test_data):
        """Test peak button tracking with various button combinations."""
        # Start with button 1
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_ONLY)
        assert combo_parser.peak_buttons_this_session == {'BUTTON_1'}

        # Add button 2 (new peak)
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_2)
        assert combo_parser.peak_buttons_this_session == {'BUTTON_1', 'BUTTON_2'}

        # Change to button 1+3 (different combination, same size)
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_3)
        assert combo_parser.peak_buttons_this_session == {'BUTTON_1', 'BUTTON_3'}

        # Add button 2 back (new peak with 3 buttons)
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_2_3)
        assert combo_parser.peak_buttons_this_session == {'BUTTON_1', 'BUTTON_2', 'BUTTON_3'}

    @pytest.mark.combo
    def test_session_reset_conditions(self, combo_parser, combo_test_data):
        """Test when combo sessions reset correctly."""
        # Build up a combo session
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_2)
        combo_parser._parse_button_events(combo_test_data.BUTTON_1_ONLY)  # Trigger combo

        assert combo_parser.peak_buttons_this_session == {'BUTTON_1', 'BUTTON_2'}
        assert combo_parser.key_event_triggered is True

        # Release all buttons (should reset everything)
        combo_parser._parse_button_events(combo_test_data.NO_BUTTONS)
        assert combo_parser.peak_buttons_this_session == set()
        assert combo_parser.key_event_triggered is False

    @pytest.mark.combo
    def test_combo_normalization_consistency(self, combo_parser):
        """Test that combo ID normalization is consistent regardless of input order."""
        # Test various orders of the same buttons
        combinations = [
            {'BUTTON_1', 'BUTTON_2', 'BUTTON_3'},
            {'BUTTON_3', 'BUTTON_1', 'BUTTON_2'},
            {'BUTTON_2', 'BUTTON_3', 'BUTTON_1'},
        ]

        expected = 'BUTTON_1+BUTTON_2+BUTTON_3'
        for combo in combinations:
            result = combo_parser._generate_combo_id(combo)
            assert result == expected, f"Combo {combo} should normalize to {expected}, got {result}"

    @pytest.mark.combo
    def test_no_mapping_no_event(self, combo_parser, combo_test_data):
        """Test that combinations without mappings don't generate events."""
        # Create parser without combo mappings
        no_combo_config = Config({
            'key_mappings': {
                'BUTTON_1': 'KEY_F1',  # Only individual mappings
                'BUTTON_2': 'KEY_F2',
            },
            'dial_settings': {},
            'debug_mode': True
        })
        parser = HIDParser(no_combo_config)

        # Try combo sequence
        parser._parse_button_events(combo_test_data.BUTTON_1_2)
        events = parser._parse_button_events(combo_test_data.BUTTON_1_ONLY)

        # Should not generate combo events since no mapping exists
        assert events == []
        assert parser.key_event_triggered is False
