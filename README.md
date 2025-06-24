# Huion Keydial Mini Driver

A user space driver for the Huion Keydial Mini bluetooth device that provides HID-over-BLE functionality on Linux.

## Features

- Bluetooth Low Energy (BLE) connectivity using Bleak
- Virtual input device creation using evdev/uinput
- Customizable key mappings and dial settings
- Multi-distribution Linux packaging support
- Command-line interface for device scanning and configuration
- **Device blacklisting to prevent kernel module conflicts**

## Requirements

- Python 3.8+
- Linux with Bluetooth support
- Root privileges (for uinput device creation)

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/your-username/huion-keydial-mini-uinput.git
cd huion-keydial-mini-uinput

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .

# Install udev rules for device blacklisting (recommended)
make install-udev
```

### System Installation

```bash
# Install as a system package
sudo pip install .

# Or build and install a wheel
python -m build
sudo pip install dist/huion_keydial_mini_driver-*.whl

# Install udev rules for device blacklisting
make install-udev
```

## Device Blacklisting

The driver includes udev rules that unbind the `hid-generic` kernel module from Huion Keydial Mini devices. This ensures that your userspace driver can exclusively handle these specific devices.

The udev rules target devices with:
- Vendor ID: `256c` (Huion)
- Product ID: `8251` (Keydial Mini)
- Name containing "Keydial"

### Automatic Installation

```bash
# Install udev rules automatically
make install-udev
```

### Manual Installation

```bash
# Copy udev rules
sudo cp packaging/udev/99-huion-keydial-mini.rules /etc/udev/rules.d/

# Reload udev rules
sudo udevadm control --reload-rules

# Trigger rules for existing devices
sudo udevadm trigger
```

### What the udev rules do:

1. **Unbinds hid-generic** from Huion Keydial Mini devices (vendor: 256c, product: 8251)
2. **Matches devices precisely** by vendor ID, product ID, and name containing "Keydial"
3. **Allows exclusive access** for the userspace driver
4. **Device-specific** - Only affects Huion Keydial Mini devices, not other HID devices

### Troubleshooting Device Conflicts

If you experience conflicts with kernel modules:

```bash
# Check if hid-generic is loaded
lsmod | grep hid

# Check device attributes
sudo udevadm info -a -p $(udevadm info -q path -n /dev/input/eventX)

# Manually unbind hid-generic from a specific device (if needed)
echo "device_id" | sudo tee /sys/bus/hid/drivers/hid-generic/unbind

# Check device ownership
ls -la /dev/input/
ls -la /dev/hidraw*

# Verify udev rules are active
sudo udevadm test /sys/class/hid/hidraw0
```

## Usage

### Scanning for Devices

```bash
# Scan for available Huion devices
huion-keydial-mini --scan
```

### Running the Driver

```bash
# Auto-discover and connect to the first Huion device found
sudo huion-keydial-mini

# Connect to a specific device by MAC address
sudo huion-keydial-mini --device-address AA:BB:CC:DD:EE:FF

# Use a custom configuration file
sudo huion-keydial-mini --config /path/to/config.yaml

# Set log level
sudo huion-keydial-mini --log-level DEBUG
```

### Configuration Management

Use the `keydialctl` command to manage device configuration:

```bash
# List current bindings
keydialctl list-bindings

# Bind a button to a key
keydialctl bind button_1 KEY_F1
keydialctl bind button_2 KEY_CTRL+KEY_C  # Key combinations

# Remove a binding
keydialctl unbind button_1

# Configure dial settings
keydialctl dial --clockwise KEY_VOLUMEUP --counterclockwise KEY_VOLUMEDOWN
keydialctl dial --click KEY_ENTER --sensitivity 1.5

# Set specific device address
keydialctl set-device AA:BB:CC:DD:EE:FF

# Clear device address (auto-discover)
keydialctl clear-device

# List available key codes
keydialctl list-keys

# Reset configuration to defaults
keydialctl reset
```

### Makefile Shortcuts

For development convenience, you can also use Makefile targets:

```bash
# Device blacklisting
make install-udev                                    # Install udev rules

# Configuration management
make config-list                                    # List current bindings
make config-bind BUTTON=button_1 KEY=KEY_F1        # Bind a button
make config-unbind BUTTON=button_1                 # Unbind a button
make config-keys                                    # List available keys
make config-reset                                   # Reset to defaults

# Development tasks
make install-dev                                    # Install in development mode
make scan                                          # Scan for devices
make run                                           # Run driver (requires sudo)
make debug                                         # Run with debug logging
make debug-parser                                  # Test HID parser
```

## Configuration

The driver uses YAML configuration files. It looks for configuration in these locations (in order):

1. `./config.yaml` (current directory)
2. `~/.config/huion-keydial-mini/config.yaml`
3. `/etc/huion-keydial-mini/config.yaml`

### Example Configuration

```yaml
device:
  name: "Huion Keydial Mini"
  address: "AA:BB:CC:DD:EE:FF"  # Optional: specific device address

bluetooth:
  scan_timeout: 10.0
  connection_timeout: 30.0
  reconnect_attempts: 3

uinput:
  device_name: "Huion Keydial Mini"

key_mappings:
  button_1: "KEY_F1"
  button_2: "KEY_F2"
  button_3: "KEY_F3"
  button_4: "KEY_F4"
  button_5: "KEY_F5"
  button_6: "KEY_F6"
  button_7: "KEY_F7"
  button_8: "KEY_F8"

dial_settings:
  sensitivity: 1.0
  clockwise_key: "KEY_VOLUMEUP"
  counterclockwise_key: "KEY_VOLUMEDOWN"
  click_key: "KEY_ENTER"
```

## Systemd Service

Create a systemd service for automatic startup:

```bash
# Create service file
sudo tee /etc/systemd/system/huion-keydial-mini.service << EOF
[Unit]
Description=Huion Keydial Mini Driver
After=bluetooth.target
Wants=bluetooth.target

[Service]
Type=simple
ExecStart=/usr/local/bin/huion-keydial-mini
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl enable huion-keydial-mini.service
sudo systemctl start huion-keydial-mini.service
```

## Development

### Setting up Development Environment

```bash
# Clone and set up the development environment
git clone https://github.com/your-username/huion-keydial-mini-uinput.git
cd huion-keydial-mini-uinput

# Create virtual environment
make venv-dev

# Activate virtual environment
source venv/bin/activate

# Install in development mode
make install-dev

# Install udev rules
make install-udev
```

### Testing

```bash
# Test HID parser with sample data
make debug-parser

# Interactive HID parser testing
make debug-parser-interactive

# Run linters
make lint

# Format code
make format

# Run tests
make test
```

### Debugging

```bash
# Run with debug logging
make debug

# Test device scanning
make scan

# Check device information
sudo huion-keydial-mini --log-level DEBUG --device-address AA:BB:CC:DD:EE:FF
```

## Troubleshooting

### Common Issues

1. **Permission denied for uinput**
   ```bash
   # Add user to input group
   sudo usermod -a -G input $USER
   # Then log out and back in
   ```

2. **Device not found**
   ```bash
   # Check if device is paired
   bluetoothctl paired-devices

   # Check if udev rules are installed
   ls /etc/udev/rules.d/99-huion-keydial-mini.rules
   ```

3. **Kernel module conflicts**
   ```bash
   # Unload conflicting modules
   sudo modprobe -r hid-generic

   # Install udev rules
   make install-udev
   ```

4. **Bluetooth connection issues**
   ```bash
   # Check Bluetooth status
   systemctl status bluetooth

   # Restart Bluetooth service
   sudo systemctl restart bluetooth
   ```

### Debug Information

```bash
# Get detailed device information
sudo huion-keydial-mini --log-level DEBUG

# Check udev rules
sudo udevadm test /sys/class/bluetooth/hci0

# Monitor udev events
sudo udevadm monitor --property --subsystem-match=bluetooth
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
