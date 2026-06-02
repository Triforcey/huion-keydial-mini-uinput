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

# Check for read-only filesystem
check_writable() {
    local dir="$1"
    local test_file="$dir/.write_test_$$"
    touch "$test_file" 2>/dev/null && rm -f "$test_file" && return 0 || return 1
}

# Check if /usr is read-only (atomic filesystem)
if ! check_writable "$BIN_DIR"; then
    echo "WARNING: $BIN_DIR is read-only (atomic filesystem detected)"
    echo ""
    echo "On read-only filesystems, udev rules and system binaries cannot be installed."
    echo "Options:"
    echo "  1. Use a system package (e.g., NixOS module, Flatpak, etc.)"
    echo "  2. Manually integrate the unbind script into your system's udev configuration"
    echo "  3. Run without the unbind step (device may not work correctly)"
    echo ""
    read -p "Continue anyway to check if /etc is writable? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install unbind script
if check_writable "$BIN_DIR"; then
    echo "Installing unbind script to $BIN_DIR..."
    install -m "$SCRIPT_PERMS" "$SCRIPT_DIR/udev/unbind-huion.sh" "$BIN_DIR/"
    echo "Unbind script installed with permissions $SCRIPT_PERMS"
else
    echo "SKIPPED: Cannot write to $BIN_DIR (read-only filesystem)"
fi

# Install udev rules
if check_writable "$UDEV_RULES_DIR"; then
    echo "Installing udev rules to $UDEV_RULES_DIR..."
    install -m "$UDEV_PERMS" "$SCRIPT_DIR/udev/99-huion-keydial-mini.rules" "$UDEV_RULES_DIR/"
    echo "Udev rules installed with permissions $UDEV_PERMS"

    # Reload udev rules
    echo "Reloading udev rules..."
    udevadm control --reload-rules

    # Trigger rules for existing devices
    echo "Triggering rules for existing devices..."
    udevadm trigger
else
    echo "SKIPPED: Cannot write to $UDEV_RULES_DIR (read-only filesystem)"
    echo ""
    echo "On this system, udev rules cannot be installed automatically."
    echo "You may need to manually configure udev or use an alternative approach."
fi

echo ""
echo "Installation complete!"
echo ""
if check_writable "$BIN_DIR"; then
    echo "Installed files with permissions:"
    echo "  - $BIN_DIR/unbind-huion.sh: $SCRIPT_PERMS"
fi
echo ""
echo "The udev rules will now:"
echo "1. Unbind hid-generic from Huion Keydial Mini devices (vendor: 256c, product: 8251)"
echo "2. Match devices by vendor ID, product ID, and name containing 'Keydial'"
echo "3. Use a script to find the correct kernel device ID for unbinding"
echo "4. Allow your userspace driver to claim the device exclusively"
echo ""
echo "You may need to reconnect your device for changes to take effect."
