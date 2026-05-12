{
  description = "User space driver for Huion Keydial Mini bluetooth device";

  inputs.nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1"; # unstable Nixpkgs

  outputs =
    { self, ... }@inputs:

    let
      inherit (inputs.nixpkgs) lib;

      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];

      forEachSupportedSystem =
        f:
        lib.genAttrs supportedSystems (
          system:
          f {
            inherit system;
            pkgs = import inputs.nixpkgs { inherit system; };
          }
        );

      /*
        Change this value ({major}.{min}) to
        update the Python virtual-environment
        version. When you do this, make sure
        to delete the `.venv` directory to
        have the hook rebuild it for the new
        version, since it won't overwrite an
        existing one. After this, reload the
        development shell to rebuild it.
        You'll see a warning asking you to
        do this when version mismatches are
        present. For safety, removal should
        be a manual step, even if trivial.
      */
      version = "3.13";
    in
    {
      packages = forEachSupportedSystem (
        { pkgs, system }:
        {
          default = self.packages.${system}.huion-keydial-mini-driver;

          huion-keydial-mini-driver = pkgs.python3Packages.buildPythonApplication {
            pname = "huion-keydial-mini-driver";
            version = "1.2.0";

            src = ./.;

            pyproject = true;

            build-system = with pkgs.python3Packages; [
              setuptools
              wheel
            ];

            dependencies = with pkgs.python3Packages; [
              bleak
              evdev
              click
              pyyaml
              dbus-next
            ];

            nativeCheckInputs = with pkgs.python3Packages; [
              pytest
              pytest-asyncio
              pytest-cov
              pytest-mock
            ];

            doCheck = false; # Disable tests for now, can enable if needed

            postInstall = ''
              # Install udev helper script first (needed for path substitution)
              install -Dm755 ${./packaging/udev/unbind-huion.sh} \
                $out/bin/unbind-huion.sh

              # Patch and install systemd user service with correct binary path
              mkdir -p $out/lib/systemd/user
              ${pkgs.gnused}/bin/sed \
                "s|/usr/bin/huion-keydial-mini|$out/bin/huion-keydial-mini|g" \
                ${./packaging/systemd/huion-keydial-mini-user.service} \
                > $out/lib/systemd/user/huion-keydial-mini-user.service

              # Patch and install udev rules with correct script path
              mkdir -p $out/lib/udev/rules.d
              ${pkgs.gnused}/bin/sed \
                "s|/usr/local/bin/unbind-huion.sh|$out/bin/unbind-huion.sh|g" \
                ${./packaging/udev/99-huion-keydial-mini.rules} \
                > $out/lib/udev/rules.d/99-huion-keydial-mini.rules

              # Install default config
              install -Dm644 ${./packaging/config.yaml.default} \
                $out/etc/huion-keydial-mini/config.yaml

              # Install documentation
              install -Dm644 ${./README.md} \
                $out/share/doc/huion-keydial-mini-driver/README.md

              # Install license
              install -Dm644 ${./LICENSE} \
                $out/share/licenses/huion-keydial-mini-driver/LICENSE

              # Install systemd user preset
              install -Dm644 ${
                pkgs.writeText "99-huion-keydial-mini.preset" ''
                  # Enable huion-keydial-mini-user service
                  enable huion-keydial-mini-user.service
                ''
              } $out/lib/systemd/user-preset/99-huion-keydial-mini.preset
            '';

            meta = with lib; {
              description = "User space driver for Huion Keydial Mini bluetooth device";
              homepage = "https://github.com/Triforcey/huion-keydial-mini-uinput";
              license = licenses.mit;
              maintainers = [ ];
              platforms = platforms.linux;
            };
          };
        }
      );

      # NixOS module for easy system integration
      nixosModules.default =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        let
          cfg = config.services.huion-keydial-mini;
        in
        {
          options.services.huion-keydial-mini = {
            enable = lib.mkEnableOption "Huion Keydial Mini driver";

            package = lib.mkOption {
              type = lib.types.package;
              default = self.packages.${pkgs.system}.huion-keydial-mini-driver;
              description = "The huion-keydial-mini-driver package to use";
            };
          };

          config = lib.mkIf cfg.enable {
            environment.systemPackages = [ cfg.package ];

            # Install udev rules (already patched in postInstall)
            services.udev.packages = [ cfg.package ];

            # Install systemd user service (already patched in postInstall)
            systemd.packages = [ cfg.package ];

            # Ensure bluez is enabled
            hardware.bluetooth.enable = true;

            # Add users to input group (users need to be specified in their own config)
            users.groups.input = { };
          };
        };

      devShells = forEachSupportedSystem (
        { pkgs, system }:
        let
          concatMajorMinor =
            v:
            lib.pipe v [
              lib.versions.splitVersion
              (lib.sublist 0 2)
              lib.concatStrings
            ];

          python = pkgs."python${concatMajorMinor version}";
        in
        {
          default = pkgs.mkShellNoCC {
            venvDir = ".venv";

            postShellHook = ''
              export CPATH="${pkgs.linuxHeaders}/include:$CPATH"
              export C_INCLUDE_PATH="${pkgs.linuxHeaders}/include:$C_INCLUDE_PATH"
              export CPLUS_INCLUDE_PATH="${pkgs.linuxHeaders}/include:$CPLUS_INCLUDE_PATH"

              venvVersionWarn() {
              	local venvVersion
              	venvVersion="$("$venvDir/bin/python" -c 'import platform; print(platform.python_version())')"

              	[[ "$venvVersion" == "${python.version}" ]] && return

              	cat <<EOF
              Warning: Python version mismatch: [$venvVersion (venv)] != [${python.version}]
                       Delete '$venvDir' and reload to rebuild for version ${python.version}
              EOF
              }

              venvVersionWarn
            '';

            packages =
              (with python.pkgs; [
                venvShellHook
                pip
              ])
              ++ (with pkgs; [
                linuxHeaders
              ])
              ++ [ self.formatter.${system} ];
          };
        }
      );

      formatter = forEachSupportedSystem ({ pkgs, ... }: pkgs.nixfmt);
    };
}
