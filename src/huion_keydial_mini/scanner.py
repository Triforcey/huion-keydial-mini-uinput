"""Device scanner for discovering Huion devices."""

import asyncio
import logging
from typing import List, NamedTuple
from bleak import BleakScanner


logger = logging.getLogger(__name__)


class DiscoveredDevice(NamedTuple):
    """Represents a discovered Bluetooth device."""
    address: str
    name: str
    rssi: int


class DeviceScanner:
    """Scanner for Huion Bluetooth devices."""

    # Known Huion device identifiers
    HUION_DEVICE_NAMES = [
        'Huion Keydial Mini',
        'HUION Keydial Mini',
        'Keydial Mini',
    ]

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def scan(self) -> List[DiscoveredDevice]:
        """Scan for Huion devices."""
        logger.info(f"Scanning for devices for {self.timeout} seconds...")

        devices = []

        try:
            discovered = await BleakScanner.discover(timeout=self.timeout)

            for device in discovered:
                if self._is_huion_device(device):
                    logger.info(f"Found Huion device: {device.address} - {device.name}")
                    devices.append(DiscoveredDevice(
                        address=device.address,
                        name=device.name or "Unknown",
                        rssi=device.rssi or -999
                    ))

        except Exception as e:
            logger.error(f"Error during scan: {e}")
            raise

        return devices

    def _is_huion_device(self, device) -> bool:
        """Check if a discovered device is a Huion device."""
        if not device.name:
            return False

        device_name = device.name.lower()

        # Check for known Huion device names
        for huion_name in self.HUION_DEVICE_NAMES:
            if huion_name.lower() in device_name:
                return True

        # Check for other Huion indicators
        huion_indicators = ['huion', 'keydial']
        return any(indicator in device_name for indicator in huion_indicators)
