# NixOS Installation Guide

This flake provides a NixOS package and module for the Huion Keydial Mini driver.

## Installation Methods

### Method 1: Using the NixOS Module (Recommended)

Add this to your NixOS configuration (`/etc/nixos/configuration.nix` or your flake):

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    huion-keydial-mini = {
      url = "github:Triforcey/huion-keydial-mini-uinput";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, huion-keydial-mini }: {
    nixosConfigurations.yourHostname = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ./configuration.nix
        huion-keydial-mini.nixosModules.default
        {
          services.huion-keydial-mini.enable = true;
          
          # Add your user to the input group
          users.users.yourUsername.extraGroups = [ "input" ];
        }
      ];
    };
  };
}
```

### Method 2: Direct Package Installation

You can also install just the package without the module:

```nix
{ config, pkgs, ... }:

{
  environment.systemPackages = [
    inputs.huion-keydial-mini.packages.${pkgs.system}.huion-keydial-mini-driver
  ];

  # Manually enable required services
  hardware.bluetooth.enable = true;
  services.udev.packages = [
    inputs.huion-keydial-mini.packages.${pkgs.system}.huion-keydial-mini-driver
  ];

  # Add your user to the input group
  users.users.yourUsername.extraGroups = [ "input" ];
}
```

## Post-Installation Steps

1. **Copy the default configuration:**
   ```bash
   mkdir -p ~/.config/huion-keydial-mini
   cp /etc/huion-keydial-mini/config.yaml ~/.config/huion-keydial-mini/
   ```

2. **Edit your configuration:**
   ```bash
   $EDITOR ~/.config/huion-keydial-mini/config.yaml
   ```

3. **Enable and start the user service:**
   ```bash
   systemctl --user enable --now huion-keydial-mini-user.service
   ```

4. **Check service status:**
   ```bash
   systemctl --user status huion-keydial-mini-user.service
   journalctl --user -u huion-keydial-mini-user.service -f
   ```

## What Gets Installed

The NixOS module automatically installs and configures:

- ✅ Python package with all dependencies (bleak, evdev, click, pyyaml, dbus-next)
- ✅ Command-line tools:
  - `huion-keydial-mini` - Main driver daemon
  - `keydialctl` - Control utility
  - `create-huion-keydial-uinput-device` - Device creation utility
  - `unbind-huion.sh` - Udev helper script
- ✅ Systemd user service (`huion-keydial-mini-user.service`)
- ✅ **Udev rules** (automatically configured with correct Nix store paths)
- ✅ **Bluetooth support** (hardware.bluetooth.enable = true)
- ✅ **Input group** configuration
- ✅ Default configuration file at `/etc/huion-keydial-mini/config.yaml`
- ✅ Documentation and license files

**No manual udev configuration needed!** The module automatically sets up udev rules with the correct Nix store paths when you enable the service.

## Configuration Files

- **System default config:** `/etc/huion-keydial-mini/config.yaml`
- **User config:** `~/.config/huion-keydial-mini/config.yaml`
- **Systemd service:** `/run/current-system/sw/share/systemd/user/huion-keydial-mini-user.service`
- **Udev rules:** `/run/current-system/sw/lib/udev/rules.d/99-huion-keydial-mini.rules`

## Troubleshooting

### Service won't start
```bash
# Check if bluetooth is enabled
systemctl status bluetooth

# Check if you're in the input group
groups | grep input

# If not, add yourself and log out/in
sudo usermod -a -G input $USER
```

### Permission issues
```bash
# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Check logs
```bash
# User service logs
journalctl --user -u huion-keydial-mini-user.service -b

# System logs
journalctl -b | grep huion
```

## Development Shell

For development, the flake also provides a dev shell with Python 3.13 and all necessary dependencies:

```bash
nix develop
```

This sets up a Python virtual environment in `.venv` with all development dependencies.

## Building from Source

```bash
# Build the package
nix build .#huion-keydial-mini-driver

# Check the flake
nix flake check

# Show package info
nix flake show
```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development guidelines.
