.PHONY: help install install-dev install-system install-all install-udev install-udev-system install-systemd install-config uninstall clean build test test-simple test-cov lint format check-deps scan run debug package-deb package-rpm package-arch package-all config-list config-bind config-unbind config-dial config-reset config-keys debug-parser debug-parser-interactive install-udev diagnose-hid install-systemd uninstall-systemd uninstall-system uninstall-udev uninstall-config check-permissions fix-permissions uninstall-all

PYTHON := python3
PIP := pip3
VENV_DIR := venv

# Permission constants
SERVICE_PERMS := 644
UDEV_PERMS := 644
SCRIPT_PERMS := 755
CONFIG_PERMS := 644

help:
	@echo "Huion Keydial Mini Driver - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install       Install the package"
	@echo "  install-dev   Install in development mode with dev dependencies"
	@echo "  install-system Install system-wide package"
	@echo "  install-all   Install system package, systemd services, and udev rules"
	@echo "  install-udev  Install modprobe blacklist for device conflicts"
	@echo "  install-udev-system Install system udev rules and unbind script"
	@echo "  install-systemd Install systemd services"
	@echo "  install-config Install configuration files"
	@echo "  uninstall     Uninstall the package"
	@echo "  uninstall-system Uninstall system-wide package"
	@echo "  uninstall-systemd Uninstall systemd services"
	@echo "  uninstall-udev Uninstall udev rules and scripts"
	@echo "  uninstall-config Uninstall configuration files"
	@echo "  uninstall-all Uninstall everything (system, services, udev, config)"
	@echo ""
	@echo "Permission Management:"
	@echo "  check-permissions Check permissions on installed files"
	@echo "  fix-permissions  Fix permissions on installed files"
	@echo ""
	@echo "Development:"
	@echo "  clean         Clean build artifacts"
	@echo "  build         Build wheel package"
	@echo "  test          Run tests with pytest"
	@echo "  test-simple   Run simple tests without pytest"
	@echo "  test-cov      Run tests with coverage"
	@echo "  lint          Run linters"
	@echo "  format        Format code"
	@echo "  check-deps    Check for dependency issues"
	@echo ""
	@echo "Running:"
	@echo "  run           Run the driver (requires sudo)"
	@echo "  debug         Run with debug logging (requires sudo)"
	@echo "  event-logger  Run event logger to see parsed events"
	@echo "  diagnose-hid  Run HID diagnostic tool to capture raw events"
	@echo ""
	@echo "Debugging:"
	@echo "  debug-parser  Test HID parser with sample data"
	@echo "  debug-parser-interactive  Interactive HID parser test"
	@echo ""
	@echo "Packaging:"
	@echo "  package-deb   Build DEB package"
	@echo "  package-rpm   Build RPM package"
	@echo "  package-arch  Build Arch Linux package"
	@echo "  package-all   Build all packages"
	@echo ""
	@echo "Configuration:"
	@echo "  config-list   List current key bindings"
	@echo "  config-bind   Bind a button to a key (use BUTTON=BUTTON_1 KEY=KEY_F1)"
	@echo "  config-unbind Unbind a button (use BUTTON=BUTTON_1)"
	@echo "  config-dial   Configure dial settings"
	@echo "  config-keys   List available key codes"
	@echo "  config-reset  Reset configuration to defaults"

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

install-udev-system:
	@echo "Installing system udev rules with proper permissions..."
	sudo install -m $(UDEV_PERMS) packaging/udev/99-huion-keydial-mini.rules /etc/udev/rules.d/
	sudo install -m $(SCRIPT_PERMS) packaging/udev/unbind-huion.sh /usr/local/bin/
	@echo "Reloading udev rules..."
	sudo udevadm control --reload-rules
	sudo udevadm trigger
	@echo "System udev rules installed with proper permissions:"
	@echo "  - Udev rules: $(UDEV_PERMS)"
	@echo "  - Unbind script: $(SCRIPT_PERMS)"

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

test-simple:
	@echo "Running simple tests without pytest..."
	$(PYTHON) tests/run_tests.py

test-cov:
	@echo "Running tests with coverage..."
	@if command -v pytest >/dev/null 2>&1; then \
		pytest tests/ -v --cov=src/huion_keydial_mini --cov-report=html --cov-report=term; \
	else \
		echo "pytest not found. Installing test dependencies..."; \
		$(PIP) install -e ".[test]"; \
		pytest tests/ -v --cov=src/huion_keydial_mini --cov-report=html --cov-report=term; \
	fi

lint:
	flake8 src/
	mypy src/

format:
	black src/

check-deps:
	$(PIP) check

run:
	@echo "Note: This requires sudo privileges"
	@echo "Running with virtual environment Python..."
	sudo $(VENV_DIR)/bin/python -m huion_keydial_mini

debug:
	@echo "Note: This requires sudo privileges"
	@echo "Running with virtual environment Python and debug logging..."
	sudo $(VENV_DIR)/bin/python -m huion_keydial_mini --log-level DEBUG

event-logger:
	sudo $(VENV_DIR)/bin/python -m huion_keydial_mini.event_logger

diagnose-hid:
	$(VENV_DIR)/bin/python diagnose_hid.py $(ARGS)

debug-parser:
	$(PYTHON) src/huion_keydial_mini/debug_parser.py

debug-parser-interactive:
	$(PYTHON) src/huion_keydial_mini/debug_parser.py --interactive

package-deb:
	./packaging/build.sh

package-rpm:
	./packaging/build.sh

package-arch:
	./packaging/arch/build.sh

package-all:
	./packaging/build.sh
	./packaging/arch/build.sh

# Virtual environment management
venv:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -e .

venv-dev: venv
	$(VENV_DIR)/bin/pip install -e ".[test]"

activate:
	@echo "Run: source $(VENV_DIR)/bin/activate"

# Configuration management
config-list:
	keydialctl list-bindings

config-bind:
	@if [ -z "$(BUTTON)" ] || [ -z "$(KEY)" ]; then \
		echo "Usage: make config-bind BUTTON=BUTTON_1 KEY=KEY_F1"; \
		echo "Available buttons: BUTTON_1 through BUTTON_8"; \
		exit 1; \
	fi
	keydialctl bind $(BUTTON) $(KEY)

config-unbind:
	@if [ -z "$(BUTTON)" ]; then \
		echo "Usage: make config-unbind BUTTON=BUTTON_1"; \
		echo "Available buttons: BUTTON_1 through BUTTON_8"; \
		exit 1; \
	fi
	keydialctl unbind $(BUTTON)

config-dial:
	@echo "Configure dial settings interactively:"
	@echo "Available options: --clockwise, --counterclockwise, --click, --sensitivity"
	@echo "Example: keydialctl dial --clockwise KEY_VOLUMEUP --counterclockwise KEY_VOLUMEDOWN"
	keydialctl dial

config-reset:
	keydialctl reset

config-keys:
	keydialctl list-keys

install-systemd:
	@echo "Installing systemd services with proper permissions..."
	install -m $(SERVICE_PERMS) packaging/systemd/huion-keydial-mini-uinput.service /etc/systemd/system/huion-keydial-mini-uinput.service
	install -m $(SERVICE_PERMS) packaging/systemd/huion-keydial-mini-user.service /etc/systemd/user/huion-keydial-mini-user.service
	@echo "Reloading systemd daemon..."
	systemctl daemon-reload
	@echo "Systemd services installed with proper permissions:"
	@echo "  - System service: $(SERVICE_PERMS)"
	@echo "  - User service: $(SERVICE_PERMS)"

uninstall-systemd:
	rm -f /etc/systemd/system/huion-keydial-mini-uinput.service
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

# Permission verification targets
check-permissions:
	@echo "Checking installed file permissions..."
	@echo "Systemd services:"
	@ls -la /etc/systemd/system/huion-keydial-mini-uinput.service 2>/dev/null || echo "  System service not installed"
	@ls -la /etc/systemd/user/huion-keydial-mini-user.service 2>/dev/null || echo "  User service not installed"
	@echo "Udev rules:"
	@ls -la /etc/udev/rules.d/99-huion-keydial-mini.rules 2>/dev/null || echo "  Udev rules not installed"
	@echo "Scripts:"
	@ls -la /usr/local/bin/unbind-huion.sh 2>/dev/null || echo "  Unbind script not installed"
	@echo "Configuration:"
	@ls -la ~/.config/huion-keydial-mini/config.yaml 2>/dev/null || echo "  Configuration not installed"

fix-permissions:
	@echo "Fixing permissions on installed files..."
	@if [ -f /etc/systemd/system/huion-keydial-mini-uinput.service ]; then \
		sudo chmod $(SERVICE_PERMS) /etc/systemd/system/huion-keydial-mini-uinput.service; \
		echo "Fixed system service permissions"; \
	fi
	@if [ -f /etc/systemd/user/huion-keydial-mini-user.service ]; then \
		chmod $(SERVICE_PERMS) /etc/systemd/user/huion-keydial-mini-user.service; \
		echo "Fixed user service permissions"; \
	fi
	@if [ -f /etc/udev/rules.d/99-huion-keydial-mini.rules ]; then \
		sudo chmod $(UDEV_PERMS) /etc/udev/rules.d/99-huion-keydial-mini.rules; \
		echo "Fixed system udev rules permissions"; \
	fi
	@if [ -f /usr/local/bin/unbind-huion.sh ]; then \
		sudo chmod $(SCRIPT_PERMS) /usr/local/bin/unbind-huion.sh; \
		echo "Fixed unbind script permissions"; \
	fi
	@if [ -f ~/.config/huion-keydial-mini/config.yaml ]; then \
		chmod $(CONFIG_PERMS) ~/.config/huion-keydial-mini/config.yaml; \
		echo "Fixed configuration permissions"; \
	fi
	@echo "Permission fix complete"

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
