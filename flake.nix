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

      # Extract the project version from pyproject.toml at evaluation time
      projectVersion =
        let
          pyprojectTOML = builtins.readFile ./pyproject.toml;
          versionMatch = builtins.match ".*[[]project[]].*version = \"([^\"]+)\".*" pyprojectTOML;
        in
        if versionMatch != null then builtins.head versionMatch else "unknown";
    in
    {
      packages = forEachSupportedSystem (
        { pkgs, system }:
        let
          isLinux = system == "x86_64-linux";
        in
        {
          default = self.packages.${system}.huion-keydial-mini-driver;

          huion-keydial-mini-driver = pkgs.python3Packages.buildPythonApplication {
            pname = "huion-keydial-mini-driver";
            version = projectVersion;

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
              # Patch and install udev helper script with correct bash path
              mkdir -p $out/bin
              ${pkgs.gnused}/bin/sed \
                "s|#!/bin/bash|#!${pkgs.bash}/bin/bash|g" \
                ${./packaging/udev/unbind-huion.sh} \
                > $out/bin/unbind-huion.sh
              chmod 755 $out/bin/unbind-huion.sh

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
              install -Dm644 ${pkgs.writeText "99-huion-keydial-mini.preset" ''
                # Enable huion-keydial-mini-user service
                enable huion-keydial-mini-user.service
              ''} $out/lib/systemd/user-preset/99-huion-keydial-mini.preset
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
        // lib.optionalAttrs isLinux {
          # Source tarball — shared input for all distro builds
          source-tarball = pkgs.stdenv.mkDerivation {
            pname = "huion-keydial-mini-source";
            version = projectVersion;

            src = ./.;

            buildPhase = ''
              mkdir -p $out
              tar --transform="s,^,huion-keydial-mini-driver-${projectVersion}/," \
                -czf $out/huion-keydial-mini-driver-${projectVersion}.tar.gz \
                src/ pyproject.toml README.md LICENSE \
                packaging/udev/ packaging/systemd/ packaging/config.yaml.default
            '';

            dontInstall = true;
          };

          # Debian package — built from source using dpkg-deb
          deb-pkg = pkgs.stdenv.mkDerivation {
            pname = "huion-keydial-mini-deb";
            version = projectVersion;

            src = self.packages.${system}.source-tarball;
            dontUnpack = true;

            nativeBuildInputs = with pkgs; [
              dpkg
              python3
              python3Packages.build
              python3Packages.installer
              python3Packages.wheel
              python3Packages.setuptools
              python3Packages.pip
            ];

            buildPhase = ''
                            # Unpack source tarball
                            tar xzf $src/huion-keydial-mini-driver-${projectVersion}.tar.gz
                            cd huion-keydial-mini-driver-${projectVersion}

                            # Build wheel
                            python -m build --wheel --no-isolation

                            # Stage FHS layout
                            STAGING=$TMPDIR/deb-root
                            mkdir -p $STAGING/usr/bin $STAGING/usr/lib/udev/rules.d
                            mkdir -p $STAGING/usr/lib/systemd/user $STAGING/usr/lib/systemd/user-preset
                            mkdir -p $STAGING/etc/huion-keydial-mini $STAGING/usr/local/bin
                            mkdir -p $STAGING/usr/share/doc/huion-keydial-mini-driver
                            mkdir -p $STAGING/usr/share/licenses/huion-keydial-mini-driver

                            # Install Python package to staging using pip with FHS prefix
                            pip install --no-deps --no-compile --prefix=$STAGING/usr dist/*.whl

                            # Fix shebangs: replace Nix Python with system Python
                            for bin in $STAGING/usr/bin/*; do
                              if [ -f "$bin" ]; then
                                sed -i '1s|.*|#!/usr/bin/env python3|' "$bin"
                              fi
                            done

                            # Remove any Nix store paths that leaked into the staging tree
                            rm -rf $STAGING/nix

                            # Install udev rules
                            install -Dm644 packaging/udev/99-huion-keydial-mini.rules \
                              $STAGING/usr/lib/udev/rules.d/99-huion-keydial-mini.rules

                            # Install unbind script
                            install -Dm755 packaging/udev/unbind-huion.sh \
                              $STAGING/usr/local/bin/unbind-huion.sh

                            # Install systemd service
                            install -Dm644 packaging/systemd/huion-keydial-mini-user.service \
                              $STAGING/usr/lib/systemd/user/huion-keydial-mini-user.service

                            # Install default config
                            install -Dm644 packaging/config.yaml.default \
                              $STAGING/etc/huion-keydial-mini/config.yaml

                            # Install docs and license
                            install -Dm644 README.md \
                              $STAGING/usr/share/doc/huion-keydial-mini-driver/README.md
                            install -Dm644 LICENSE \
                              $STAGING/usr/share/licenses/huion-keydial-mini-driver/LICENSE

                            # Install systemd preset
                            echo "enable huion-keydial-mini-user.service" > \
                              $STAGING/usr/lib/systemd/user-preset/99-huion-keydial-mini.preset

                            # DEBIAN control directory
                            mkdir -p $STAGING/DEBIAN
                            cat > $STAGING/DEBIAN/control <<CONTROL
              Package: huion-keydial-mini-driver
              Version: ${projectVersion}-1
              Architecture: all
              Maintainer: JD Flamm <judsonwebdesign@gmail.com>
              Depends: python3 (>= 3.8), python3-bleak, python3-evdev, python3-click, python3-yaml, python3-dbus-next, systemd, bluez
              Provides: huion-keydial-mini
              Conflicts: huion-keydial-mini
              Section: utils
              Priority: optional
              Homepage: https://github.com/Triforcey/huion-keydial-mini-uinput
              Description: User space driver for Huion Keydial Mini bluetooth device
               This package provides a user space driver for the Huion Keydial Mini
               bluetooth device. It intercepts HID over BLE events and creates a
               virtual input device using uinput.
               .
               Features:
                - Bluetooth Low Energy connectivity
                - Customizable key mappings
                - Dial rotation and click support
                - Systemd service integration
              CONTROL

                            # postinst
                            install -Dm755 ${./packaging/debian/postinst} $STAGING/DEBIAN/postinst
                            # prerm
                            install -Dm755 ${./packaging/debian/prerm} $STAGING/DEBIAN/prerm

                            # Build .deb
                            dpkg-deb --build --root-owner-group $STAGING
                            mkdir -p $out
                            cp $TMPDIR/deb-root.deb $out/huion-keydial-mini-driver_${projectVersion}-1_all.deb
            '';

            dontInstall = true;
          };

          # Arch package — built from source using makepkg
          arch-pkg = pkgs.stdenv.mkDerivation {
            pname = "huion-keydial-mini-arch";
            version = projectVersion;

            src = self.packages.${system}.source-tarball;
            dontUnpack = true;

            nativeBuildInputs = with pkgs; [
              pacman
              fakeroot
              libarchive
              zstd
              python3
              python3Packages.build
              python3Packages.installer
              python3Packages.wheel
              python3Packages.setuptools
              python3Packages.pip
            ];

            buildPhase = ''
                            # Set up makepkg build directory
                            mkdir -p build
                            cd build

                            # Place source tarball where PKGBUILD expects it
                            cp $src/huion-keydial-mini-driver-${projectVersion}.tar.gz .

                            # Copy PKGBUILD and inject the project version
                            # from pyproject.toml (the single source of truth)
                            cp ${./packaging/arch/PKGBUILD} ./PKGBUILD
                            sed -i "s|@PKGVER@|${projectVersion}|" PKGBUILD

                            # Run makepkg with Nix-provided config
                            export HOME=$TMPDIR

                            # Create a minimal pacman.conf so makepkg can initialize
                            mkdir -p $TMPDIR/pacman-root $TMPDIR/pacman-db $TMPDIR/pacman-cache
                            cat > $TMPDIR/pacman.conf <<'PACMANCONF'
              [options]
              RootDir = $TMPDIR/pacman-root
              DBPath = $TMPDIR/pacman-db
              CacheDir = $TMPDIR/pacman-cache
              LogFile = /dev/null
              PACMANCONF
                            export PACMAN_CONF=$TMPDIR/pacman.conf

                            PKGEXT=".pkg.tar.zst" makepkg \
                              --config ${pkgs.pacman}/etc/makepkg.conf \
                              --skipinteg \
                              --skippgpcheck \
                              --nodeps \
                              --nocheck \
                              --noconfirm \
                              --holdver
            '';

            installPhase = ''
              mkdir -p $out
              cp *.pkg.tar.zst $out/
            '';
          };

          # RPM package — built from source using rpmbuild
          rpm-pkg = pkgs.stdenv.mkDerivation {
            pname = "huion-keydial-mini-rpm";
            version = projectVersion;

            src = self.packages.${system}.source-tarball;
            dontUnpack = true;

            nativeBuildInputs = with pkgs; [
              rpm
              python3
              python3Packages.setuptools
              python3Packages.wheel
              python3Packages.pip
            ];

            buildPhase = ''
              # Set up rpmbuild tree
              RPMROOT=$TMPDIR/rpmbuild
              mkdir -p $RPMROOT/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

              # Place source tarball
              cp $src/huion-keydial-mini-driver-${projectVersion}.tar.gz $RPMROOT/SOURCES/

              # Place spec file with the project version injected
              # from pyproject.toml (the single source of truth)
              sed "s|@VERSION@|${projectVersion}|" \
                ${./packaging/rpm/huion-keydial-mini-driver.spec} \
                > $RPMROOT/SPECS/huion-keydial-mini-driver.spec

              # Build
              rpmbuild -bb \
                --nodeps \
                --define "_topdir $RPMROOT" \
                --define "_udevrulesdir /usr/lib/udev/rules.d" \
                --define "_userunitdir /usr/lib/systemd/user" \
                --define "_rpmdir $RPMROOT/RPMS" \
                --define "_tmppath $TMPDIR" \
                --define "_var /tmp/rpmvar" \
                --define "_dbpath /tmp/rpmdb" \
                $RPMROOT/SPECS/huion-keydial-mini-driver.spec

              # Collect output
              mkdir -p $out
              find $RPMROOT/RPMS -name '*.rpm' -exec cp {} $out/ \;
            '';

            dontInstall = true;
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
          # Same interpreter the package builds use; tracks nixpkgs updates.
          python = pkgs.python3;
        in
        {
          default = pkgs.mkShellNoCC {
            venvDir = ".venv";

            # Runs before venvShellHook's create-or-activate decision: delete a
            # stale venv when its Python no longer matches nixpkgs so the hook
            # recreates it with the correct interpreter.
            preShellHook = ''
              if [[ -x "$venvDir/bin/python" ]]; then
                venvPythonVersion="$("$venvDir/bin/python" -c 'import platform; print(platform.python_version())')"
                if [[ "$venvPythonVersion" != "${python.version}" ]]; then
                  echo "Python version mismatch: [$venvPythonVersion (venv)] != [${python.version}]"
                  echo "Deleting '$venvDir' so it is recreated for Python ${python.version}"
                  echo "(reinstall dependencies afterwards: pip install -e '.[test]')"
                  rm -rf "$venvDir"
                fi
              fi
            '';

            postShellHook = ''
              export CPATH="${pkgs.linuxHeaders}/include:$CPATH"
              export C_INCLUDE_PATH="${pkgs.linuxHeaders}/include:$C_INCLUDE_PATH"
              export CPLUS_INCLUDE_PATH="${pkgs.linuxHeaders}/include:$CPLUS_INCLUDE_PATH"
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
