"""Pytest configuration for ECHOCRAFT project."""

import sys
from pathlib import Path

# Add lib and tools directories to sys.path for imports
project_root = Path(__file__).parent
lib_path = project_root / "lib"
tools_path = project_root / "tools"

# Add lib/common to path
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Add all tool directories to path
for tool_dir in tools_path.iterdir():
    if tool_dir.is_dir() and not tool_dir.name.startswith('.'):
        if str(tool_dir) not in sys.path:
            sys.path.insert(0, str(tool_dir))


def pytest_configure(config):
    """Configure pytest with importlib mode to avoid module name conflicts."""
    config.option.importmode = "importlib"
