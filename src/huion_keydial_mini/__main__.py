#!/usr/bin/env python3
"""Main entry point for the Huion Keydial Mini driver."""

import sys
import argparse
from pathlib import Path

from .main import main as driver_main
from .scanner import main as scanner_main


def main():
    """Main entry point with subcommands."""
    parser = argparse.ArgumentParser(
        description="Huion Keydial Mini Linux Driver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  run         Run the driver (default)
  scan        Scan for paired devices
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        default='run',
        choices=['run', 'scan'],
        help='Command to run (default: run)'
    )

    # Parse only the command, pass remaining args to subcommands
    args, remaining = parser.parse_known_args()

    if args.command == 'run':
        # Pass remaining args to the driver
        sys.argv = [sys.argv[0]] + remaining
        driver_main()
    elif args.command == 'scan':
        # Pass remaining args to the scanner
        sys.argv = [sys.argv[0]] + remaining
        scanner_main()


if __name__ == "__main__":
    main()
