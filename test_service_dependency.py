#!/usr/bin/env python3
"""Test script to verify service dependency management."""

import asyncio
import subprocess
import sys
import time

def run_command(cmd, check=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def test_service_dependency():
    """Test that the user service can start the system service."""
    print("Testing service dependency management...")

    # Check if system service is installed
    success, stdout, stderr = run_command("systemctl --system is-enabled huion-keydial-mini-uinput.service", check=False)
    if not success:
        print("❌ System service not found. Please install it first:")
        print("   sudo make install-systemd")
        return False

    # Check if user service is installed
    success, stdout, stderr = run_command("systemctl --user is-enabled huion-keydial-mini.service", check=False)
    if not success:
        print("❌ User service not found. Please install it first:")
        print("   ./packaging/install-user.sh")
        return False

    print("✅ Both services are installed")

    # Stop both services to start fresh
    print("Stopping services...")
    run_command("systemctl --user stop huion-keydial-mini.service", check=False)
    run_command("systemctl --system stop huion-keydial-mini-uinput.service", check=False)
    time.sleep(2)

    # Check initial state
    system_active, _, _ = run_command("systemctl --system is-active --quiet huion-keydial-mini-uinput.service", check=False)
    user_active, _, _ = run_command("systemctl --user is-active --quiet huion-keydial-mini.service", check=False)

    print(f"Initial state - System service: {'active' if system_active else 'inactive'}")
    print(f"Initial state - User service: {'active' if user_active else 'inactive'}")

    # Start user service and see if it starts system service
    print("Starting user service...")
    success, stdout, stderr = run_command("systemctl --user start huion-keydial-mini.service")
    if not success:
        print(f"❌ Failed to start user service: {stderr}")
        return False

    # Wait a moment for services to start
    time.sleep(3)

    # Check final state
    system_active, _, _ = run_command("systemctl --system is-active --quiet huion-keydial-mini-uinput.service", check=False)
    user_active, _, _ = run_command("systemctl --user is-active --quiet huion-keydial-mini.service", check=False)

    print(f"Final state - System service: {'active' if system_active else 'inactive'}")
    print(f"Final state - User service: {'active' if user_active else 'inactive'}")

    if system_active and user_active:
        print("✅ Success! User service successfully started the system service")
        return True
    else:
        print("❌ Failed! User service did not start the system service")
        if not system_active:
            print("   System service is not active")
        if not user_active:
            print("   User service is not active")
        return False

def main():
    """Main test function."""
    print("Huion Keydial Mini Service Dependency Test")
    print("=" * 50)

    success = test_service_dependency()

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
        print("The user service can successfully start the system service when needed.")
    else:
        print("❌ Tests failed!")
        print("Please check the service configuration and polkit rules.")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
