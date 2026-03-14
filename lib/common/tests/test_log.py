"""Tests for setup_logging function."""

import io
import logging
import sys
from typing import Any

import pytest

from lib.common.log import setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    def teardown_method(self) -> None:
        """Clean up logging state after each test."""
        # Remove all handlers from the root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_verbose_false_sets_info_level(self) -> None:
        """Test that verbose=False sets logging level to INFO."""
        setup_logging(verbose=False)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_verbose_true_sets_debug_level(self) -> None:
        """Test that verbose=True sets logging level to DEBUG."""
        setup_logging(verbose=True)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_default_verbose_is_false(self) -> None:
        """Test that default verbose parameter is False."""
        setup_logging()
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_creates_stderr_handler(self) -> None:
        """Test that a stderr StreamHandler is created."""
        setup_logging()
        
        root_logger = logging.getLogger()
        handlers = root_logger.handlers
        
        # Should have at least one handler
        assert len(handlers) > 0
        
        # The handler should be a StreamHandler
        handler = handlers[-1]
        assert isinstance(handler, logging.StreamHandler)

    def test_handler_streams_to_stderr(self) -> None:
        """Test that handler streams to stderr."""
        setup_logging()
        
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream == sys.stderr

    def test_handler_level_matches_root_logger_verbose_false(self) -> None:
        """Test that handler level matches root logger for verbose=False."""
        setup_logging(verbose=False)
        
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        
        assert handler.level == logging.INFO

    def test_handler_level_matches_root_logger_verbose_true(self) -> None:
        """Test that handler level matches root logger for verbose=True."""
        setup_logging(verbose=True)
        
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        
        assert handler.level == logging.DEBUG

    def test_formatter_set_on_handler(self) -> None:
        """Test that a formatter is set on the handler."""
        setup_logging()
        
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        
        assert handler.formatter is not None

    def test_formatter_format_string(self) -> None:
        """Test that formatter uses correct format string."""
        setup_logging()
        
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        formatter = handler.formatter
        
        assert formatter is not None
        # Create a log record and check formatting
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "INFO" in formatted
        assert "test message" in formatted

    def test_info_level_logging_verbose_false(self) -> None:
        """Test that INFO level messages are logged when verbose=False."""
        setup_logging(verbose=False)
        
        # Capture stderr
        captured_stderr = io.StringIO()
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        handler.setStream(captured_stderr)
        
        logger = logging.getLogger("test_module")
        logger.info("Test info message")
        
        output = captured_stderr.getvalue()
        assert "Test info message" in output

    def test_debug_level_not_logged_verbose_false(self) -> None:
        """Test that DEBUG messages are not logged when verbose=False."""
        setup_logging(verbose=False)
        
        # Capture stderr
        captured_stderr = io.StringIO()
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        handler.setStream(captured_stderr)
        
        logger = logging.getLogger("test_module")
        logger.debug("Test debug message")
        
        output = captured_stderr.getvalue()
        assert "Test debug message" not in output

    def test_debug_level_logged_verbose_true(self) -> None:
        """Test that DEBUG messages are logged when verbose=True."""
        setup_logging(verbose=True)
        
        # Capture stderr
        captured_stderr = io.StringIO()
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        handler.setStream(captured_stderr)
        
        logger = logging.getLogger("test_module")
        logger.debug("Test debug message")
        
        output = captured_stderr.getvalue()
        assert "Test debug message" in output

    def test_warning_level_always_logged(self) -> None:
        """Test that WARNING messages are always logged."""
        setup_logging(verbose=False)
        
        # Capture stderr
        captured_stderr = io.StringIO()
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        handler.setStream(captured_stderr)
        
        logger = logging.getLogger("test_module")
        logger.warning("Test warning message")
        
        output = captured_stderr.getvalue()
        assert "Test warning message" in output

    def test_multiple_setup_calls(self) -> None:
        """Test that multiple setup_logging calls work correctly."""
        setup_logging(verbose=False)
        root_logger = logging.getLogger()
        initial_handlers = len(root_logger.handlers)
        
        setup_logging(verbose=True)
        
        # Should have additional handler
        assert len(root_logger.handlers) >= initial_handlers
        # Most recent handler should have DEBUG level
        assert root_logger.handlers[-1].level == logging.DEBUG
        assert root_logger.level == logging.DEBUG

    def test_logging_format_includes_level_and_message(self) -> None:
        """Test that log format includes level name and message."""
        setup_logging(verbose=False)
        
        # Capture stderr
        captured_stderr = io.StringIO()
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        handler.setStream(captured_stderr)
        
        logger = logging.getLogger("test_module")
        logger.info("Test message")
        
        output = captured_stderr.getvalue()
        # Format is "%(levelname)s: %(message)s"
        assert "INFO:" in output
        assert "Test message" in output

    def test_error_level_logged(self) -> None:
        """Test that ERROR level messages are logged."""
        setup_logging(verbose=False)
        
        # Capture stderr
        captured_stderr = io.StringIO()
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        handler.setStream(captured_stderr)
        
        logger = logging.getLogger("test_module")
        logger.error("Test error message")
        
        output = captured_stderr.getvalue()
        assert "ERROR:" in output
        assert "Test error message" in output

    def test_critical_level_logged(self) -> None:
        """Test that CRITICAL level messages are logged."""
        setup_logging(verbose=False)
        
        # Capture stderr
        captured_stderr = io.StringIO()
        root_logger = logging.getLogger()
        handler = root_logger.handlers[-1]
        handler.setStream(captured_stderr)
        
        logger = logging.getLogger("test_module")
        logger.critical("Test critical message")
        
        output = captured_stderr.getvalue()
        assert "CRITICAL:" in output
        assert "Test critical message" in output
