# Huion Keydial Mini Driver

A user space driver for the Huion Keydial Mini bluetooth device that provides HID-over-BLE functionality on Linux.

## Features

- Bluetooth Low Energy (BLE) connectivity using Bleak
- Virtual input device creation using evdev/uinput
- Customizable key mappings and dial settings
- Multi-distribution Linux packaging support
- Command-line interface for device scanning and configuration

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
```

### System Installation

```bash
# Install as a system package
sudo pip install .

# Or build and install a wheel
python -m build
sudo pip install dist/huion_keydial_mini_driver-*.whl
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
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install pytest black flake8 mypy
```

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
flake8 src/
mypy src/
```

## Building Packages

### Building Python Wheel

```bash
pip install build
python -m build
```

### Building DEB Package

```bash
# Install build dependencies
sudo apt install build-essential debhelper dh-python python3-all python3-setuptools

# Build the package
dpkg-buildpackage -us -uc -b
```

### Building RPM Package

```bash
# Install build dependencies
sudo dnf install rpm-build python3-devel

# Build the package
python setup.py bdist_rpm
```

## Troubleshooting

### Permission Issues

The driver requires root privileges to create uinput devices. Make sure to run with `sudo`.

### Bluetooth Issues

1. Ensure Bluetooth is enabled: `sudo systemctl enable bluetooth`
2. Check if the device is paired: `bluetoothctl paired-devices`
3. Make sure no other applications are using the device

### Device Not Found

1. Verify the device is in pairing mode
2. Check the device name matches the expected names in the scanner
3. Try scanning with a longer timeout: `--scan-timeout 30`

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
