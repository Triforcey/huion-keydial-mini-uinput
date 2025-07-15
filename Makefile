.PHONY: help install install-dev install-system install-all install-udev install-systemd install-config uninstall uninstall-all clean build test test-cov package-python package-arch package-debian package-rpm package-all uninstall-systemd uninstall-system uninstall-udev uninstall-config

PYTHON := python3
PIP := pip3
VENV_DIR := venv

# Permission constants
SERVICE_PERMS := 644
UDEV_PERMS := 644
SCRIPT_PERMS := 755
CONFIG_PERMS := 644

help:
	@echo "Huion Keydial Mini Driver - Make Commands"
	@echo ""
	@echo "Installation:"
	@echo "  install       Install the package locally"
	@echo "  install-dev   Install in development mode"
	@echo "  install-all   Complete installation (system + services + udev)"
	@echo "  uninstall-all Uninstall everything"
	@echo ""
	@echo "Development:"
	@echo "  build         Build wheel package"
	@echo "  test          Run tests"
	@echo "  test-cov      Run tests with coverage"
	@echo "  clean         Clean build artifacts"
	@echo ""
	@echo "Packaging:"
	@echo "  package-python Build Python wheel (works on all systems)"
	@echo "  package-arch   Build Arch Linux package (Arch/Manjaro only)"
	@echo "  package-debian Build Debian package (Debian/Ubuntu only)"
	@echo "  package-rpm    Build RPM package (Fedora/RHEL/openSUSE only)"
	@echo "  package-all    Build all packages supported on current system"
	@echo ""
	@echo "Configuration:"
	@echo "  Use 'keydialctl' command for runtime configuration"
	@echo "  See CONTRIBUTING.md for developer tools and advanced usage"

install:
	$(PIP) install .

install-dev:
	$(PIP) install -e .
	$(PIP) install -e ".[test]"

install-system: build-system
	$(PYTHON) -m installer --prefix=/usr dist/*.whl

build-system:
	$(PYTHON) -m build

uninstall:
	$(PIP) uninstall -y huion-keydial-mini-driver

install-udev:
	@echo "Installing modprobe blacklist for device conflicts..."
	sudo ./packaging/install-udev.sh



install-config:
	@echo "Installing configuration files with proper permissions..."
	mkdir -p ~/.config/huion-keydial-mini
	install -m $(CONFIG_PERMS) packaging/config.yaml.default ~/.config/huion-keydial-mini/config.yaml
	@echo "Configuration installed with permissions: $(CONFIG_PERMS)"
	@echo "Edit ~/.config/huion-keydial-mini/config.yaml to customize your key bindings"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	$(PYTHON) -m build

test:
	@echo "Running tests with pytest..."
	@if command -v pytest >/dev/null 2>&1; then \
		pytest tests/ -v --tb=short; \
	else \
		echo "pytest not found. Installing test dependencies..."; \
		$(PIP) install -e ".[test]"; \
		pytest tests/ -v --tb=short; \
	fi



test-cov:
	@echo "Running tests with coverage..."
	@if command -v pytest >/dev/null 2>&1; then \
		pytest tests/ -v --cov=src/huion_keydial_mini --cov-report=html --cov-report=term; \
	else \
		echo "pytest not found. Installing test dependencies..."; \
		$(PIP) install -e ".[test]"; \
		pytest tests/ -v --cov=src/huion_keydial_mini --cov-report=html --cov-report=term; \
	fi

package-python:
	@echo "Building Python wheel package..."
	./packaging/build.sh

package-arch:
	@echo "Building Arch Linux package..."
	@if command -v makepkg >/dev/null 2>&1; then \
		./packaging/arch/build.sh; \
	else \
		echo "Error: makepkg not found. This command only works on Arch Linux."; \
		exit 1; \
	fi

package-debian:
	@echo "Building Debian package..."
	@if command -v dpkg-buildpackage >/dev/null 2>&1; then \
		./packaging/debian/build.sh; \
	else \
		echo "Error: dpkg-buildpackage not found. This command only works on Debian/Ubuntu."; \
		echo "Install with: sudo apt-get install dpkg-dev"; \
		exit 1; \
	fi

package-rpm:
	@echo "Building RPM package..."
	@if command -v rpmbuild >/dev/null 2>&1; then \
		./packaging/rpm/build.sh; \
	else \
		echo "Error: rpmbuild not found. This command only works on RPM-based systems."; \
		echo "Install with: sudo dnf install rpm-build  # or sudo yum install rpm-build"; \
		exit 1; \
	fi

package-all:
	@echo "Building all packages supported on current system..."
	@./packaging/build.sh
	@if command -v makepkg >/dev/null 2>&1; then \
		echo "Arch Linux detected - building Arch package..."; \
		./packaging/arch/build.sh; \
	fi
	@if command -v dpkg-buildpackage >/dev/null 2>&1; then \
		echo "Debian/Ubuntu detected - building Debian package..."; \
		./packaging/debian/build.sh; \
	fi
	@if command -v rpmbuild >/dev/null 2>&1; then \
		echo "RPM-based system detected - building RPM package..."; \
		./packaging/rpm/build.sh; \
	fi
	@echo "Package building complete for all supported systems on this host"



install-systemd:
	@echo "Installing systemd services with proper permissions..."
	install -m $(SERVICE_PERMS) packaging/systemd/huion-keydial-mini-user.service /etc/systemd/user/huion-keydial-mini-user.service
	@echo "Reloading systemd daemon..."
	systemctl daemon-reload
	@echo "Systemd services installed with proper permissions:"
	@echo "  - User service: $(SERVICE_PERMS)"

uninstall-systemd:
	rm -f /etc/systemd/user/huion-keydial-mini-user.service
	systemctl daemon-reload

uninstall-system:
	rm -rf /usr/lib/python*/site-packages/huion_keydial_mini*
	rm -rf /usr/lib/python*/site-packages/huion_keydial_mini_driver*
	rm -f /usr/bin/huion-keydial-mini
	rm -f /usr/bin/create-huion-keydial-uinput-device
	rm -f /usr/bin/keydialctl

# Additional installation targets with proper permissions
install-all: install-system install-systemd install-udev
	@echo "Full installation complete with proper permissions set"



uninstall-all: uninstall-system uninstall-systemd uninstall-udev
	@echo "Complete uninstallation finished"
	@echo ""
	@echo "Note: If you want to remove all traces, you may also want to:"
	@echo "  - Remove user from input group: sudo gpasswd -d \$$USER input"
	@echo "  - Remove any remaining log files: journalctl --vacuum-time=1s"

uninstall-udev:
	@echo "Removing udev rules and scripts..."
	@if [ -f /etc/udev/rules.d/99-huion-keydial-mini.rules ]; then \
		sudo rm -f /etc/udev/rules.d/99-huion-keydial-mini.rules; \
		echo "Removed system udev rules"; \
	fi
	@if [ -f /usr/local/bin/unbind-huion.sh ]; then \
		sudo rm -f /usr/local/bin/unbind-huion.sh; \
		echo "Removed unbind script"; \
	fi
	@echo "Reloading udev rules..."
	@if command -v udevadm >/dev/null 2>&1; then \
		sudo udevadm control --reload-rules; \
		sudo udevadm trigger; \
	fi

uninstall-config:
	@echo "Removing configuration files..."
	@if [ -f ~/.config/huion-keydial-mini/config.yaml ]; then \
		rm -f ~/.config/huion-keydial-mini/config.yaml; \
		echo "Removed user configuration"; \
	fi
	@if [ -d ~/.config/huion-keydial-mini ]; then \
		rmdir ~/.config/huion-keydial-mini 2>/dev/null || echo "Config directory not empty, leaving in place"; \
	fi
