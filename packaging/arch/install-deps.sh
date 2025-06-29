#!/bin/bash
# Install Arch Linux dependencies for huion-keydial-mini

set -e

echo "Installing Arch Linux dependencies for huion-keydial-mini..."

# Install packages available in official repos
echo "Installing packages from official repositories..."
sudo pacman -S --needed --asdeps \
    python-evdev \
    python-bleak \
    python-pyudev \
    python-click \
    python-pyyaml

echo "Dependencies installed successfully!"
echo ""
echo "You can now run: sudo make install-system"
