#!/usr/bin/env python3
"""Test script to verify user service functionality."""

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

def test_user_service():
    """Test that the user service can start and stop properly."""
    print("Testing user service functionality...")

    # Check if user service is installed
    success, stdout, stderr = run_command("systemctl --user is-enabled huion-keydial-mini-user.service", check=False)
    if not success:
        print("❌ User service not found. Please install it first:")
        print("   sudo make install-systemd")
        return False

    print("✅ User service is installed")

    # Stop service to start fresh
    print("Stopping user service...")
    run_command("systemctl --user stop huion-keydial-mini-user.service", check=False)
    time.sleep(2)

    # Check initial state
    user_active, _, _ = run_command("systemctl --user is-active --quiet huion-keydial-mini-user.service", check=False)
    print(f"Initial state - User service: {'active' if user_active else 'inactive'}")

    # Start user service
    print("Starting user service...")
    success, stdout, stderr = run_command("systemctl --user start huion-keydial-mini-user.service")
    if not success:
        print(f"❌ Failed to start user service: {stderr}")
        return False

    # Wait a moment for service to start
    time.sleep(3)

    # Check final state
    user_active, _, _ = run_command("systemctl --user is-active --quiet huion-keydial-mini-user.service", check=False)
    print(f"Final state - User service: {'active' if user_active else 'inactive'}")

    if user_active:
        print("✅ Success! User service started successfully")
        return True
    else:
        print("❌ Failed! User service did not start")
        return False

def main():
    """Main test function."""
    print("Huion Keydial Mini User Service Test")
    print("=" * 50)

    success = test_user_service()

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
        print("The user service is working correctly.")
    else:
        print("❌ Tests failed!")
        print("Please check the service configuration.")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
