#!/usr/bin/env python3
"""Diagnostic script to capture and analyze raw HID events from Huion Keydial Mini."""

import asyncio
import logging
import sys
import argparse
from datetime import datetime
from typing import Optional, Dict, Any
import json

from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Huion Keydial Mini service and characteristic UUIDs
HID_SERVICE_UUID = "1812"  # Standard HID Service
HID_REPORT_UUID = "2a4d"   # HID Report
HID_REPORT_MAP_UUID = "2a4b"  # HID Report Map
HID_CONTROL_POINT_UUID = "2a4c"  # HID Control Point

# Alternative UUIDs that might be used
ALTERNATIVE_UUIDS = [
    "0000ff00-0000-1000-8000-00805f9b34fb",  # Common Huion UUID
    "0000ff01-0000-1000-8000-00805f9b34fb",
    "0000ff02-0000-1000-8000-00805f9b34fb",
]

class HIDDiagnostic:
    """Diagnostic tool for HID events."""

    def __init__(self, device_address: Optional[str] = None):
        self.device_address = device_address
        self.client: Optional[BleakClient] = None
        self.connected = False
        self.event_count = 0
        self.raw_events = []
        self.characteristics_found = []

    async def scan_for_devices(self):
        """Scan for Huion devices."""
        print("=== Scanning for Huion devices ===")

        devices = await BleakScanner.discover(timeout=10.0)
        huion_devices = []

        for device in devices:
            if device.name and "huion" in device.name.lower():
                huion_devices.append(device)
                print(f"Found: {device.name} ({device.address})")
                if device.metadata:
                    print(f"  Metadata: {device.metadata}")

        if not huion_devices:
            print("No Huion devices found. Scanning all devices...")
            for device in devices:
                if device.name:
                    print(f"Device: {device.name} ({device.address})")

        return huion_devices

    async def connect_to_device(self, address: str):
        """Connect to a specific device."""
        print(f"\n=== Connecting to {address} ===")

        try:
            self.client = BleakClient(address)
            await self.client.connect()
            self.connected = True
            print(f"Connected to {address}")

            # Get device info
            await self.print_device_info()

        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

        return True

    async def print_device_info(self):
        """Print detailed device information."""
        if not self.client:
            return

        print("\n=== Device Information ===")

        try:
            services = list(self.client.services)
            print(f"Services found: {len(services)}")

            for service in services:
                print(f"\nService: {service.uuid}")
                print(f"  Description: {service.description}")

                for char in service.characteristics:
                    print(f"  Characteristic: {char.uuid}")
                    print(f"    Properties: {list(char.properties)}")
                    print(f"    Description: {char.description}")

                    # Check if this looks like an HID characteristic
                    if "notify" in char.properties or "indicate" in char.properties:
                        self.characteristics_found.append(char)
                        print(f"    *** Potential HID characteristic ***")

                    # Try to read descriptor if available
                    if char.descriptors:
                        for desc in char.descriptors:
                            try:
                                value = await self.client.read_gatt_descriptor(desc.handle)
                                print(f"    Descriptor {desc.uuid}: {value.hex()}")
                            except Exception as e:
                                print(f"    Descriptor {desc.uuid}: Error reading - {e}")

        except Exception as e:
            print(f"Error getting device info: {e}")

    async def subscribe_to_characteristics(self):
        """Subscribe to all potential HID characteristics."""
        if not self.client or not self.characteristics_found:
            print("No characteristics to subscribe to")
            return

        print(f"\n=== Subscribing to {len(self.characteristics_found)} characteristics ===")

        for char in self.characteristics_found:
            try:
                await self.client.start_notify(char.uuid, self.handle_notification)
                print(f"Subscribed to: {char.uuid}")
            except Exception as e:
                print(f"Failed to subscribe to {char.uuid}: {e}")

    async def handle_notification(self, sender, data: bytearray):
        """Handle incoming notifications."""
        self.event_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Store raw event
        event_data = {
            'timestamp': timestamp,
            'event_number': self.event_count,
            'sender': str(sender),
            'data_hex': data.hex(),
            'data_length': len(data),
            'data_bytes': list(data)
        }
        self.raw_events.append(event_data)

        # Print event
        print(f"\n[{timestamp}] Event #{self.event_count:03d}")
        print(f"  Sender: {sender}")
        print(f"  Data: {data.hex()}")
        print(f"  Length: {len(data)} bytes")
        print(f"  Bytes: {list(data)}")

        # Try to interpret the data
        self.interpret_data(data)

    def interpret_data(self, data: bytearray):
        """Try to interpret the HID data."""
        if len(data) == 0:
            print("  Interpretation: Empty data")
            return

        print("  Interpretation:")

        # Try different interpretations
        interpretations = []

        # 1. Check if it's a button report
        if len(data) >= 2:
            if data[0] == 0x01:
                button_state = data[1]
                interpretations.append(f"Button report: state={button_state:02x} ({button_state})")

                # Check individual buttons
                for i in range(8):
                    if button_state & (1 << i):
                        interpretations.append(f"  Button {i+1} pressed")

            elif data[0] == 0x02:
                if len(data) >= 4:
                    # Try to interpret as dial data
                    try:
                        dial_delta = int.from_bytes(data[1:3], byteorder='little', signed=True)
                        dial_click = data[3] & 0x01
                        interpretations.append(f"Dial report: delta={dial_delta}, click={dial_click}")
                    except:
                        interpretations.append(f"Dial report (raw): {data[1:4].hex()}")

            elif data[0] == 0x00:
                if len(data) >= 6:
                    button_state = data[1]
                    try:
                        dial_delta = int.from_bytes(data[3:5], byteorder='little', signed=True)
                        dial_click = data[5] & 0x01
                        interpretations.append(f"Combined report: buttons={button_state:02x}, dial_delta={dial_delta}, click={dial_click}")
                    except:
                        interpretations.append(f"Combined report (raw): {data[1:6].hex()}")

        # 2. Check for standard HID format
        if len(data) >= 1:
            report_id = data[0]
            interpretations.append(f"Report ID: {report_id:02x}")

            # Look for button state in common positions
            for i in range(1, min(4, len(data))):
                if data[i] != 0:
                    interpretations.append(f"Non-zero byte at position {i}: {data[i]:02x}")

        # 3. Check for patterns
        if len(data) >= 8:
            # Check if it looks like a standard HID report
            if all(b == 0 for b in data[1:]):
                interpretations.append("All-zero payload (idle report)")
            else:
                interpretations.append("Mixed data (active report)")

        # Print interpretations
        for interpretation in interpretations:
            print(f"    {interpretation}")

    async def run_diagnostic(self, duration: int = 60):
        """Run the diagnostic for a specified duration."""
        print(f"\n=== Running diagnostic for {duration} seconds ===")
        print("Press buttons and rotate the dial on your Huion Keydial Mini")
        print("Press Ctrl+C to stop early")

        try:
            await asyncio.sleep(duration)
        except KeyboardInterrupt:
            print("\nStopped by user")

        print(f"\n=== Diagnostic complete ===")
        print(f"Total events captured: {self.event_count}")

        if self.raw_events:
            await self.save_results()

    async def save_results(self):
        """Save diagnostic results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hid_diagnostic_{timestamp}.json"

        results = {
            'device_address': self.device_address,
            'total_events': self.event_count,
            'characteristics_found': [str(c.uuid) for c in self.characteristics_found],
            'events': self.raw_events
        }

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to: {filename}")

    async def cleanup(self):
        """Clean up connections."""
        if self.client and self.connected:
            await self.client.disconnect()
            print("Disconnected from device")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="HID Diagnostic Tool for Huion Keydial Mini")
    parser.add_argument('--address', '-a', help='Device address to connect to')
    parser.add_argument('--scan', '-s', action='store_true', help='Scan for devices only')
    parser.add_argument('--duration', '-d', type=int, default=60, help='Diagnostic duration in seconds')

    args = parser.parse_args()

    diagnostic = HIDDiagnostic(args.address)

    try:
        if args.scan:
            await diagnostic.scan_for_devices()
            return

        if not args.address:
            # Scan and let user choose
            devices = await diagnostic.scan_for_devices()
            if not devices:
                print("No Huion devices found. Please specify an address manually.")
                return

            if len(devices) == 1:
                args.address = devices[0].address
                print(f"Auto-selecting: {devices[0].name} ({args.address})")
            else:
                print("\nMultiple devices found. Please specify one with --address")
                return

        # Connect and run diagnostic
        if await diagnostic.connect_to_device(args.address):
            await diagnostic.subscribe_to_characteristics()
            await diagnostic.run_diagnostic(args.duration)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await diagnostic.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
