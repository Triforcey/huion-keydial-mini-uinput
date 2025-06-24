"""Device scanner for discovering Huion devices."""

import asyncio
import logging
import subprocess
import re
from typing import List, NamedTuple, Optional, Dict, Any
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
import sys
import argparse


logger = logging.getLogger(__name__)


class DiscoveredDevice(NamedTuple):
    """Represents a discovered Bluetooth device."""
    address: str
    name: str
    rssi: int
    metadata: Optional[Dict[str, Any]] = None


class DeviceScanner:
    """Scanner for Huion Bluetooth devices."""

    # Known Huion device identifiers
    HUION_DEVICE_NAMES = [
        'Huion Keydial Mini',
        'HUION Keydial Mini',
        'Keydial Mini',
        'Huion KD Mini',
        'HUION KD Mini',
    ]

    # Known Huion manufacturer data patterns
    HUION_MANUFACTURER_IDS = [
        0x256c,  # Huion vendor ID
    ]

    def __init__(self, timeout: float = 10.0, debug_mode: bool = False):
        self.timeout = timeout
        self.debug_mode = debug_mode
        self.discovered_devices: List[DiscoveredDevice] = []

    async def scan(self) -> List[DiscoveredDevice]:
        """Scan for paired Huion devices."""
        logger.info("Checking for paired Huion devices...")

        devices = []

        try:
            # Get paired devices using bluetoothctl
            paired_devices = await self._get_paired_devices()

            if self.debug_mode:
                logger.info(f"Found {len(paired_devices)} paired devices")
                logger.info("=== Paired Devices ===")
                for i, (address, name) in enumerate(paired_devices, 1):
                    logger.info(f"{i:2d}. {address} - {name}")
                logger.info("======================")

            # Check each paired device for Huion devices
            for address, name in paired_devices:
                if self._is_huion_device_name(name):
                    logger.info(f"Found paired Huion device: {address} - {name}")
                    devices.append(DiscoveredDevice(
                        address=address,
                        name=name,
                        rssi=-999,  # No RSSI for paired devices
                        metadata={'paired': True, 'name': name}
                    ))

            if not devices:
                logger.info("No paired Huion devices found")

        except Exception as e:
            logger.error(f"Error checking paired devices: {e}")
            raise

        return devices

    async def _get_paired_devices(self) -> List[tuple[str, str]]:
        """Get list of paired devices using bluetoothctl."""
        try:
            # Run bluetoothctl to get paired devices
            result = subprocess.run(
                ['bluetoothctl', 'devices', 'Paired'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning(f"bluetoothctl failed: {result.stderr}")
                return []

            devices = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # Parse line like: "Device AA:BB:CC:DD:EE:FF Device Name"
                    match = re.match(r'Device\s+([A-Fa-f0-9:]+)\s+(.+)', line)
                    if match:
                        address = match.group(1)
                        name = match.group(2).strip()
                        devices.append((address, name))

            return devices

        except subprocess.TimeoutExpired:
            logger.error("bluetoothctl command timed out")
            return []
        except FileNotFoundError:
            logger.error("bluetoothctl not found. Make sure bluetooth is installed.")
            return []
        except Exception as e:
            logger.error(f"Error running bluetoothctl: {e}")
            return []

    def _is_huion_device_name(self, device_name: str) -> bool:
        """Check if a device name matches Huion device patterns."""
        if not device_name:
            return False

        device_name_lower = device_name.lower()

        # Check for known Huion device names
        for huion_name in self.HUION_DEVICE_NAMES:
            if huion_name.lower() in device_name_lower:
                return True

        # Check for other Huion indicators
        huion_indicators = ['huion', 'keydial']
        if any(indicator in device_name_lower for indicator in huion_indicators):
            return True

        return False

    def _is_huion_device(self, device: BLEDevice) -> bool:
        """Check if a discovered device is a Huion device."""
        if not device.name:
            return False

        return self._is_huion_device_name(device.name)

    def _extract_metadata(self, device: BLEDevice) -> Optional[Dict[str, Any]]:
        """Extract useful metadata from the device."""
        metadata = {}

        # Basic device info
        metadata['name'] = device.name
        metadata['rssi'] = device.rssi
        metadata['address'] = device.address

        # Extract manufacturer data if available
        if hasattr(device, 'metadata') and device.metadata:
            metadata['manufacturer_data'] = device.metadata.get('manufacturer_data', {})
            metadata['service_data'] = device.metadata.get('service_data', {})
            metadata['service_uuids'] = device.metadata.get('service_uuids', [])

        return metadata if metadata else None

    async def scan_specific_device(self, address: str) -> Optional[DiscoveredDevice]:
        """Check if a specific device is paired."""
        logger.info(f"Checking if device {address} is paired...")

        try:
            paired_devices = await self._get_paired_devices()

            for device_address, device_name in paired_devices:
                if device_address.lower() == address.lower():
                    logger.info(f"Found paired device: {device_address} - {device_name}")
                    return DiscoveredDevice(
                        address=device_address,
                        name=device_name,
                        rssi=-999,
                        metadata={'paired': True, 'name': device_name}
                    )

            logger.warning(f"Device {address} is not paired")
            return None

        except Exception as e:
            logger.error(f"Error checking specific device: {e}")
            raise

    def get_scan_statistics(self) -> Dict[str, Any]:
        """Get statistics about the last scan."""
        return {
            'paired_devices_checked': len(self.discovered_devices),
            'huion_devices_found': len([d for d in self.discovered_devices if self._is_huion_device_name(d.name)]),
            'scan_timeout': self.timeout,
            'debug_mode': self.debug_mode
        }

    def clear_discovered_devices(self):
        """Clear the list of discovered devices."""
        self.discovered_devices.clear()
        logger.debug("Cleared discovered devices list")


async def scan_devices(debug_mode: bool = False) -> None:
    """Scan for Huion devices."""
    scanner = DeviceScanner(debug_mode=debug_mode)

    try:
        devices = await scanner.scan()

        if devices:
            print(f"\nFound {len(devices)} Huion device(s):")
            for i, device in enumerate(devices, 1):
                print(f"  {i}. {device.address} - {device.name}")
        else:
            print("\nNo Huion devices found.")

    except Exception as e:
        print(f"Error scanning for devices: {e}")
        sys.exit(1)


def main():
    """Main entry point for the scanner."""
    parser = argparse.ArgumentParser(description="Scan for Huion Keydial Mini devices")
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug mode'
    )

    args = parser.parse_args()

    # Set up logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Run the scan
    asyncio.run(scan_devices(debug_mode=args.debug))


if __name__ == "__main__":
    main()
