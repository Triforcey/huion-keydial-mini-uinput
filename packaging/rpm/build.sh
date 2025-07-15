#!/bin/bash
# Build script for RPM package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Building RPM package for huion-keydial-mini-driver..."
echo "Project root: $PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
    echo "Error: pyproject.toml not found. Are you in the project root?"
    exit 1
fi

# Check if rpmbuild is available
if ! command -v rpmbuild >/dev/null 2>&1; then
    echo "Error: rpmbuild not found. Please install rpm-build package."
    exit 1
fi

# Create RPM build directory structure
RPMBUILD_DIR="$HOME/rpmbuild"
mkdir -p "$RPMBUILD_DIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Create source tarball
cd "$PROJECT_ROOT"
PACKAGE_VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
TARBALL_NAME="huion-keydial-mini-driver-${PACKAGE_VERSION}.tar.gz"

echo "Creating source tarball: $TARBALL_NAME"
git archive --format=tar.gz --prefix="huion-keydial-mini-driver-${PACKAGE_VERSION}/" HEAD > "$RPMBUILD_DIR/SOURCES/$TARBALL_NAME"

# Copy spec file
cp "$SCRIPT_DIR/huion-keydial-mini-driver.spec" "$RPMBUILD_DIR/SPECS/"

# Build the package
echo "Building RPM package..."
cd "$RPMBUILD_DIR"
rpmbuild -ba SPECS/huion-keydial-mini-driver.spec

echo ""
echo "Package built successfully!"
echo "Package files:"
ls -la RPMS/noarch/*.rpm 2>/dev/null || echo "No RPM files found"
ls -la SRPMS/*.src.rpm 2>/dev/null || echo "No SRPM files found"

echo ""
echo "To install the package:"
echo "  sudo rpm -ivh RPMS/noarch/huion-keydial-mini-driver-*.rpm"
echo ""
echo "To install dependencies first:"
echo "  sudo dnf install python3-evdev python3-bleak python3-pyudev python3-click python3-pyyaml python3-dbus-next"
