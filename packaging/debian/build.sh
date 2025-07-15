#!/bin/bash
# Build script for Debian package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Building Debian package for huion-keydial-mini-driver..."
echo "Project root: $PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
    echo "Error: pyproject.toml not found. Are you in the project root?"
    exit 1
fi

# Check if dpkg-buildpackage is available
if ! command -v dpkg-buildpackage >/dev/null 2>&1; then
    echo "Error: dpkg-buildpackage not found. Please install dpkg-dev package."
    exit 1
fi

# Create build directory
BUILD_DIR="$SCRIPT_DIR/build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy project files to build directory
cd "$PROJECT_ROOT"
cp -r src pyproject.toml README.md LICENSE packaging "$BUILD_DIR/"

# Change to build directory
cd "$BUILD_DIR"

# Build the package
echo "Building Debian package..."
dpkg-buildpackage -us -uc -b

echo ""
echo "Package built successfully!"
echo "Package files:"
ls -la ../*.deb 2>/dev/null || echo "No .deb files found"
ls -la ../*.changes 2>/dev/null || echo "No .changes files found"

echo ""
echo "To install the package:"
echo "  sudo dpkg -i ../huion-keydial-mini-driver_*.deb"
echo "  sudo apt-get install -f  # Install any missing dependencies"
echo ""
echo "To install dependencies first:"
echo "  sudo apt-get install python3-evdev python3-bleak python3-pyudev python3-click python3-yaml python3-dbus-next"
