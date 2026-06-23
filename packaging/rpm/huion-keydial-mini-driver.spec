Name:           huion-keydial-mini-driver
Version:        1.2.1
Release:        1%{?dist}
Summary:        User space driver for Huion Keydial Mini bluetooth device

License:        MIT
URL:            https://github.com/Triforcey/huion-keydial-mini-uinput
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-pip

Requires:       python3 >= 3.8
Requires:       python3-bleak
Requires:       python3-evdev
Requires:       python3-click
Requires:       python3-pyyaml
Requires:       python3-dbus-next
Requires:       systemd
Requires:       bluez

Provides:       huion-keydial-mini
Conflicts:      huion-keydial-mini

%description
This package provides a user space driver for the Huion Keydial Mini
bluetooth device. It intercepts HID over BLE events and creates a
virtual input device using uinput.

Features:
  - Bluetooth Low Energy connectivity
  - Customizable key mappings
  - Dial rotation and click support
  - Systemd service integration

%prep
%setup -q

%build
python3 -m pip install --no-build-isolation --no-deps --no-compile \
  --prefix=/usr --root=%{buildroot} --ignore-installed .

%install
# Fix shebangs to use system Python
for bin in %{buildroot}/usr/bin/*; do
  if [ -f "$bin" ]; then
    sed -i '1s|.*|#!/usr/bin/env python3|' "$bin"
  fi
done

# Remove any Nix store paths
rm -rf %{buildroot}/nix

# Install udev rules
install -D -m 644 packaging/udev/99-huion-keydial-mini.rules \
  %{buildroot}/usr/lib/udev/rules.d/99-huion-keydial-mini.rules

# Install unbind script
install -D -m 755 packaging/udev/unbind-huion.sh \
  %{buildroot}/usr/bin/unbind-huion.sh

# Install systemd user service
install -D -m 644 packaging/systemd/huion-keydial-mini-user.service \
  %{buildroot}/usr/lib/systemd/user/huion-keydial-mini-user.service

# Install default config
install -D -m 644 packaging/config.yaml.default \
  %{buildroot}/etc/huion-keydial-mini/config.yaml

# Install systemd user preset
mkdir -p %{buildroot}/usr/lib/systemd/user-preset
echo "enable huion-keydial-mini-user.service" > \
  %{buildroot}/usr/lib/systemd/user-preset/99-huion-keydial-mini.preset

# Install docs and license
install -D -m 644 README.md \
  %{buildroot}/usr/share/doc/%{name}/README.md
install -D -m 644 LICENSE \
  %{buildroot}/usr/share/licenses/%{name}/LICENSE

%post
echo "Huion Keydial Mini Driver installed."
echo "Add your user to the input group: sudo usermod -a -G input $USER"
echo "Reload udev rules: sudo udevadm control --reload-rules && sudo udevadm trigger"
echo "Enable service: systemctl --user enable --now huion-keydial-mini-user.service"

%preun
systemctl --user stop huion-keydial-mini-user.service 2>/dev/null || true
systemctl --user disable huion-keydial-mini-user.service 2>/dev/null || true

%files
/usr/bin/huion-keydial-mini
/usr/bin/keydialctl
/usr/bin/create-huion-keydial-uinput-device
/usr/bin/unbind-huion.sh
/usr/lib/udev/rules.d/99-huion-keydial-mini.rules
/usr/lib/systemd/user/huion-keydial-mini-user.service
/usr/lib/systemd/user-preset/99-huion-keydial-mini.preset
/etc/huion-keydial-mini/config.yaml
/usr/share/doc/%{name}/README.md
/usr/share/licenses/%{name}/LICENSE
/usr/lib/python3.13/site-packages/huion_keydial_mini*/

%changelog
* Wed May 13 2026 JD Flamm <judsonwebdesign@gmail.com> - 1.2.1-1
- Bump to 1.2.1
- Fix compatibility with read-only filesystems
- Handle BlueZ 'Notify acquired' errors gracefully

* Mon Jul 28 2025 JD Flamm <judsonwebdesign@gmail.com> - 1.2.0-1
- Add support for sticky keys

* Mon Jul 28 2025 JD Flamm <judsonwebdesign@gmail.com> - 1.1.0-1
- Add support for button combinations

* Mon Jul 21 2025 JD Flamm <judsonwebdesign@gmail.com> - 1.0.1-1
- Fix Bluetooth device filtering

* Sun Dec 22 2024 JD Flamm <judsonwebdesign@gmail.com> - 1.0.0-1
- Initial release
