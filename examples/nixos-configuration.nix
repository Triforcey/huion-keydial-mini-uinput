# Example NixOS configuration for Huion Keydial Mini driver
# This can be used as a reference for integrating the driver into your NixOS system

{ config, pkgs, ... }:

{
  # If using flakes, add this to your flake.nix inputs:
  # inputs.huion-keydial-mini.url = "github:Triforcey/huion-keydial-mini-uinput";

  # Import the module (when using flakes)
  # imports = [ huion-keydial-mini.nixosModules.default ];

  # Enable the Huion Keydial Mini service
  services.huion-keydial-mini = {
    enable = true;
    # Optionally specify a custom package
    # package = inputs.huion-keydial-mini.packages.${pkgs.system}.huion-keydial-mini-driver;
  };

  # Add your user to the input group (required for device access)
  users.users.yourUsername = {
    extraGroups = [ "input" ];
  };

  # The module automatically enables:
  # - hardware.bluetooth.enable = true;
  # - Adds udev rules
  # - Installs systemd user service
  # - Creates input group

  # Optional: Install additional tools for debugging
  environment.systemPackages = with pkgs; [
    bluez
    bluez-tools
  ];
}
