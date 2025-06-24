.PHONY: help install install-dev uninstall clean build test test-simple test-cov lint format check-deps scan run debug package-deb package-rpm package-all config-list config-bind config-unbind config-dial config-reset config-keys debug-parser debug-parser-interactive install-udev diagnose-hid

PYTHON := python3
PIP := pip3
VENV_DIR := venv

help:
	@echo "Huion Keydial Mini Driver - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install       Install the package"
	@echo "  install-dev   Install in development mode with dev dependencies"
	@echo "  uninstall     Uninstall the package"
	@echo "  install-udev  Install modprobe blacklist for device conflicts"
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
	@echo "  scan          Scan for Huion devices"
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
	@echo "  package-all   Build all packages"
	@echo ""
	@echo "Configuration:"
	@echo "  config-list   List current key bindings"
	@echo "  config-bind   Bind a button to a key (use BUTTON=button_1 KEY=KEY_F1)"
	@echo "  config-unbind Unbind a button (use BUTTON=button_1)"
	@echo "  config-dial   Configure dial settings"
	@echo "  config-keys   List available key codes"
	@echo "  config-reset  Reset configuration to defaults"

install:
	$(PIP) install .

install-dev:
	$(PIP) install -e .
	$(PIP) install -e ".[test]"

uninstall:
	$(PIP) uninstall -y huion-keydial-mini-driver

install-udev:
	@echo "Installing modprobe blacklist for device conflicts..."
	sudo ./packaging/install-udev.sh

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

scan:
	$(VENV_DIR)/bin/python -m huion_keydial_mini --scan

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

package-all:
	./packaging/build.sh

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
		echo "Usage: make config-bind BUTTON=button_1 KEY=KEY_F1"; \
		echo "Available buttons: button_1 through button_8"; \
		exit 1; \
	fi
	keydialctl bind $(BUTTON) $(KEY)

config-unbind:
	@if [ -z "$(BUTTON)" ]; then \
		echo "Usage: make config-unbind BUTTON=button_1"; \
		echo "Available buttons: button_1 through button_8"; \
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
