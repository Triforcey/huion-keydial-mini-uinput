#!/bin/bash
# Installation script for Huion Keydial Mini user-level service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for user-level installation"
   exit 1
fi

print_status "Installing Huion Keydial Mini user-level service..."

# Get user information
USER=$(whoami)
USER_HOME=$(eval echo ~$USER)

print_status "Installing for user: $USER"

# Create necessary directories
print_status "Creating directories..."
mkdir -p "$USER_HOME/.config/systemd/user"
mkdir -p "$USER_HOME/.config/huion-keydial-mini"
mkdir -p "$USER_HOME/.local/share/huion-keydial-mini"

# Install the user service file
print_status "Installing systemd user service..."
cp packaging/systemd/huion-keydial-mini-user.service "$USER_HOME/.config/systemd/user/huion-keydial-mini.service"

# Create default config if it doesn't exist
if [[ ! -f "$USER_HOME/.config/huion-keydial-mini/config.yaml" ]]; then
    print_status "Creating default configuration..."
    cat > "$USER_HOME/.config/huion-keydial-mini/config.yaml" << EOF
# Huion Keydial Mini Configuration
device_address: null  # Will auto-discover if not set

# Key mappings (will be loaded into memory)
key_mappings: {}

# Dial settings
dial_settings:
  clockwise_key: KEY_VOLUMEUP
  counterclockwise_key: KEY_VOLUMEDOWN
  click_key: KEY_MUTE
  sensitivity: 1.0

# UInput device settings
uinput_device_name: "Huion Keydial Mini"

# Connection settings
connection_timeout: 10.0

# Debug mode
debug_mode: false
EOF
fi

# Install udev rules (requires sudo)
print_status "Installing udev rules..."
if command -v sudo &> /dev/null; then
    sudo cp packaging/udev/99-huion-keydial-mini-user.rules /etc/udev/rules.d/
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    print_status "Udev rules installed successfully"
else
    print_warning "sudo not available. Please manually install udev rules:"
    print_warning "  cp packaging/udev/99-huion-keydial-mini-user.rules /etc/udev/rules.d/"
    print_warning "  udevadm control --reload-rules"
    print_warning "  udevadm trigger"
fi

# Add user to input group if not already a member
if groups $USER | grep -q "\binput\b"; then
    print_status "User already in input group"
else
    print_warning "User not in input group. Adding user to input group..."
    if command -v sudo &> /dev/null; then
        sudo usermod -a -G input $USER
        print_status "User added to input group. Please log out and back in for changes to take effect."
    else
        print_warning "sudo not available. Please manually add user to input group:"
        print_warning "  usermod -a -G input $USER"
    fi
fi

# Enable and start the service
print_status "Enabling systemd user service..."
systemctl --user enable huion-keydial-mini.service

print_status "Starting systemd user service..."
systemctl --user start huion-keydial-mini.service

# Check service status
if systemctl --user is-active --quiet huion-keydial-mini.service; then
    print_status "Service started successfully!"
else
    print_error "Service failed to start. Check logs with:"
    print_error "  journalctl --user -u huion-keydial-mini.service"
fi

print_status "Installation complete!"
print_status ""
print_status "Usage:"
print_status "  keydialctl list-bindings          # List current bindings"
print_status "  keydialctl bind button_1 keyboard KEY_F1  # Bind button 1 to F1"
print_status "  keydialctl bind dial_clockwise mouse scroll  # Bind dial to scroll"
print_status "  keydialctl unbind button_1        # Remove binding"
print_status ""
print_status "Service management:"
print_status "  systemctl --user status huion-keydial-mini.service"
print_status "  systemctl --user restart huion-keydial-mini.service"
print_status "  systemctl --user stop huion-keydial-mini.service"
print_status ""
print_status "Logs:"
print_status "  journalctl --user -u huion-keydial-mini.service -f"
