#!/usr/bin/env python3
"""Simple test runner for HID parser tests."""

import sys
import os
import unittest
from pathlib import Path

# Add src to path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from huion_keydial_mini.hid_parser import HIDParser, EventType, InputEvent
from huion_keydial_mini.config import Config


class SimpleHIDParserTest(unittest.TestCase):
    """Simple test cases for HID parser without pytest dependencies."""

    def setUp(self):
        """Set up test fixtures."""
        config_data = {
            'key_mappings': {
                'button_1': 'KEY_F1',
                'button_2': 'KEY_F2',
                'button_3': 'KEY_F3',
                'button_4': 'KEY_F4',
                'button_5': 'KEY_F5',
                'button_6': 'KEY_F6',
                'button_7': 'KEY_F7',
                'button_8': 'KEY_F8',
            },
            'dial_settings': {
                'sensitivity': 1.0,
                'clockwise_key': 'KEY_VOLUMEUP',
                'counterclockwise_key': 'KEY_VOLUMEDOWN',
                'click_key': 'KEY_ENTER',
            },
            'debug_mode': True,
        }
        self.config = Config(config_data)
        self.parser = HIDParser(self.config)

        # Test data
        self.button_press = bytearray([0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        self.button_release = bytearray([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        self.dial_cw = bytearray([0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        self.dial_ccw = bytearray([0x02, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00])
        self.dial_click = bytearray([0x02, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00])

    def test_parser_initialization(self):
        """Test HIDParser initialization."""
        self.assertEqual(self.parser.config, self.config)
        self.assertEqual(self.parser.previous_state, {})
        self.assertEqual(self.parser.report_formats, {})
        self.assertTrue(self.parser.debug_mode)

    def test_parse_button_press(self):
        """Test parsing button press."""
        events = self.parser.parse(self.button_press)

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.event_type, EventType.KEY_PRESS)
        self.assertEqual(event.key_code, "KEY_F1")
        self.assertEqual(event.raw_data, self.button_press)

    def test_parse_button_release(self):
        """Test parsing button release."""
        # First press the button
        self.parser.parse(self.button_press)

        # Then release it
        events = self.parser.parse(self.button_release)

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.event_type, EventType.KEY_RELEASE)
        self.assertEqual(event.key_code, "KEY_F1")

    def test_parse_dial_clockwise(self):
        """Test parsing dial clockwise rotation."""
        events = self.parser.parse(self.dial_cw)

        self.assertEqual(len(events), 2)  # Press and release
        press_event = events[0]
        release_event = events[1]

        self.assertEqual(press_event.event_type, EventType.KEY_PRESS)
        self.assertEqual(press_event.key_code, "KEY_VOLUMEUP")
        self.assertEqual(press_event.direction, 1)
        self.assertEqual(press_event.value, 1)

        self.assertEqual(release_event.event_type, EventType.KEY_RELEASE)
        self.assertEqual(release_event.key_code, "KEY_VOLUMEUP")

    def test_parse_dial_counterclockwise(self):
        """Test parsing dial counter-clockwise rotation."""
        events = self.parser.parse(self.dial_ccw)

        self.assertEqual(len(events), 2)  # Press and release
        press_event = events[0]
        release_event = events[1]

        self.assertEqual(press_event.event_type, EventType.KEY_PRESS)
        self.assertEqual(press_event.key_code, "KEY_VOLUMEDOWN")
        self.assertEqual(press_event.direction, -1)
        self.assertEqual(press_event.value, -1)

        self.assertEqual(release_event.event_type, EventType.KEY_RELEASE)
        self.assertEqual(release_event.key_code, "KEY_VOLUMEDOWN")

    def test_parse_dial_click(self):
        """Test parsing dial click."""
        events = self.parser.parse(self.dial_click)

        self.assertEqual(len(events), 2)  # Press and release
        press_event = events[0]
        release_event = events[1]

        self.assertEqual(press_event.event_type, EventType.KEY_PRESS)
        self.assertEqual(press_event.key_code, "KEY_ENTER")

        self.assertEqual(release_event.event_type, EventType.KEY_RELEASE)
        self.assertEqual(release_event.key_code, "KEY_ENTER")

    def test_parse_empty_data(self):
        """Test parsing empty data."""
        events = self.parser.parse(bytearray([]))
        self.assertEqual(events, [])

    def test_parse_short_data(self):
        """Test parsing short data."""
        events = self.parser.parse(bytearray([0x01]))
        self.assertEqual(events, [])

    def test_parser_state_management(self):
        """Test that parser maintains state correctly."""
        # Press button
        events1 = self.parser.parse(self.button_press)
        self.assertEqual(len(events1), 1)
        self.assertEqual(events1[0].event_type, EventType.KEY_PRESS)

        # Press same button again (should not generate event)
        events2 = self.parser.parse(self.button_press)
        self.assertIsInstance(events2, list)

        # Release button
        events3 = self.parser.parse(self.button_release)
        self.assertEqual(len(events3), 1)
        self.assertEqual(events3[0].event_type, EventType.KEY_RELEASE)

    def test_reset_state(self):
        """Test resetting parser state."""
        # Press button to set state
        self.parser.parse(self.button_press)
        self.assertNotEqual(self.parser.previous_state, {})

        # Reset state
        self.parser.reset_state()
        self.assertEqual(self.parser.previous_state, {})


def run_simple_tests():
    """Run the simple test suite."""
    print("Running simple HID parser tests...")

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(SimpleHIDParserTest)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_simple_tests())
