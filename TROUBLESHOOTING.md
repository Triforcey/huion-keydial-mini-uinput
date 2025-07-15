# Troubleshooting

## Service Won't Start

1. **Check logs**:
   ```bash
   journalctl --user -u huion-keydial-mini-user.service -f
   ```

2. **Verify uinput access**:
   > Shouldn't be necessary if running as a user service
   ```bash
   ls -la /dev/uinput
   groups $USER  # Should include 'input'
   ```

3. **Check Bluetooth permissions**:
   ```bash
   bluetoothctl list
   ```

## Keybinds Not Working

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

## Permission Issues

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

## Device Not Connecting

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

## Common Issues and Solutions

### Service Fails to Start with "Permission Denied"

**Problem**: The service cannot access `/dev/uinput` or create virtual devices.

**Solution**:
1. Add user to input group: `sudo usermod -a -G input $USER`
2. Log out and back in to apply group changes
3. Restart the service: `systemctl --user restart huion-keydial-mini-user.service`

### Device Connects but No Key Events

**Problem**: Device is connected but pressing buttons doesn't trigger actions.

**Solution**:
1. Check if keybindings are configured: `keydialctl list-bindings`
2. Verify the service is receiving HID events: `journalctl --user -u huion-keydial-mini-user.service -f`
3. Test with debug logging: `huion-keydial-mini --log-level DEBUG`

### Bluetooth Connection Issues

**Problem**: Device won't connect or keeps disconnecting.

**Solution**:
1. Ensure device is in pairing mode
2. Clear Bluetooth cache: `bluetoothctl remove AA:BB:CC:DD:EE:FF` then re-pair
3. Check Bluetooth service status: `systemctl status bluetooth`
4. Restart Bluetooth service: `sudo systemctl restart bluetooth`

### UInput Device Not Created

**Problem**: Virtual input device is not being created.

**Solution**:
1. Check if `uinput` module is loaded: `lsmod | grep uinput`
2. Load the module if missing: `sudo modprobe uinput`
3. Verify device creation permissions: `ls -la /dev/uinput`
4. Check service logs for device creation errors

### High CPU Usage

**Problem**: Service is consuming excessive CPU resources.

**Solution**:
1. Check for excessive logging: Set `debug_mode: false` in config
2. Verify no infinite loops in event processing
3. Check if multiple instances are running: `ps aux | grep huion`
4. Restart the service: `systemctl --user restart huion-keydial-mini-user.service`

### Configuration Changes Not Taking Effect

**Problem**: Config file changes are not being applied.

**Solution**:
1. Restart the service: `systemctl --user restart huion-keydial-mini-user.service`
2. Check config file syntax: `python3 -c "import yaml; yaml.safe_load(open('~/.config/huion-keydial-mini/config.yaml'))"`
3. Verify config file location: `~/.config/huion-keydial-mini/config.yaml`

## Debugging Commands

### Check Service Status
```bash
systemctl --user status huion-keydial-mini-user.service
```

### View Real-time Logs
```bash
journalctl --user -u huion-keydial-mini-user.service -f
```

### Test Device Communication
```bash
python3 -m huion_keydial_mini.event_logger --test
```

### Diagnose HID Issues
```bash
python3 diagnose_hid.py
```

### Check Bluetooth Connectivity
```bash
bluetoothctl show
bluetoothctl devices
```

### Test UInput Device Creation
```bash
python3 -m huion_keydial_mini.create_uinput_device
```

## Getting Help

If you're still experiencing issues:

1. **Check existing issues** on the GitHub repository
2. **Gather logs** using the debugging commands above
3. **Create a new issue** with:
   - Your Linux distribution and version
   - Complete error logs
   - Steps to reproduce the problem
   - Your configuration file (remove sensitive info)

## Reporting Bugs

When reporting bugs, please include:

- **System information**: OS, kernel version, Python version
- **Complete logs**: Full service logs showing the error
- **Device information**: Device model, firmware version if available
- **Configuration**: Your config file (sanitized)
- **Steps to reproduce**: Exact steps that trigger the issue
