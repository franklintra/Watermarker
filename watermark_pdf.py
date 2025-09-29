#!/usr/bin/env python3
"""
Compatibility wrapper for the old script entry.

Delegates to the package CLI at watermark.cli:main
"""
from watermark.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

