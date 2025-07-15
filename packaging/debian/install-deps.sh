#!/bin/bash
# Install Debian dependencies for huion-keydial-mini

set -e

echo "Installing Debian/Ubuntu dependencies for huion-keydial-mini..."

# Update package list
echo "Updating package list..."
sudo apt-get update

# Install packages
echo "Installing packages..."
sudo apt-get install -y \
    python3-evdev \
    python3-bleak \
    python3-pyudev \
    python3-click \
    python3-yaml \
    python3-dbus-next

echo "Dependencies installed successfully!"
echo ""
echo "You can now run: sudo make install-system"
