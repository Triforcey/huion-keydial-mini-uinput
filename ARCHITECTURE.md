# Architecture

## Overview

The Huion Keydial Mini driver uses a modular architecture with automatic device detection and runtime configuration management.

## Automatic Connection Detection

The driver uses DBus monitoring to automatically detect when your Huion Keydial Mini connects or disconnects:

```
DBus Monitoring → Device Connection Event → Automatic Attachment → HID Processing → Virtual Input
```

**Key Features:**
- **Start early**: Service can start at login, even before device connection
- **Automatic attachment**: Detects device connections via BlueZ DBus signals
- **No manual intervention**: No need to restart service when connecting/disconnecting
- **Multiple device support**: Can target specific devices or auto-discover any Huion device

## Runtime Keybind Management

The driver uses an in-memory keybind manager with Unix socket control interface:

```
HID Parser → Event → In-Memory Keybind Map → UInput Handler → Virtual Device
```

**Key Features:**
- **In-Memory Mappings**: Config initializes bindings, but they can be modified at runtime
- **Unix Socket Control**: `keydialctl` communicates with the service via Unix socket
- **Advanced Actions**: Support for keyboard combos, mouse actions, and mixed events
- **No Service Restart**: Changes take effect immediately without restarting the service

## User-Level Service

The driver runs as a user-level systemd service, providing:
- **Better Security**: No need to run as root
- **User Isolation**: Each user can have their own service instance
- **Easier Management**: User-specific configuration and logs

## Component Overview

### Core Components

1. **HID Parser** (`src/huion_keydial_mini/hid_parser.py`)
   - Parses raw HID data from the device
   - Converts hardware events to standardized input events
   - Handles both button presses and dial rotations

2. **Keybind Manager** (`src/huion_keydial_mini/keybind_manager.py`)
   - Manages runtime keybind mappings
   - Provides Unix socket interface for configuration
   - Supports keyboard, mouse, and combo actions

3. **UInput Handler** (`src/huion_keydial_mini/uinput_handler.py`)
   - Creates virtual input devices
   - Translates events to Linux input system
   - Supports comprehensive keyboard and mouse events

4. **Bluetooth Watcher** (`src/huion_keydial_mini/bluetooth_watcher.py`)
   - Monitors DBus for device connection events
   - Automatically attaches to devices when connected
   - Handles connection/disconnection gracefully

5. **Device Interface** (`src/huion_keydial_mini/device.py`)
   - Manages Bluetooth GATT connections
   - Handles device communication and data flow
   - Provides connection state management

### Data Flow

```
Device → Bluetooth GATT → HID Parser → Keybind Manager → UInput Handler → Linux Input System
                                                     ↑
                                            Unix Socket Control
                                                     ↓
                                                keydialctl
```

## Security Model

- **User-level service**: No root privileges required
- **Input group membership**: Required for uinput device creation
- **Unix socket**: Local communication only, no network exposure
- **Bluetooth permissions**: Uses user's Bluetooth stack permissions
