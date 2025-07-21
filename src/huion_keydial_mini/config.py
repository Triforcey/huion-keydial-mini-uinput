"""Configuration management for the Huion Keydial Mini driver."""

import os
import yaml
from typing import Optional, Dict, Any, Union, cast
from pathlib import Path


class Config:
    """Configuration class for the driver."""

    def __init__(self, data: Dict[str, Any]):
        self.data = self._validate_config_data(data)
        # Preserve all top-level keys for global options
        self._global = {k: v for k, v in data.items() if k not in self.data}

    def _validate_config_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize configuration data."""
        # Ensure all required sections exist
        validated: Dict[str, Dict[str, Any]] = {
            'device': {},
            'bluetooth': {},
            'uinput': {},
            'key_mappings': {},
            'dial_settings': {},
        }

        # Copy and validate each section
        for section in validated.keys():
            if section in data and isinstance(data[section], dict):
                validated[section] = data[section].copy()
            elif section in data:
                # Convert non-dict values to empty dict for safety
                validated[section] = {}

        return validated

    @property
    def device_address(self) -> Optional[str]:
        """Get the Bluetooth device address."""
        address = self.data.get('device', {}).get('address')
        return str(address) if address is not None else None

    @property
    def device_name(self) -> str:
        """Get the expected device name."""
        name = self.data.get('device', {}).get('name', 'Huion Keydial Mini')
        return str(name)

    @property
    def scan_timeout(self) -> float:
        """Get the BLE scan timeout in seconds."""
        timeout = self.data.get('bluetooth', {}).get('scan_timeout', 10.0)
        try:
            return float(timeout)
        except (TypeError, ValueError):
            return 10.0

    @property
    def connection_timeout(self) -> float:
        """Get the connection timeout in seconds."""
        timeout = self.data.get('bluetooth', {}).get('connection_timeout', 30.0)
        try:
            return float(timeout)
        except (TypeError, ValueError):
            return 30.0

    @property
    def reconnect_attempts(self) -> int:
        """Get the number of reconnection attempts."""
        attempts = self.data.get('bluetooth', {}).get('reconnect_attempts', 3)
        try:
            return int(attempts)
        except (TypeError, ValueError):
            return 3

    @property
    def auto_reconnect(self) -> bool:
        """Get whether to enable automatic reconnection via DBus monitoring."""
        auto_reconnect = self.data.get('bluetooth', {}).get('auto_reconnect', True)
        return bool(auto_reconnect)

    @property
    def uinput_device_name(self) -> str:
        """Get the uinput device name."""
        name = self.data.get('uinput', {}).get('device_name', 'huion-keydial-mini-uinput')
        return str(name)

    @property
    def key_mappings(self) -> Dict[str, str]:
        """Get the key mappings configuration."""
        mappings = self.data.get('key_mappings', {})
        if not isinstance(mappings, dict):
            return {}
        # Ensure all values are strings with proper type checking
        result: Dict[str, str] = {}
        for k, v in mappings.items():
            if isinstance(k, str) and v is not None:
                result[k] = str(v)
        return result

    @property
    def dial_settings(self) -> Dict[str, Any]:
        """Get the dial settings configuration."""
        settings = self.data.get('dial_settings', {})
        if not isinstance(settings, dict):
            return {}

        # Cast specific dial settings to appropriate types
        result: Dict[str, Any] = {}
        for key, value in settings.items():
            if not isinstance(key, str):
                continue

            if key == 'sensitivity':
                try:
                    result[key] = float(value) if value is not None else 1.0
                except (TypeError, ValueError):
                    result[key] = 1.0
            elif key in ['DIAL_CW', 'DIAL_CCW', 'DIAL_CLICK']:
                result[key] = str(value) if value is not None else None
            else:
                result[key] = value

        return result

    @property
    def debug_mode(self) -> bool:
        # Prefer top-level debug_mode, fallback to False
        return bool(self._global.get('debug_mode', False))

    @classmethod
    def load(cls, config_path: Optional[str] = None, device_address: Optional[str] = None) -> 'Config':
        """Load configuration from file or create default."""

        # Try to find config file
        if config_path:
            config_file = Path(config_path)
        else:
            # Look for config in standard locations
            config_locations = [
                Path.home() / '.config' / 'huion-keydial-mini' / 'config.yaml',
                Path('/etc/huion-keydial-mini/config.yaml'),
            ]

            config_file = None
            for location in config_locations:
                if location.exists():
                    config_file = location
                    break

        # Load config data
        raw_data: Dict[str, Any] = {}
        if config_file and config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    loaded_data = yaml.safe_load(f)
                    if isinstance(loaded_data, dict):
                        raw_data = loaded_data  # type: ignore
            except (yaml.YAMLError, IOError) as e:
                # If config file is malformed, use defaults
                print(f"Warning: Error loading config file {config_file}: {e}")

        # Apply command line overrides
        if device_address:
            if 'device' not in raw_data:
                raw_data['device'] = {}
            raw_data['device']['address'] = device_address

        # Handle flat config structure mapping to nested structure
        if 'device_address' in raw_data:
            if 'device' not in raw_data:
                raw_data['device'] = {}
            raw_data['device']['address'] = raw_data.pop('device_address')

        if 'connection_timeout' in raw_data:
            if 'bluetooth' not in raw_data:
                raw_data['bluetooth'] = {}
            raw_data['bluetooth']['connection_timeout'] = raw_data.pop('connection_timeout')

        if 'uinput_device_name' in raw_data:
            if 'uinput' not in raw_data:
                raw_data['uinput'] = {}
            raw_data['uinput']['device_name'] = raw_data.pop('uinput_device_name')

        # Start with defaults and merge user data
        config_data = cls._get_default_config()
        config_data = cls._merge_config_data(config_data, raw_data)

        return cls(config_data)

    @staticmethod
    def _merge_config_data(defaults: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user configuration with defaults, ensuring proper types."""
        result = defaults.copy()

        for section, section_data in user_data.items():
            if section in result and isinstance(section_data, dict) and isinstance(result[section], dict):
                # Merge section data
                result[section].update(section_data)
            elif section_data is not None:
                # Replace entire section
                result[section] = section_data

        return result

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get the default configuration."""
        return {
            'device': {
                'name': 'Huion Keydial Mini',
                'address': None,
            },
            'bluetooth': {
                'scan_timeout': 10.0,
                'connection_timeout': 30.0,
                'reconnect_attempts': 3,
            },
            'uinput': {
                'device_name': 'huion-keydial-mini-uinput',
            },
            'key_mappings': {},
            'dial_settings': {},
        }

    def save(self, config_path: str):
        """Save configuration to file."""
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, 'w') as f:
            yaml.dump(self.data, f, default_flow_style=False)

    def validate(self) -> bool:
        """Validate the current configuration."""
        try:
            # Test all property accessors to ensure they work
            _ = self.device_address
            _ = self.device_name
            _ = self.scan_timeout
            _ = self.connection_timeout
            _ = self.reconnect_attempts
            _ = self.auto_reconnect
            _ = self.uinput_device_name
            _ = self.key_mappings
            _ = self.dial_settings
            return True
        except Exception:
            return False

    def get_effective_config(self) -> Dict[str, Any]:
        """Get the effective configuration with all type casting applied."""
        return {
            'device': {
                'address': self.device_address,
                'name': self.device_name,
            },
            'bluetooth': {
                'scan_timeout': self.scan_timeout,
                'connection_timeout': self.connection_timeout,
                'reconnect_attempts': self.reconnect_attempts,
                'auto_reconnect': self.auto_reconnect,
            },
            'uinput': {
                'device_name': self.uinput_device_name,
            },
            'key_mappings': self.key_mappings,
            'dial_settings': self.dial_settings,
        }
