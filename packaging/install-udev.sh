#!/bin/bash
# Installation script for Huion Keydial Mini udev rules

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UDEV_RULES_DIR="/etc/udev/rules.d"
BIN_DIR="/usr/local/bin"

# Permission constants
UDEV_PERMS="644"
SCRIPT_PERMS="755"

echo "Installing Huion Keydial Mini udev rules..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

# Install unbind script
echo "Installing unbind script..."
install -m "$SCRIPT_PERMS" "$SCRIPT_DIR/udev/unbind-huion.sh" "$BIN_DIR/"
echo "Unbind script installed with permissions $SCRIPT_PERMS"

# Install udev rules
echo "Installing udev rules..."
install -m "$UDEV_PERMS" "$SCRIPT_DIR/udev/99-huion-keydial-mini.rules" "$UDEV_RULES_DIR/"
echo "Udev rules installed with permissions $UDEV_PERMS"

# Reload udev rules
echo "Reloading udev rules..."
udevadm control --reload-rules

# Trigger rules for existing devices
echo "Triggering rules for existing devices..."
udevadm trigger

echo "Installation complete!"
echo ""
echo "Installed files with permissions:"
echo "  - $BIN_DIR/unbind-huion.sh: $SCRIPT_PERMS"
echo "  - $UDEV_RULES_DIR/99-huion-keydial-mini.rules: $UDEV_PERMS"
echo ""
echo "The udev rules will now:"
echo "1. Unbind hid-generic from Huion Keydial Mini devices (vendor: 256c, product: 8251)"
echo "2. Match devices by vendor ID, product ID, and name containing 'Keydial'"
echo "3. Use a script to find the correct kernel device ID for unbinding"
echo "4. Allow your userspace driver to claim the device exclusively"
echo ""
echo "You may need to reconnect your device for changes to take effect."
