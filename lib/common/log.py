"""Logging configuration for ECHOCRAFT tools."""

import logging
import sys


def setup_logging(verbose: bool = False) -> None:
    """Configure root logger for ECHOCRAFT tools.
    
    Sets up stderr logging with appropriate level and format for command-line
    tools. DEBUG level for verbose mode, INFO otherwise.
    
    Args:
        verbose: If True, set logging level to DEBUG; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
