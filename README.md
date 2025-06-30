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

## Architecture

### Automatic Connection Detection

The driver uses DBus monitoring to automatically detect when your Huion Keydial Mini connects or disconnects:

```
DBus Monitoring → Device Connection Event → Automatic Attachment → HID Processing → Virtual Input
```

**Key Features:**
- **Start early**: Service can start at boot time, even before device connection
- **Automatic attachment**: Detects device connections via BlueZ DBus signals
- **No manual intervention**: No need to restart service when connecting/disconnecting
- **Multiple device support**: Can target specific devices or auto-discover any Huion device

### Runtime Keybind Management

The driver uses an in-memory keybind manager with Unix socket control interface:

```
HID Parser → Event → In-Memory Keybind Map → UInput Handler → Virtual Device
```

**Key Features:**
- **In-Memory Mappings**: Config initializes bindings, but they can be modified at runtime
- **Unix Socket Control**: `keydialctl` communicates with the service via Unix socket
- **Advanced Actions**: Support for keyboard combos, mouse actions, and mixed events
- **No Service Restart**: Changes take effect immediately without restarting the service

### User-Level Service

The driver runs as a user-level systemd service, providing:
- **Better Security**: No need to run as root
- **User Isolation**: Each user can have their own service instance
- **Easier Management**: User-specific configuration and logs

## Installation

### Quick Installation

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

### Manual Installation

If you prefer manual installation:

1. **Install udev rules** (requires sudo):
   ```bash
   sudo cp packaging/udev/99-huion-keydial-mini.rules /etc/udev/rules.d/
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

2. **Add user to input group**:
   ```bash
   sudo usermod -a -G input $USER
   # Log out and back in for changes to take effect
   ```

3. **Install systemd user service**:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp packaging/systemd/huion-keydial-mini-user.service ~/.config/systemd/user/
   systemctl --user enable huion-keydial-mini-user.service
   systemctl --user start huion-keydial-mini-user.service
   ```

## Usage

### Automatic Connection Detection

The driver automatically detects device connections via DBus monitoring:

```bash
# Start the service
systemctl --user start huion-keydial-mini-user.service

# Connect your device via bluetoothctl or system settings
bluetoothctl connect AA:BB:CC:DD:EE:FF

# The driver automatically detects and attaches to the device
journalctl --user -u huion-keydial-mini-user.service -f
```

### Runtime Keybind Management

The `keydialctl` command communicates with the running service via Unix socket:

```bash
# List current bindings
keydialctl list-bindings

# Bind button 1 to F1 key
keydialctl bind BUTTON_1 keyboard KEY_F1

# Bind button 2 to Ctrl+C combo
keydialctl bind BUTTON_2 keyboard KEY_LEFTCTRL+KEY_C

# Bind dial clockwise to volume up
keydialctl bind DIAL_CW keyboard KEY_VOLUMEUP

# Bind dial click to mute
keydialctl bind DIAL_CLICK keyboard KEY_MUTE

# Remove a binding
keydialctl unbind BUTTON_1
```

### Supported Action Types

**Keyboard Actions:**
- Single keys: `KEY_F1`, `KEY_ENTER`, `KEY_SPACE`
- Key combinations: `KEY_LEFTCTRL+KEY_C`, `KEY_LEFTALT+KEY_TAB`
- All standard keys: A-Z, 0-9, function keys, modifiers, etc.

**Mouse Actions:**
- Scroll: `scroll` (uses dial direction)
- Clicks: `left_click`, `right_click`, `middle_click`

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

## Troubleshooting

### Service Won't Start

1. **Check logs**:
   ```bash
   journalctl --user -u huion-keydial-mini-user.service -f
   ```

2. **Verify uinput access**:
   ```bash
   ls -la /dev/uinput
   groups $USER  # Should include 'input'
   ```

3. **Check Bluetooth permissions**:
   ```bash
   bluetoothctl list
   ```

### Keybinds Not Working

1. **Check if service is running**:
   ```bash
   systemctl --user is-active huion-keydial-mini-user.service
   ```

2. **Verify bindings**:
   ```bash
   keydialctl list-bindings
   ```

3. **Test with event logger**:
   ```bash
   huion-keydial-mini --log-level DEBUG
   ```

### Permission Issues

If you get permission errors:

1. **Ensure user is in input group**:
   ```bash
   groups $USER
   ```

2. **Reload udev rules**:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

3. **Check uinput permissions**:
   ```bash
   ls -la /dev/uinput
   ```

### Device Not Connecting

1. **Check if device is paired**:
   ```bash
   bluetoothctl devices
   ```

2. **Verify device is connected**:
   ```bash
   bluetoothctl info AA:BB:CC:DD:EE:FF
   ```

3. **Check service logs for connection events**:
   ```bash
   journalctl --user -u huion-keydial-mini-user.service -f
   ```

## Development

### Building from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/
```

### Testing

```bash
# Test event logger
python -m huion_keydial_mini.event_logger --test

# Test with debug logging
python -m huion_keydial_mini --log-level DEBUG

# Test HID diagnostic tool
python diagnose_hid.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Acknowledgments

- [Bleak](https://github.com/hbldh/bleak) for Bluetooth Low Energy support
- [evdev](https://github.com/gvalkov/python-evdev) for Linux input device handling
- [Click](https://click.palletsprojects.com/) for command-line interface
- [dbus-next](https://github.com/altdesktop/python-dbus-next) for DBus integration
