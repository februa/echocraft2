"""Logging configuration for ECHOCRAFT tools."""

import logging
import sys


def setup_logging(verbose: bool = False, tool_name: str | None = None) -> None:
    """Configure root logger for ECHOCRAFT tools.

    Sets up stderr logging with appropriate level and format for command-line
    tools. DEBUG level for verbose mode, INFO otherwise.

    When tool_name is provided, log messages are prefixed with the tool name
    for easier identification in pipeline error output:
        ec-propagate: INFO: Processing 3 source records

    Without tool_name, the format remains:
        INFO: Processing 3 source records

    Args:
        verbose: If True, set logging level to DEBUG; otherwise INFO.
        tool_name: Tool name prefix for log messages (e.g., "ec-propagate").
    """
    level = logging.DEBUG if verbose else logging.INFO

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    if tool_name:
        fmt = f"{tool_name}: %(levelname)s: %(message)s"
    else:
        fmt = "%(levelname)s: %(message)s"

    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
