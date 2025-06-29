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

    # Button report format (type 2 buttons using bitmasking in first byte)
    # button 13: bit 0, button 14: bit 2, button 15: bit 1
    BUTTON_13_PRESS = bytearray([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Button 13 pressed (bit 0)
    BUTTON_14_PRESS = bytearray([0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Button 14 pressed (bit 2)
    BUTTON_15_PRESS = bytearray([0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Button 15 pressed (bit 1)
    BUTTON_RELEASE = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # All buttons released
    MULTIPLE_BUTTONS = bytearray([0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Buttons 13 and 15 pressed (bits 0+1)

    # Type 1 button format (buttons in bytes 3-5)
    BUTTON_1_PRESS = bytearray([0x00, 0x00, 0x00, 0x0e, 0x00, 0x00, 0x00, 0x00])  # Button 1 (0x0e in byte 3)
    BUTTON_2_PRESS = bytearray([0x00, 0x00, 0x00, 0x0a, 0x00, 0x00, 0x00, 0x00])  # Button 2 (0x0a in byte 3)
    BUTTON_3_PRESS = bytearray([0x00, 0x00, 0x00, 0x0f, 0x00, 0x00, 0x00, 0x00])  # Button 3 (0x0f in byte 3)

    # Dial report format: f1[clicked][count][direction]0000000000 (9 bytes)
    DIAL_CW = bytearray([0xf1, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Clockwise rotation (count=1, direction=0x00)
    DIAL_CCW = bytearray([0xf1, 0x00, 0xff, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00])  # Counter-clockwise rotation (count=0xff, direction=0xff)
    DIAL_CLICK = bytearray([0xf1, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Dial click (clicked=0x03, count=0x00)
    DIAL_CLICK_RELEASE = bytearray([0xf1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Dial click release

    # Edge cases
    EMPTY_DATA = bytearray([])
    SHORT_DATA = bytearray([0x01])
    INVALID_DATA = bytearray([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])


@pytest.fixture
def hid_test_data():
    """Provide common HID test data."""
    return HIDTestData()
