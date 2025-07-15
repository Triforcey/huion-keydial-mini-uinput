#!/bin/bash
# Install RPM dependencies for huion-keydial-mini

set -e

echo "Installing RPM dependencies for huion-keydial-mini..."

# Detect package manager
if command -v dnf >/dev/null 2>&1; then
    PKG_MGR="dnf"
elif command -v yum >/dev/null 2>&1; then
    PKG_MGR="yum"
else
    echo "Error: No supported package manager found (dnf or yum)"
    exit 1
fi

echo "Using package manager: $PKG_MGR"

# Install packages
echo "Installing packages..."
sudo $PKG_MGR install -y \
    python3-evdev \
    python3-bleak \
    python3-pyudev \
    python3-click \
    python3-pyyaml \
    python3-dbus-next

echo "Dependencies installed successfully!"
echo ""
echo "You can now run: sudo make install-system"
