#!/usr/bin/env python3
"""Simple event logger for Huion Keydial Mini HID events."""

import logging
import sys
import argparse
from typing import List, Optional
from datetime import datetime
import asyncio

from .config import Config
from .hid_parser import HIDParser, InputEvent, EventType


class EventLogger:
    """Simple logger for HID events."""

    def __init__(self, config: Config):
        self.config = config
        self.parser = HIDParser(config)
        self.event_count = 0
        self.debug_mode = getattr(config, "debug_mode", False)

    def log_event(self, event: InputEvent, raw_data: Optional[bytearray] = None):
        """Log a single HID event in a readable format."""
        self.event_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Determine event description
        if event.event_type == EventType.KEY_PRESS:
            action = "PRESS"
        elif event.event_type == EventType.KEY_RELEASE:
            action = "RELEASE"
        elif event.event_type == EventType.DIAL_ROTATE:
            direction = "CW" if event.direction and event.direction > 0 else "CCW"
            action = f"DIAL {direction}"
        elif event.event_type == EventType.DIAL_CLICK:
            action = "DIAL CLICK"
        else:
            action = event.event_type.value.upper()

        # Build the log line
        parts = [f"[{timestamp}] #{self.event_count:03d} {action}"]

        if event.key_code:
            parts.append(f"key={event.key_code}")

        if event.direction is not None:
            parts.append(f"dir={event.direction:+d}")

        if event.value is not None:
            parts.append(f"val={event.value}")

        if raw_data:
            parts.append(f"raw={raw_data.hex()}")

        print(" ".join(parts))
        sys.stdout.flush()  # Ensure immediate output

    def log_raw_data(self, data: bytearray):
        """Log raw HID data."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] RAW: {data.hex()}")
        sys.stdout.flush()

    def log_parser_events(self, data: bytearray, characteristic_uuid: Optional[str] = None):
        """Parse and log events from raw HID data."""
        # Debug: Print all incoming events to see what we're getting
        if (self.debug_mode): print(f"DEBUG: Received event from characteristic: {characteristic_uuid}")
        if (self.debug_mode): print(f"DEBUG: Raw data: {data.hex()}")

        # Accept standard HID characteristics and let the parser handle the data
        if characteristic_uuid and self.debug_mode:
            handle = self._extract_handle_from_uuid(characteristic_uuid)
            print(f"DEBUG: Extracted handle: {handle}")

            # Accept standard HID Report characteristic (2a4d) and any other HID characteristics
            if "2a4d" in characteristic_uuid.lower() or "2a4b" in characteristic_uuid.lower():
                print(f"DEBUG: Processing HID characteristic {handle}")
            else:
                print(f"DEBUG: Skipping non-HID characteristic {handle}")
                return

        events = self.parser.parse(data, characteristic_uuid)

        if events:
            for event in events:
                self.log_event(event, data)
        elif self.debug_mode:
            # Log raw data for HID characteristics
            if characteristic_uuid and ("2a4d" in characteristic_uuid.lower() or "2a4b" in characteristic_uuid.lower()):
                self.log_raw_data(data)
                print(f"  Characteristic: {characteristic_uuid}")

    def _extract_handle_from_uuid(self, uuid: str) -> str:
        """Extract handle from characteristic UUID."""
        # UUID format: "0000001f-0000-1000-8000-00805f9b34fb"
        # Extract the handle part (last 2 digits before the first dash)
        parts = uuid.split('-')
        if parts and len(parts[0]) >= 8:
            return parts[0][-2:]  # Last 2 characters
        return ""


def setup_clean_logging():
    """Set up clean logging without debug noise."""
    # Disable all the verbose Bluetooth logging
    logging.getLogger('bleak').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('dbus_fast').setLevel(logging.WARNING)

    # Only show our own logs at INFO level
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )


def main():
    """Main entry point for the event logger."""
    parser = argparse.ArgumentParser(
        description="Simple HID event logger for Huion Keydial Mini"
    )
    parser.add_argument(
        '--config', '-c',
        default=None,
        help='Configuration file path (default: auto-detect)'
    )
    parser.add_argument(
        '--raw', '-r',
        action='store_true',
        help='Show raw HID data in addition to parsed events'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Test with sample data instead of running the driver'
    )

    args = parser.parse_args()

    # Set up clean logging
    setup_clean_logging()

    try:
        # Load configuration
        config = Config.load(args.config)
        logger = EventLogger(config)

        if args.test:
            # Test mode with sample data
            print("=== Testing Event Logger with Sample Data ===")
            test_data = [
                bytearray([0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),  # Button 1 press
                bytearray([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),  # Button 1 release
                bytearray([0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),  # Dial clockwise
                bytearray([0x02, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00]),  # Dial counterclockwise
                bytearray([0x02, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]),  # Dial click
            ]

            for i, data in enumerate(test_data, 1):
                print(f"\n--- Test {i} ---")
                logger.log_parser_events(data)

        else:
            # Run the actual driver with event logging
            print("=== Huion Keydial Mini Event Logger ===")
            print("Connecting to device...")
            print("Press Ctrl+C to stop")
            print()

            # Import and run the main driver with our event logger
            from .main import run_driver_with_logger
            asyncio.run(run_driver_with_logger(logger, show_raw=args.raw, auto_connect=True))

    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
