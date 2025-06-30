# Arch Linux Packaging

This directory contains the files needed to build an Arch Linux package for the Huion Keydial Mini driver.

## Files

- `PKGBUILD` - The main package build script
- `build.sh` - Helper script to build the package
- `install-deps.sh` - Script to install dependencies
- `README.md` - This file

## Building the Package

### Prerequisites

Make sure you have the base-devel group installed:
```bash
sudo pacman -S --needed base-devel
```

### Quick Build

Use the provided build script:
```bash
./packaging/arch/build.sh
```

### Manual Build

1. Create a build directory:
```bash
mkdir -p /tmp/huion-build
cd /tmp/huion-build
```

2. Copy the PKGBUILD:
```bash
cp /path/to/project/packaging/arch/PKGBUILD .
```

3. Build the package:
```bash
makepkg --syncdeps --noconfirm
```

## Installing Dependencies

The package will automatically install required dependencies, but you can install them manually first:

```bash
sudo pacman -S --needed \
    python-evdev \
    python-bleak \
    python-click \
    python-pyyaml \
    python-dbus-next \
    systemd \
    bluez
```

## Installing the Package

After building, install the package:
```bash
sudo pacman -U *.pkg.tar.zst
```

## Post-Installation Setup

After installing the package, you need to:

1. Add your user to the input group:
```bash
sudo usermod -a -G input $USER
```

2. Copy the default configuration:
```bash
mkdir -p ~/.config/huion-keydial-mini
cp /etc/huion-keydial-mini/config.yaml ~/.config/huion-keydial-mini/
```

3. Edit your configuration:
```bash
nano ~/.config/huion-keydial-mini/config.yaml
```

4. Reboot or log out and back in for group changes to take effect

5. Start the user service:
```bash
systemctl --user enable --now huion-keydial-mini-user.service
```

## Package Information

- **Package Name**: `huion-keydial-mini-driver`
- **Version**: 0.1.0
- **Architecture**: Any (Python package)
- **License**: MIT

## Troubleshooting

### Build Issues

If you encounter build issues:

1. Make sure you have the latest base-devel group:
```bash
sudo pacman -Syu base-devel
```

2. Clean the build directory:
```bash
rm -rf /tmp/huion-build
```

3. Try building again with verbose output:
```bash
makepkg --syncdeps --noconfirm --log
```

### Installation Issues

If the package fails to install:

1. Check for dependency conflicts:
```bash
pacman -Qi huion-keydial-mini-driver
```

2. Check the package contents:
```bash
tar -tvf *.pkg.tar.zst
```

## Contributing

To update the package:

1. Modify the `PKGBUILD` file
2. Update the version number if needed
3. Test the build process
4. Submit a pull request

## License

This packaging is licensed under the same MIT license as the main project.
