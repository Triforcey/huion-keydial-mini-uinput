#!/bin/bash
# Script to unbind Huion Keydial Mini from hid-generic driver

# Get the input event path from udev environment
INPUT_DEVICE="$1"

if [ -z "$INPUT_DEVICE" ]; then
    echo "Usage: $0 <input_device_path>"
    exit 1
fi

# Convert udev path to sysfs path
SYSFS_PATH="/sys$INPUT_DEVICE"

if [ ! -d "$SYSFS_PATH" ]; then
    echo "Device path does not exist: $SYSFS_PATH"
    exit 1
fi

# Find the parent HID device by walking up the device tree
HID_DEVICE=""
CURRENT_PATH="$SYSFS_PATH"

while [ -n "$CURRENT_PATH" ] && [ "$CURRENT_PATH" != "/sys" ]; do
    # Check if this is a HID device with hid-generic driver
    if [ -f "$CURRENT_PATH/uevent" ] && grep -q "DRIVER=hid-generic" "$CURRENT_PATH/uevent" 2>/dev/null; then
        # Extract the kernel device ID from the path
        HID_DEVICE=$(basename "$CURRENT_PATH")
        break
    fi
    # Move up to parent directory
    CURRENT_PATH=$(dirname "$CURRENT_PATH")
done

if [ -n "$HID_DEVICE" ]; then
    echo "Found HID device: $HID_DEVICE"
    echo "Unbinding from hid-generic..."

    # Unbind from hid-generic
    if echo "$HID_DEVICE" > /sys/bus/hid/drivers/hid-generic/unbind 2>/dev/null; then
        echo "Successfully unbound $HID_DEVICE from hid-generic"
        exit 0
    else
        echo "Failed to unbind $HID_DEVICE from hid-generic"
        exit 1
    fi
else
    echo "Could not find HID device for $INPUT_DEVICE"
    echo "Searched path: $SYSFS_PATH"
    exit 1
fi
