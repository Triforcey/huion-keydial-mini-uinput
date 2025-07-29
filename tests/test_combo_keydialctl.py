"""Tests for button combo handling in keydialctl CLI."""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from huion_keydial_mini.keybind_manager import send_command, KeybindManager
from huion_keydial_mini.config import Config


class TestKeydialctlComboHandling:
    """Test cases for keydialctl combo functionality."""

    @pytest.fixture
    def mock_socket_path(self):
        """Mock socket path for testing."""
        return "/tmp/test_keydial.sock"

    @pytest.fixture
    def combo_config(self):
        """Create a test config with combo support."""
        return Config({
            'key_mappings': {
                'BUTTON_1': 'KEY_F1',
                'BUTTON_2': 'KEY_F2',
                'BUTTON_1+BUTTON_2': 'KEY_CTRL+KEY_C',
                'BUTTON_1+BUTTON_3': 'KEY_CTRL+KEY_V',
                'BUTTON_2+BUTTON_3': 'KEY_CTRL+KEY_Z',
            },
            'dial_settings': {},
            'debug_mode': True
        })

    @pytest.fixture
    def keybind_manager(self, combo_config):
        """Create a keybind manager for testing."""
        return KeybindManager(combo_config)

    @pytest.mark.combo
    @pytest.mark.asyncio
    async def test_send_combo_bind_command(self, mock_socket_path):
        """Test sending combo bind command via socket."""
        # Mock the socket communication
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_reader.readline.return_value = b'{"status": "success", "message": "Binding set"}\n'

        with patch('huion_keydial_mini.keybind_manager.asyncio.open_unix_connection') as mock_connect:
            mock_connect.return_value = (mock_reader, mock_writer)

            command = {
                'command': 'set_binding',
                'action_id': 'BUTTON_1+BUTTON_2',
                'action': {
                    'type': 'keyboard',
                    'keys': ['KEY_CTRL', 'KEY_C'],
                    'description': 'BUTTON_1+BUTTON_2 -> KEY_CTRL+KEY_C'
                }
            }

            response = await send_command(mock_socket_path, command)

            # Verify the command was sent correctly
            mock_writer.write.assert_called_once()
            written_data = mock_writer.write.call_args[0][0].decode('utf-8')
            import json
            sent_command = json.loads(written_data)

            assert sent_command['action_id'] == 'BUTTON_1+BUTTON_2'
            assert sent_command['action']['keys'] == ['KEY_CTRL', 'KEY_C']
            assert response['status'] == 'success'

    @pytest.mark.combo
    def test_combo_id_validation_valid_combos(self, keybind_manager):
        """Test validation of valid combo action IDs."""
        valid_combos = [
            'BUTTON_1+BUTTON_2',
            'BUTTON_1+BUTTON_3',
            'BUTTON_2+BUTTON_3',
            'BUTTON_1+BUTTON_2+BUTTON_3',
            'BUTTON_10+BUTTON_18',  # Edge case with high numbers
        ]

        for combo_id in valid_combos:
            normalized = keybind_manager._validate_and_normalize_action_id(combo_id)
            assert normalized is not None, f"Valid combo {combo_id} was rejected"

            # Check normalization (should be sorted)
            buttons = combo_id.split('+')
            expected = '+'.join(sorted(buttons))
            assert normalized == expected

    @pytest.mark.combo
    def test_combo_id_validation_invalid_combos(self, keybind_manager):
        """Test validation rejects invalid combo action IDs."""
        invalid_combos = [
            'BUTTON_99',                    # Invalid button number
            'BUTTON_1+BUTTON_99',          # Contains invalid button
            'BUTTON_1+',                   # Incomplete combo
            '+BUTTON_2',                   # Starts with separator
            'BUTTON_1++BUTTON_2',          # Double separator
            'BUTTON_1+BUTTON_1',           # Duplicate button
            'INVALID_BUTTON',              # Not a button at all
            '',                            # Empty string
        ]

        for combo_id in invalid_combos:
            normalized = keybind_manager._validate_and_normalize_action_id(combo_id)
            assert normalized is None, f"Invalid combo {combo_id} was accepted"

    @pytest.mark.combo
    def test_combo_id_normalization_order(self, keybind_manager):
        """Test that combo IDs are normalized to consistent order."""
        test_cases = [
            ('BUTTON_3+BUTTON_1', 'BUTTON_1+BUTTON_3'),
            ('BUTTON_2+BUTTON_1+BUTTON_3', 'BUTTON_1+BUTTON_2+BUTTON_3'),
            ('BUTTON_18+BUTTON_1+BUTTON_10', 'BUTTON_1+BUTTON_10+BUTTON_18'),
            ('BUTTON_5+BUTTON_2+BUTTON_8+BUTTON_1', 'BUTTON_1+BUTTON_2+BUTTON_5+BUTTON_8'),
        ]

        for input_combo, expected_combo in test_cases:
            normalized = keybind_manager._validate_and_normalize_action_id(input_combo)
            assert normalized == expected_combo, f"'{input_combo}' should normalize to '{expected_combo}', got '{normalized}'"

    @pytest.mark.combo
    def test_combo_action_creation(self, keybind_manager):
        """Test creating combo actions with the keybind manager."""
        # Create a combo action
        combo_id = keybind_manager.set_combo_action(
            ['BUTTON_1', 'BUTTON_2'],
            ['KEY_CTRL', 'KEY_C'],
            'Copy action'
        )

        assert combo_id == 'BUTTON_1+BUTTON_2'
        assert keybind_manager.has_combo_mapping(combo_id)

        action = keybind_manager.get_action(combo_id)
        assert action.keys == ['KEY_CTRL', 'KEY_C']
        assert action.description == 'Copy action'

    @pytest.mark.combo
    def test_combo_vs_individual_mappings_separation(self, keybind_manager):
        """Test that combo and individual mappings are properly separated."""
        # Add some individual and combo mappings
        keybind_manager.set_combo_action(['BUTTON_1', 'BUTTON_2'], ['KEY_CTRL', 'KEY_C'])
        keybind_manager.set_combo_action(['BUTTON_1', 'BUTTON_3'], ['KEY_CTRL', 'KEY_V'])

        individual_mappings = keybind_manager.get_individual_mappings()
        combo_mappings = keybind_manager.get_combo_mappings()

        # Check that we have the expected individual mappings from config
        individual_keys = set(individual_mappings.keys())
        expected_individual = {'BUTTON_1', 'BUTTON_2'}
        assert expected_individual.issubset(individual_keys)

        # Check that we have the expected combo mappings
        combo_keys = set(combo_mappings.keys())
        expected_combos = {'BUTTON_1+BUTTON_2', 'BUTTON_1+BUTTON_3'}
        assert expected_combos.issubset(combo_keys)

        # Ensure no overlap
        assert individual_keys.isdisjoint(combo_keys)

    @pytest.mark.combo
    def test_is_combo_action_detection(self, keybind_manager):
        """Test detection of combo vs individual actions."""
        test_cases = [
            ('BUTTON_1', False),
            ('BUTTON_18', False),
            ('DIAL_CW', False),
            ('BUTTON_1+BUTTON_2', True),
            ('BUTTON_1+BUTTON_2+BUTTON_3', True),
            ('BUTTON_10+BUTTON_15', True),
        ]

        for action_id, expected_is_combo in test_cases:
            result = keybind_manager.is_combo_action(action_id)
            assert result == expected_is_combo, f"'{action_id}' combo detection failed"

    @pytest.mark.combo
    @pytest.mark.asyncio
    async def test_combo_bind_command_processing(self, keybind_manager):
        """Test processing combo bind commands through the manager."""
        # Simulate a bind command for a combo
        command = {
            'command': 'set_binding',
            'action_id': 'BUTTON_1+BUTTON_2',
            'action': {
                'type': 'keyboard',
                'keys': ['KEY_CTRL', 'KEY_C'],
                'description': 'Copy combo'
            }
        }

        response = await keybind_manager._cmd_set_binding(command)

        assert response['status'] == 'success'
        assert 'BUTTON_1+BUTTON_2' in response['message']

        # Verify the binding was created
        assert keybind_manager.has_combo_mapping('BUTTON_1+BUTTON_2')
        action = keybind_manager.get_action('BUTTON_1+BUTTON_2')
        assert action.keys == ['KEY_CTRL', 'KEY_C']

    @pytest.mark.combo
    @pytest.mark.asyncio
    async def test_combo_unbind_command_processing(self, keybind_manager):
        """Test processing combo unbind commands through the manager."""
        # First create a combo binding
        keybind_manager.set_combo_action(['BUTTON_1', 'BUTTON_2'], ['KEY_CTRL', 'KEY_C'])
        assert keybind_manager.has_combo_mapping('BUTTON_1+BUTTON_2')

        # Now remove it
        command = {
            'command': 'remove_binding',
            'action_id': 'BUTTON_1+BUTTON_2'
        }

        response = await keybind_manager._cmd_remove_binding(command)

        assert response['status'] == 'success'
        assert 'BUTTON_1+BUTTON_2' in response['message']

        # Verify the binding was removed
        assert not keybind_manager.has_combo_mapping('BUTTON_1+BUTTON_2')

    @pytest.mark.combo
    @pytest.mark.asyncio
    async def test_get_bindings_includes_combos(self, keybind_manager):
        """Test that get_bindings command includes combo mappings."""
        # Add a combo mapping
        keybind_manager.set_combo_action(['BUTTON_1', 'BUTTON_2'], ['KEY_CTRL', 'KEY_C'])

        response = await keybind_manager._cmd_get_bindings()

        assert response['status'] == 'success'
        bindings = response['bindings']

        # Should include both individual and combo mappings
        assert 'BUTTON_1' in bindings  # Individual from config
        assert 'BUTTON_1+BUTTON_2' in bindings  # Combo we added

        combo_binding = bindings['BUTTON_1+BUTTON_2']
        assert combo_binding['type'] == 'keyboard'
        assert combo_binding['keys'] == ['KEY_CTRL', 'KEY_C']

    @pytest.mark.combo
    def test_combo_button_edge_cases(self, keybind_manager):
        """Test edge cases in combo button handling."""
        # Test with maximum button numbers
        valid_high_combo = keybind_manager._validate_and_normalize_action_id('BUTTON_18+BUTTON_17')
        assert valid_high_combo == 'BUTTON_17+BUTTON_18'

        # Test with minimum button numbers
        valid_low_combo = keybind_manager._validate_and_normalize_action_id('BUTTON_2+BUTTON_1')
        assert valid_low_combo == 'BUTTON_1+BUTTON_2'

        # Test single button (should work for individual buttons)
        single_button = keybind_manager._validate_and_normalize_action_id('BUTTON_1')
        assert single_button == 'BUTTON_1'

        # Test empty combo (should fail)
        empty_combo = keybind_manager._validate_and_normalize_action_id('+')
        assert empty_combo is None
