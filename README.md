# Huion Keydial Mini Driver

A Linux driver for the Huion Keydial Mini device that provides HID over GATT support and virtual input device creation.

## Features

- **Bluetooth HID over GATT support** for Huion Keydial Mini
- **Virtual input device creation** using uinput
- **Runtime keybind management** via Unix socket
- **User-level systemd service** (no root required)
- **Advanced event types**: keyboard, mouse, and combo actions
- **Real-time configuration** without service restart
- **Automatic device detection** via DBus monitoring
- **Comprehensive input support**: 167+ keyboard keys and full mouse button/movement support

## Installation

```bash
# Clone the repository
git clone https://github.com/Triforcey/huion-keydial-mini-uinput.git
cd huion-keydial-mini-uinput

# Install dependencies and build
make install-dev

# Install system components
sudo make install-all

# Add user to input group
sudo usermod -a -G input $USER

# Copy and edit configuration
mkdir -p ~/.config/huion-keydial-mini
cp packaging/config.yaml.default ~/.config/huion-keydial-mini/config.yaml
nano ~/.config/huion-keydial-mini/config.yaml

# Start the service
systemctl --user enable --now huion-keydial-mini-user.service
```

## Usage

### Basic Usage

1. **Start the service**:
   ```bash
   systemctl --user start huion-keydial-mini-user.service
   ```

2. **Connect your device** via Bluetooth settings or `bluetoothctl`

3. **Configure key bindings**:
   ```bash
   # List current bindings
   keydialctl list-bindings

   # Show all supported key codes
   keydialctl list-keys

   # Bind button 1 to F1 key
   keydialctl bind BUTTON_1 keyboard KEY_F1

   # Bind dial clockwise to volume up
   keydialctl bind DIAL_CW keyboard KEY_VOLUMEUP

   # Remove a binding
   keydialctl unbind BUTTON_1
   ```

### Supported Action Types

**Keyboard Actions:**
- Single keys: `KEY_F1`, `KEY_ENTER`, `KEY_SPACE`
- Key combinations: `KEY_LEFTCTRL+KEY_C`, `KEY_LEFTALT+KEY_TAB`
- **Comprehensive key support**: 167+ keys including F1-F24, all letters/numbers, modifiers, media keys, system keys, and more
- Examples: `KEY_BRIGHTNESSUP`, `KEY_BLUETOOTH`, `KEY_WLAN`, `KEY_MICMUTE`, `KEY_CALCULATOR`
- Use `keydialctl list-keys` to see all supported keys

**Mouse Actions:**
- **Mouse buttons**: `BTN_LEFT`, `BTN_RIGHT`, `BTN_MIDDLE`, `BTN_SIDE`, `BTN_EXTRA`, `BTN_FORWARD`, `BTN_BACK`
- **Mouse movement**: X/Y relative movement support
- **Mouse scroll**: Vertical and horizontal scroll wheel support

**Combo Actions:**
- Mixed keyboard/mouse actions (future enhancement)

### Service Management

```bash
# Check service status
systemctl --user status huion-keydial-mini-user.service

# Restart service
systemctl --user restart huion-keydial-mini-user.service

# Stop service
systemctl --user stop huion-keydial-mini-user.service

# View logs
journalctl --user -u huion-keydial-mini-user.service -f
```

### Device Configuration

```bash
# Set specific device address
keydialctl set-device AA:BB:CC:DD:EE:FF

# Clear device address (auto-discover)
keydialctl clear-device
```

## Configuration

The configuration file is located at `~/.config/huion-keydial-mini/config.yaml`:

```yaml
# Device settings
device_address: null  # Auto-discover if not set

# Initial key mappings (loaded into memory)
key_mappings: {}

# Dial settings
dial_settings:
  DIAL_CW: "KEY_VOLUMEUP"      # Send volume up when dial is turned clockwise
  DIAL_CCW: "KEY_VOLUMEDOWN"   # Send volume down when dial is turned counterclockwise
  DIAL_CLICK: "KEY_MUTE"       # Send mute when dial is clicked
  sensitivity: 1.0             # Dial sensitivity (1.0 = normal, 2.0 = double, 0.5 = half)

# UInput device settings
uinput_device_name: "Huion Keydial Mini"

# Connection settings
connection_timeout: 10.0

# Debug mode
debug_mode: false

# Bluetooth settings
bluetooth:
  auto_reconnect: true  # Enable automatic connection detection via DBus
```

**Note**: Key mappings in the config file are loaded as initial bindings, but can be modified at runtime using `keydialctl`.

## Additional Documentation

- **[Architecture Details](ARCHITECTURE.md)** - Technical architecture and component overview
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
- **[Contributing Guide](CONTRIBUTING.md)** - Development setup and contribution guidelines

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Bleak](https://github.com/hbldh/bleak) for Bluetooth Low Energy support
- [evdev](https://github.com/gvalkov/python-evdev) for Linux input device handling
- [Click](https://click.palletsprojects.com/) for command-line interface
- [dbus-next](https://github.com/altdesktop/python-dbus-next) for DBus integration
