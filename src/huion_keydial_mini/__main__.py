#!/usr/bin/env python3
"""Main entry point for the Huion Keydial Mini driver."""

import sys
import argparse
from pathlib import Path

from .main import main as driver_main


def main():
    """Main entry point."""
    # Pass all args to the driver
    driver_main()


if __name__ == "__main__":
    main()
