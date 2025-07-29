"""Tests for the keybind manager."""

import pytest

from huion_keydial_mini.keybind_manager import KeybindManager
from huion_keydial_mini.config import Config


class TestKeybindManager:
    """Tests for the keybind manager."""

    @pytest.fixture
    def keybind_manager(self):
        """Create a keybind manager instance."""
        return KeybindManager(config=Config({
            'key_mappings': {
                'BUTTON_1': 'KEY_F1',
            },
            'sticky_key_mappings': {
                'BUTTON_2': 'KEY_F2',
            },
        }))

    @pytest.mark.keybind_manager
    def test_keybind_manager_initialization(self, keybind_manager):
        """Test the keybind manager initialization."""
        assert keybind_manager is not None

    @pytest.mark.keybind_manager
    def test_keybind_manager_load_initial_bindings(self, keybind_manager: KeybindManager):
        """Test the keybind manager load initial bindings."""
        assert keybind_manager.keybind_map is not None
        assert len(keybind_manager.keybind_map) == 2
        assert keybind_manager.keybind_map['BUTTON_1'].keys == ['KEY_F1']
        assert keybind_manager.keybind_map['BUTTON_2'].keys == ['KEY_F2']
        assert keybind_manager.keybind_map['BUTTON_1'].sticky is False
        assert keybind_manager.keybind_map['BUTTON_2'].sticky is True
