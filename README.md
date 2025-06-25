# Huion Keydial Mini Driver

A Linux driver for the Huion Keydial Mini device that provides HID over GATT support and virtual input device creation.

## Features

- **Bluetooth HID over GATT support** for Huion Keydial Mini
- **Virtual input device creation** using uinput
- **Runtime keybind management** via Unix socket
- **User-level systemd service** (no root required)
- **Advanced event types**: keyboard, mouse, and combo actions
- **Real-time configuration** without service restart

## Architecture

### New Runtime Keybind Management

The driver now uses an in-memory keybind manager with Unix socket control interface:

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

### User-Level Service Installation

```bash
# Run the user installation script
./packaging/install-user.sh
```

This script will:
1. Create necessary directories
2. Install the systemd user service
3. Set up udev rules for uinput access
4. Add user to the input group
5. Enable and start the service

### Manual Installation

If you prefer manual installation:

1. **Install udev rules** (requires sudo):
   ```bash
   sudo cp packaging/udev/99-huion-keydial-mini-user.rules /etc/udev/rules.d/
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
   cp packaging/systemd/huion-keydial-mini-user.service ~/.config/systemd/user/huion-keydial-mini.service
   systemctl --user enable huion-keydial-mini.service
   systemctl --user start huion-keydial-mini.service
   ```

## Usage

### Runtime Keybind Management

The `keydialctl` command now communicates with the running service via Unix socket:

```bash
# List current bindings
keydialctl list-bindings

# Bind button 1 to F1 key
keydialctl bind button_1 keyboard KEY_F1

# Bind button 2 to Ctrl+C combo
keydialctl bind button_2 keyboard KEY_LEFTCTRL+KEY_C

# Bind dial clockwise to mouse scroll
keydialctl bind dial_clockwise mouse scroll

# Bind dial click to left mouse click
keydialctl bind dial_click mouse left_click

# Remove a binding
keydialctl unbind button_1
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
systemctl --user status huion-keydial-mini.service

# Restart service
systemctl --user restart huion-keydial-mini.service

# Stop service
systemctl --user stop huion-keydial-mini.service

# View logs
journalctl --user -u huion-keydial-mini.service -f
```

### Device Discovery

```bash
# Scan for available devices
huion-keydial-mini --scan

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
```

**Note**: Key mappings in the config file are loaded as initial bindings, but can be modified at runtime using `keydialctl`.

## Troubleshooting

### Service Won't Start

1. **Check logs**:
   ```bash
   journalctl --user -u huion-keydial-mini.service -f
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
   systemctl --user is-active huion-keydial-mini.service
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

# Test device scanning
python -m huion_keydial_mini --scan

# Test with debug logging
python -m huion_keydial_mini --log-level DEBUG
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

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
