#!/bin/bash
# Simple build script for Huion Keydial Mini Driver

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Building Huion Keydial Mini Driver"

cd "$PROJECT_ROOT"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/

# Build Python wheel and source distribution
echo "Building Python package..."
python3 -m pip install --upgrade build
python3 -m build

echo "Python package built successfully"
echo "Available packages:"
ls -la dist/

# Optional: Build DEB package if on Debian/Ubuntu
if command -v dpkg-buildpackage >/dev/null 2>&1; then
    echo "Building DEB package..."
    dpkg-buildpackage -us -uc -b
    echo "DEB package built"
fi

echo "Build completed!"
