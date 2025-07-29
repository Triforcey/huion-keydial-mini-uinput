"""Tests for button combo support in configuration files."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, call

from huion_keydial_mini.config import Config
from huion_keydial_mini.keybind_manager import KeybindManager


class TestConfigComboSupport:
    """Test cases for combo support in configuration files."""

    @pytest.fixture
    def basic_combo_config_data(self):
        """Basic config data with combo mappings."""
        return {
            'device': {
                'address': None,
                'name': 'Huion Keydial Mini',
            },
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
            'dial_settings': {
                'DIAL_CW': 'KEY_VOLUMEUP',
                'DIAL_CCW': 'KEY_VOLUMEDOWN',
                'DIAL_CLICK': 'KEY_MUTE',
                'sensitivity': 1.0,
            },
            'uinput': {
                'device_name': 'Huion Keydial Mini Test',
            },
            'debug_mode': True,
        }

    @pytest.fixture
    def invalid_combo_config_data(self):
        """Config data with invalid combo mappings for testing validation."""
        return {
            'key_mappings': {
                # Valid mappings
                'BUTTON_1': 'KEY_F1',
                'BUTTON_1+BUTTON_2': 'KEY_CTRL+KEY_C',

                # Invalid mappings (should be ignored)
                'BUTTON_99': 'KEY_INVALID',                 # Invalid button number
                'BUTTON_1+BUTTON_99': 'KEY_ALSO_INVALID',   # Invalid button in combo
                'BUTTON_1+': 'KEY_INCOMPLETE',              # Incomplete combo
                'INVALID_ACTION': 'KEY_WHATEVER',           # Not a button action
                '': 'KEY_EMPTY',                            # Empty action ID
            },
            'dial_settings': {},
            'debug_mode': True,
        }

    @pytest.fixture
    def unsorted_combo_config_data(self):
        """Config data with unsorted combo mappings to test normalization."""
        return {
            'key_mappings': {
                # Combos in various orders (should all normalize)
                'BUTTON_3+BUTTON_1': 'KEY_ALT+KEY_TAB',
                'BUTTON_2+BUTTON_1+BUTTON_3': 'KEY_CTRL+KEY_SHIFT+KEY_A',
                'BUTTON_18+BUTTON_1+BUTTON_10': 'KEY_F12',
                'BUTTON_5+BUTTON_2': 'KEY_ESC',
            },
            'dial_settings': {},
            'debug_mode': True,
        }

    @pytest.fixture
    def temp_combo_config_file(self, basic_combo_config_data):
        """Create a temporary config file with combo mappings."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(basic_combo_config_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.combo
    def test_config_loads_combo_mappings(self, basic_combo_config_data):
        """Test that config correctly loads combo mappings."""
        config = Config(basic_combo_config_data)

        # Verify key_mappings includes both individual and combo mappings
        key_mappings = config.key_mappings

        # Individual buttons
        assert key_mappings['BUTTON_1'] == 'KEY_F1'
        assert key_mappings['BUTTON_2'] == 'KEY_F2'
        assert key_mappings['BUTTON_3'] == 'KEY_F3'

        # Combo mappings
        assert key_mappings['BUTTON_1+BUTTON_2'] == 'KEY_CTRL+KEY_C'
        assert key_mappings['BUTTON_1+BUTTON_3'] == 'KEY_CTRL+KEY_V'
        assert key_mappings['BUTTON_2+BUTTON_3'] == 'KEY_CTRL+KEY_Z'
        assert key_mappings['BUTTON_1+BUTTON_2+BUTTON_3'] == 'KEY_CTRL+KEY_SHIFT+KEY_Z'

    @pytest.mark.combo
    def test_keybind_manager_loads_combos_from_config(self, basic_combo_config_data):
        """Test that KeybindManager loads combo mappings from config."""
        config = Config(basic_combo_config_data)
        manager = KeybindManager(config)

        # Check that individual mappings were loaded
        individual_mappings = manager.get_individual_mappings()
        assert 'BUTTON_1' in individual_mappings
        assert 'BUTTON_2' in individual_mappings
        assert 'BUTTON_3' in individual_mappings

        # Check that combo mappings were loaded
        combo_mappings = manager.get_combo_mappings()
        assert 'BUTTON_1+BUTTON_2' in combo_mappings
        assert 'BUTTON_1+BUTTON_3' in combo_mappings
        assert 'BUTTON_2+BUTTON_3' in combo_mappings
        assert 'BUTTON_1+BUTTON_2+BUTTON_3' in combo_mappings

        # Verify the actual key mappings
        action = manager.get_action('BUTTON_1+BUTTON_2')
        assert action.keys == ['KEY_CTRL', 'KEY_C']

        action = manager.get_action('BUTTON_1+BUTTON_2+BUTTON_3')
        assert action.keys == ['KEY_CTRL', 'KEY_SHIFT', 'KEY_Z']

    @pytest.mark.combo
    def test_invalid_combo_mappings_ignored_with_warnings(self, invalid_combo_config_data):
        """Test that invalid combo mappings are ignored with warnings."""
        with patch('huion_keydial_mini.keybind_manager.logger') as mock_logger:
            config = Config(invalid_combo_config_data)
            manager = KeybindManager(config)

            # Verify valid mappings were loaded
            assert manager.has_combo_mapping('BUTTON_1+BUTTON_2')
            assert manager.get_action('BUTTON_1') is not None

            # Verify invalid mappings were NOT loaded
            assert not manager.has_combo_mapping('BUTTON_1+BUTTON_99')
            assert manager.get_action('BUTTON_99') is None
            assert manager.get_action('INVALID_ACTION') is None

            # Verify warnings were logged for invalid entries
            mock_logger.warning.assert_called()
            warning_calls = [call.args[0] for call in mock_logger.warning.call_args_list]

            # Should have warnings about invalid entries
            invalid_warnings = [w for w in warning_calls if 'Invalid' in w or 'invalid' in w]
            assert len(invalid_warnings) > 0

    @pytest.mark.combo
    def test_combo_normalization_in_config(self, unsorted_combo_config_data):
        """Test that combo mappings from config are normalized to sorted order."""
        config = Config(unsorted_combo_config_data)
        manager = KeybindManager(config)

        # These should be normalized to sorted order
        expected_normalizations = [
            ('BUTTON_3+BUTTON_1', 'BUTTON_1+BUTTON_3'),
            ('BUTTON_2+BUTTON_1+BUTTON_3', 'BUTTON_1+BUTTON_2+BUTTON_3'),
            ('BUTTON_18+BUTTON_1+BUTTON_10', 'BUTTON_1+BUTTON_10+BUTTON_18'),
            ('BUTTON_5+BUTTON_2', 'BUTTON_2+BUTTON_5'),
        ]

        for original, normalized in expected_normalizations:
            # Original unsorted combo should NOT exist
            assert not manager.has_combo_mapping(original)

            # Normalized combo SHOULD exist
            assert manager.has_combo_mapping(normalized), f"Normalized combo {normalized} not found"

            # Verify the mapping
            action = manager.get_action(normalized)
            assert action is not None

    @pytest.mark.combo
    def test_config_file_loading_with_combos(self, temp_combo_config_file):
        """Test loading combo mappings from actual config file."""
        config = Config.load(temp_combo_config_file)
        manager = KeybindManager(config)

        # Verify combos loaded from file
        assert manager.has_combo_mapping('BUTTON_1+BUTTON_2')
        assert manager.has_combo_mapping('BUTTON_1+BUTTON_3')
        assert manager.has_combo_mapping('BUTTON_2+BUTTON_3')
        assert manager.has_combo_mapping('BUTTON_1+BUTTON_2+BUTTON_3')

        # Verify individual buttons also loaded
        assert manager.get_action('BUTTON_1') is not None
        assert manager.get_action('BUTTON_2') is not None
        assert manager.get_action('BUTTON_3') is not None

    @pytest.mark.combo
    def test_combo_precedence_over_duplicates(self):
        """Test handling of potential conflicts between combo and individual mappings."""
        # Config with potential conflicts
        config_data = {
            'key_mappings': {
                # This could potentially conflict if not handled properly
                'BUTTON_1': 'KEY_F1',
                'BUTTON_2': 'KEY_F2',
                'BUTTON_1+BUTTON_2': 'KEY_CTRL+KEY_C',

                # Test normalization doesn't create conflicts
                'BUTTON_3+BUTTON_1': 'KEY_ALT+KEY_TAB',  # Should become BUTTON_1+BUTTON_3
                'BUTTON_1+BUTTON_3': 'KEY_SHIFT+KEY_TAB',  # Potential conflict
            },
            'dial_settings': {},
            'debug_mode': True,
        }

        config = Config(config_data)
        manager = KeybindManager(config)

        # Individual mappings should exist
        assert manager.get_action('BUTTON_1') is not None
        assert manager.get_action('BUTTON_2') is not None

        # Combo mapping should exist
        assert manager.has_combo_mapping('BUTTON_1+BUTTON_2')

        # For the duplicate case (BUTTON_3+BUTTON_1 vs BUTTON_1+BUTTON_3)
        # The last one wins (this is expected YAML behavior)
        assert manager.has_combo_mapping('BUTTON_1+BUTTON_3')
        action = manager.get_action('BUTTON_1+BUTTON_3')
        # Should be the last value defined
        assert action.keys == ['KEY_SHIFT', 'KEY_TAB']

    @pytest.mark.combo
    def test_config_combo_descriptions(self, basic_combo_config_data):
        """Test that combo actions get proper descriptions."""
        config = Config(basic_combo_config_data)
        manager = KeybindManager(config)

        # Check combo descriptions are generated properly
        action = manager.get_action('BUTTON_1+BUTTON_2')
        assert action.description is not None
        assert 'BUTTON_1+BUTTON_2' in action.description
        assert 'KEY_CTRL+KEY_C' in action.description

        action = manager.get_action('BUTTON_1+BUTTON_2+BUTTON_3')
        assert action.description is not None
        assert 'BUTTON_1+BUTTON_2+BUTTON_3' in action.description

    @pytest.mark.combo
    def test_empty_and_none_config_values(self):
        """Test handling of empty or None values in config combo mappings."""
        config_data = {
            'key_mappings': {
                'BUTTON_1': 'KEY_F1',
                'BUTTON_1+BUTTON_2': '',        # Empty value
                'BUTTON_2+BUTTON_3': None,      # None value
                'BUTTON_1+BUTTON_3': 'KEY_CTRL+KEY_V',  # Valid value
            },
            'dial_settings': {},
            'debug_mode': True,
        }

        config = Config(config_data)
        manager = KeybindManager(config)

        # Valid mappings should be loaded
        assert manager.get_action('BUTTON_1') is not None
        assert manager.has_combo_mapping('BUTTON_1+BUTTON_3')

        # Empty/None mappings should be ignored
        assert not manager.has_combo_mapping('BUTTON_1+BUTTON_2')
        assert not manager.has_combo_mapping('BUTTON_2+BUTTON_3')

    @pytest.mark.combo
    def test_config_combo_integration_with_dial_settings(self, basic_combo_config_data):
        """Test that combo mappings coexist properly with dial settings."""
        config = Config(basic_combo_config_data)
        manager = KeybindManager(config)

        # Verify dial settings loaded
        assert manager.get_action('DIAL_CW') is not None
        assert manager.get_action('DIAL_CCW') is not None
        assert manager.get_action('DIAL_CLICK') is not None

        # Verify combo mappings loaded
        assert manager.has_combo_mapping('BUTTON_1+BUTTON_2')

        # Verify individual button mappings loaded
        assert manager.get_action('BUTTON_1') is not None

        # Check total count includes all types
        all_mappings = manager.get_all_actions()
        combo_count = len(manager.get_combo_mappings())
        individual_count = len(manager.get_individual_mappings())

        # Should have individual buttons + dial actions + combos
        assert len(all_mappings) == individual_count + combo_count
        assert combo_count >= 4  # At least 4 combos from basic config
        assert individual_count >= 6  # At least 3 buttons + 3 dial actions

    @pytest.mark.combo
    def test_config_type_validation_with_combos(self):
        """Test that config type validation works with combo mappings."""
        # Test non-string values in combo mappings
        config_data = {
            'key_mappings': {
                'BUTTON_1': 123,  # Invalid type (should be ignored)
                'BUTTON_1+BUTTON_2': 'KEY_CTRL+KEY_C',  # Valid
                456: 'KEY_F1',    # Invalid key type (should be ignored)
                'BUTTON_2+BUTTON_3': ['KEY_CTRL', 'KEY_Z'],  # Invalid type (should be ignored)
            },
            'dial_settings': {},
            'debug_mode': True,
        }

        config = Config(config_data)
        manager = KeybindManager(config)

        # Only valid string mappings should be loaded
        assert manager.has_combo_mapping('BUTTON_1+BUTTON_2')
        assert not manager.get_action('BUTTON_1')  # Invalid type was ignored
        assert not manager.has_combo_mapping('BUTTON_2+BUTTON_3')  # Invalid type was ignored
