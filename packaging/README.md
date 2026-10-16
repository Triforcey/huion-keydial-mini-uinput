# Packaging

This project is packaged **via Nix**, even for users on other distributions. The Nix flake
is the single source of truth: it builds the Nix package, wires up the NixOS module, and
produces distro-native packages (`.pkg.tar.zst`, `.deb`, `.rpm`) that can be built from any
Linux system with Nix installed — you do not need to be running the target distribution.

All artifacts are also built automatically by GitHub Actions on every release tag and
published to the [Releases page](https://github.com/Triforcey/huion-keydial-mini-uinput/releases),
so installing Nix is only necessary if you want to build the packages yourself.

## Flake outputs

| Output | Produces | Used by |
|--------|----------|---------|
| `.#default` / `.#huion-keydial-mini-driver` | Nix package (`/nix/store/...` paths) | Nix users, NixOS module |
| `.#nixosModules.default` | NixOS module (`services.huion-keydial-mini.enable = true;`) | NixOS |
| `.#source-tarball` | Clean source tarball (`huion-keydial-mini-driver-<version>.tar.gz`) | Shared input for all distro builds |
| `.#arch-pkg` | `.pkg.tar.zst` (Arch Linux package) | Arch users |
| `.#deb-pkg` | `.deb` (Debian/Ubuntu package) | Debian/Ubuntu users |
| `.#rpm-pkg` | `.rpm` (Fedora/RHEL/openSUSE package) | Fedora/RHEL users |

Build them with:

```bash
nix build .#arch-pkg        # then: sudo pacman -U result/*.pkg.tar.zst
nix build .#deb-pkg         # then: sudo dpkg -i result/*.deb
nix build .#rpm-pkg         # then: sudo rpm -i result/*.rpm
make nix-build-all          # all three at once
```

All distro outputs are `x86_64-linux` only (this is a hardware driver with no compiled
extensions, but it only makes sense on Linux).

## Design principle: build from source, not from Nix output

Distro packages are **built from source using distro-native tooling** (`makepkg`,
`dpkg-deb`, `rpmbuild`), with the toolchain provided by Nix. They are *not* produced by
un-patching Nix store paths out of the Nix build output. This means:

- Distro packages contain proper FHS paths (`/usr/bin/...`, `/etc/...`) and
  `#!/usr/bin/env python3` shebangs that resolve to the target system's Python.
- Runtime dependencies (`bleak`, `evdev`, ...) come from the target distribution's package
  manager, not from Nix.
- The version is read from `pyproject.toml` at evaluation time — a single source of truth.

## How shared assets are handled

The source files in `packaging/` use FHS paths and are the canonical source for distro
packaging:

| File | Distro builds | Nix build |
|------|---------------|-----------|
| `packaging/udev/99-huion-keydial-mini.rules` | copied as-is (references `/usr/local/bin/unbind-huion.sh`) | `sed`-patched to `$out/bin/unbind-huion.sh` |
| `packaging/udev/unbind-huion.sh` | copied as-is (`#!/bin/bash`) | `sed`-patched to Nix bash |
| `packaging/systemd/huion-keydial-mini-user.service` | copied as-is (references `/usr/bin/huion-keydial-mini`) | `sed`-patched to `$out/bin/...` |
| `packaging/config.yaml.default` | installed to `/etc/huion-keydial-mini/config.yaml` | installed to `$out/etc/...` |
| `packaging/systemd/huion-keydial-mini-user-local.service` | **not installed** by distro packages | not installed |

The `user-local` service belongs to the non-packaged `make install-user-*` path (see the
README's user-level install section) and is deliberately excluded from distro packages,
which are system-level installs.

## What lives in this directory

- `arch/PKGBUILD` — standard `makepkg` definition; expects a source tarball in `$srcdir`
  (AUR-ready). `arch/README.md` documents the Arch-specific bits.
- `debian/control`, `debian/changelog`, `debian/copyright` — kept as metadata reference;
  the actual `DEBIAN/control` is generated at build time in the flake.
- `debian/postinst`, `debian/prerm` — maintainer scripts installed into the `.deb`.
- `rpm/huion-keydial-mini-driver.spec` — RPM spec used by `rpmbuild` in the flake.
- `systemd/`, `udev/`, `config.yaml.default` — shared assets (see table above).
- `install-udev.sh` — manual udev setup for the non-Nix `pip install` fallback; skips
  gracefully on read-only (atomic) filesystems.

Deleted in the Nix migration (replaced by flake outputs): `packaging/build.sh`,
`packaging/{arch,debian,rpm}/build.sh`, `packaging/{arch,debian,rpm}/install-deps.sh`,
`packaging/debian/rules`, `packaging/debian/compat`.

## Runtime dependency names per distribution

These are declared in the `.deb` (`Depends:`) and `.spec` (`Requires:`). If a
distribution renames a package, update the generated control data in `flake.nix`
(`deb-pkg`) and `packaging/rpm/huion-keydial-mini-driver.spec`.

| Upstream (pyproject) | Debian/Ubuntu | Fedora/RHEL | Arch |
|----------------------|---------------|-------------|------|
| bleak | `python3-bleak` | `python3-bleak` | `python-bleak` |
| evdev | `python3-evdev` | `python3-evdev` | `python-evdev` |
| click | `python3-click` | `python3-click` | `python-click` |
| pyyaml | `python3-yaml` | `python3-pyyaml` | `python-yaml` |
| dbus-next | `python3-dbus-next` | `python3-dbus-next` | `python-dbus-next` |
| — | `systemd`, `bluez` | `systemd`, `bluez` | `systemd`, `bluez` |

Note: Arch and some RPM-based distributions may not package `dbus-next`; verify
availability before building for those targets.
