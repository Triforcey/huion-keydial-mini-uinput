.PHONY: help install install-dev uninstall clean build test lint format check-deps scan run debug package-deb package-rpm package-all config-list config-bind config-unbind config-dial config-reset config-keys

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
	@echo ""
	@echo "Development:"
	@echo "  clean         Clean build artifacts"
	@echo "  build         Build wheel package"
	@echo "  test          Run tests"
	@echo "  lint          Run linters"
	@echo "  format        Format code"
	@echo "  check-deps    Check for dependency issues"
	@echo ""
	@echo "Running:"
	@echo "  scan          Scan for Huion devices"
	@echo "  run           Run the driver (requires sudo)"
	@echo "  debug         Run with debug logging (requires sudo)"
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
	$(PIP) install pytest black flake8 mypy build

uninstall:
	$(PIP) uninstall -y huion-keydial-mini-driver

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	$(PYTHON) -m build

test:
	pytest tests/ -v

lint:
	flake8 src/
	mypy src/

format:
	black src/

check-deps:
	$(PIP) check

scan:
	huion-keydial-mini --scan

run:
	@echo "Note: This requires sudo privileges"
	sudo huion-keydial-mini

debug:
	@echo "Note: This requires sudo privileges"
	sudo huion-keydial-mini --log-level DEBUG

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
	$(VENV_DIR)/bin/pip install pytest black flake8 mypy build

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
