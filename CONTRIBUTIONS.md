# Contributors

Thank you to everyone who has contributed to the Huion Keydial Mini driver!

## Contributors

- **Corey Schram** ([@cschram](https://github.com/cschram)) — Atomic/read-only
  filesystem installation support (user-level install targets, read-only-safe udev
  installer, user-local systemd service) and the Bluetooth device detection fixes
  (target MAC format fix, startup attach for already-connected devices, D-Bus
  object-path resolution for BleakClient) in [PR #10](https://github.com/Triforcey/huion-keydial-mini-uinput/pull/10).
  Per his own disclosure, this work was completed with significant help from MiniMax.

- **JD Flamm** ([@Triforcey](https://github.com/Triforcey)) — Project creator and
  maintainer: original driver, HID parsing, keybind system, uinput integration,
  Nix packaging and distro packaging pipeline.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get involved. Your name belongs
on this list too.
