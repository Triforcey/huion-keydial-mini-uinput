"""Pytest configuration and common fixtures for huion-keydial-mini-driver tests."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock

from huion_keydial_mini.config import Config
from huion_keydial_mini.hid_parser import HIDParser, EventType, InputEvent


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        'device': {
            'name': 'Huion Keydial Mini',
        },
        'bluetooth': {
            'scan_timeout': 10.0,
            'connection_timeout': 30.0,
            'reconnect_attempts': 3,
        },
        'uinput': {
            'device_name': 'Huion Keydial Mini',
        },
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


@pytest.fixture
def temp_config_file(sample_config_data):
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(sample_config_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def config(sample_config_data):
    """Create a Config instance for testing."""
    return Config(sample_config_data)


@pytest.fixture
def hid_parser(config):
    """Create a HIDParser instance for testing."""
    return HIDParser(config)


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock the logger to avoid output during tests."""
    mock_logger = Mock()
    monkeypatch.setattr('huion_keydial_mini.hid_parser.logger', mock_logger)
    return mock_logger


class HIDTestData:
    """Common HID test data for different report formats."""

    # Button report format: [0x01, button_state, 0x00, 0x00, ...]
    BUTTON_PRESS = bytearray([0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Button 1 pressed
    BUTTON_RELEASE = bytearray([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # All buttons released
    MULTIPLE_BUTTONS = bytearray([0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Buttons 1 and 2 pressed

    # Dial report format: [0x02, dial_delta_low, dial_delta_high, dial_click, ...]
    DIAL_CW = bytearray([0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Clockwise rotation
    DIAL_CCW = bytearray([0x02, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00])  # Counter-clockwise rotation
    DIAL_CLICK = bytearray([0x02, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00])  # Dial click

    # Combined report format: [0x00, buttons_low, buttons_high, dial_delta_low, dial_delta_high, dial_click, ...]
    COMBINED_BUTTON_DIAL = bytearray([0x00, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00])  # Button 1 + dial CW

    # Standard HID format (generic)
    STANDARD_HID_BUTTON = bytearray([0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    STANDARD_HID_DIAL = bytearray([0x02, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00])

    # Edge cases
    EMPTY_DATA = bytearray([])
    SHORT_DATA = bytearray([0x01])
    INVALID_DATA = bytearray([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])


@pytest.fixture
def hid_test_data():
    """Provide common HID test data."""
    return HIDTestData()
