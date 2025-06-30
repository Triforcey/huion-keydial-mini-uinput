#!/bin/bash
# Build script for Arch Linux package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Building Arch Linux package for huion-keydial-mini-driver..."
echo "Project root: $PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
    echo "Error: pyproject.toml not found. Are you in the project root?"
    exit 1
fi

# Create build directory
BUILD_DIR="$SCRIPT_DIR/build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy PKGBUILD to build directory
cp "$SCRIPT_DIR/PKGBUILD" "$BUILD_DIR/"

# Change to build directory
cd "$BUILD_DIR"

# Build the package
echo "Building package with makepkg..."
PROJECT_ROOT="$PROJECT_ROOT" makepkg --syncdeps --noconfirm

echo ""
echo "Package built successfully!"
echo "Package files:"
ls -la *.pkg.tar.zst 2>/dev/null || echo "No .pkg.tar.zst files found"
ls -la *.pkg.tar.zst.sig 2>/dev/null || echo "No signature files found"

echo ""
echo "To install the package:"
echo "  sudo pacman -U *.pkg.tar.zst"
echo ""
echo "To install dependencies first:"
echo "  sudo pacman -S --needed python-evdev python-bleak python-click python-pyyaml python-dbus-next"
