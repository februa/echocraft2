"""Pytest configuration for ec_pub tests."""

import sys
from pathlib import Path

# Add parent directory and lib to path
root = Path(__file__).parent.parent.parent
lib_path = root / "lib"

if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Also add tools path for tool modules
tools_path = root / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))
