#!/usr/bin/env python3
"""
Smoke test for watermarker-tool package.
This test verifies basic functionality without requiring actual files.
"""

import sys
import subprocess
from importlib import import_module

def test_import():
    """Test that the watermark module can be imported."""
    try:
        watermark = import_module("watermark")
        print("✓ Successfully imported watermark module")

        # Test that main modules are available
        from watermark import cli, pdf, images, render, utils
        print("✓ All submodules imported successfully")

    except ImportError as e:
        print(f"✗ Failed to import watermark module: {e}")
        return False

    return True

def test_cli_help():
    """Test that the CLI command works and shows help."""
    try:
        result = subprocess.run(
            ["watermark", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✓ CLI help command works")
            # Check for key help text
            if "watermark text" in result.stdout.lower():
                print("✓ CLI help contains expected content")
            else:
                print("✗ CLI help missing expected content")
                return False
        else:
            print(f"✗ CLI help command failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("✗ CLI help command timed out")
        return False
    except FileNotFoundError:
        print("✗ watermark command not found in PATH")
        return False

    return True

def main():
    """Run all smoke tests."""
    print("Running smoke tests for watermarker-tool...")

    tests = [
        test_import,
        test_cli_help,
    ]

    passed = 0
    failed = 0

    for test in tests:
        print(f"\nRunning {test.__name__}...")
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} raised exception: {e}")
            failed += 1

    print(f"\nSmoke test results: {passed} passed, {failed} failed")

    if failed > 0:
        print("Some tests failed!")
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()