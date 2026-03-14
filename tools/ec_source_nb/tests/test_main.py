"""Unit tests for ec_source_nb main module."""

import io
import json
import sys
from unittest.mock import patch

import pytest
from ec_source_nb.main import parse_args, main


class TestParseArgs:
    """Test suite for parse_args function."""

    def test_parse_args_with_valid_args(self):
        """Test parse_args with valid arguments."""
        argv = [
            "--freq", "100.0",
            "--sl", "150.0",
            "--az", "45.0",
            "--el", "10.0"
        ]
        args = parse_args(argv)
        
        assert args.freq == "100.0"
        assert args.sl == "150.0"
        assert args.az == "45.0"
        assert args.el == "10.0"
        assert args.verbose is False

    def test_parse_args_with_verbose_flag(self):
        """Test parse_args with verbose flag."""
        argv = [
            "--freq", "100.0",
            "--sl", "150.0",
            "--az", "45.0",
            "--el", "10.0",
            "--verbose"
        ]
        args = parse_args(argv)
        assert args.verbose is True

    def test_parse_args_with_comma_separated_values(self):
        """Test parse_args with comma-separated values."""
        argv = [
            "--freq", "100.0,200.0,300.0",
            "--sl", "150.0,160.0,170.0",
            "--az", "45.0,90.0,180.0",
            "--el", "10.0,20.0,30.0"
        ]
        args = parse_args(argv)
        
        assert args.freq == "100.0,200.0,300.0"
        assert args.sl == "150.0,160.0,170.0"
        assert args.az == "45.0,90.0,180.0"
        assert args.el == "10.0,20.0,30.0"

    def test_parse_args_requires_freq(self):
        """Test that --freq is required."""
        argv = ["--sl", "150.0", "--az", "45.0", "--el", "10.0"]
        with pytest.raises(SystemExit):
            parse_args(argv)

    def test_parse_args_requires_sl(self):
        """Test that --sl is required."""
        argv = ["--freq", "100.0", "--az", "45.0", "--el", "10.0"]
        with pytest.raises(SystemExit):
            parse_args(argv)

    def test_parse_args_requires_az(self):
        """Test that --az is required."""
        argv = ["--freq", "100.0", "--sl", "150.0", "--el", "10.0"]
        with pytest.raises(SystemExit):
            parse_args(argv)

    def test_parse_args_requires_el(self):
        """Test that --el is required."""
        argv = ["--freq", "100.0", "--sl", "150.0", "--az", "45.0"]
        with pytest.raises(SystemExit):
            parse_args(argv)


class TestMain:
    """Test suite for main function."""

    def test_main_with_single_source(self):
        """Test main() with single source outputs one NDJSON record."""
        argv = [
            "--freq", "100.0",
            "--sl", "150.0",
            "--az", "45.0",
            "--el", "10.0"
        ]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = output.strip().split('\n')
        
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["type"] == "source"
        assert record["freq"] == 100.0
        assert record["sl"] == 150.0
        assert record["az"] == 45.0
        assert record["el"] == 10.0

    def test_main_with_multiple_sources(self):
        """Test main() with multiple sources outputs multiple records."""
        argv = [
            "--freq", "100.0,200.0,300.0",
            "--sl", "150.0,160.0,170.0",
            "--az", "45.0,90.0,180.0",
            "--el", "10.0,20.0,30.0"
        ]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        
        assert len(lines) == 3
        
        records = [json.loads(line) for line in lines]
        
        assert records[0]["freq"] == 100.0
        assert records[0]["sl"] == 150.0
        assert records[1]["freq"] == 200.0
        assert records[1]["sl"] == 160.0
        assert records[2]["freq"] == 300.0
        assert records[2]["sl"] == 170.0

    def test_main_returns_1_on_invalid_freq(self):
        """Test main() returns 1 on invalid frequency."""
        argv = [
            "--freq", "-100.0",
            "--sl", "150.0",
            "--az", "45.0",
            "--el", "10.0"
        ]
        
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            result = main(argv)
        
        assert result == 1
        error_output = mock_stderr.getvalue()
        assert "Error" in error_output

    def test_main_returns_1_on_zero_freq(self):
        """Test main() returns 1 when frequency is zero."""
        argv = [
            "--freq", "0",
            "--sl", "150.0",
            "--az", "45.0",
            "--el", "10.0"
        ]
        
        with patch('sys.stderr', new_callable=io.StringIO):
            result = main(argv)
        
        assert result == 1

    def test_main_returns_1_on_mismatched_list_lengths(self):
        """Test main() returns 1 on mismatched argument list lengths."""
        argv = [
            "--freq", "100.0,200.0",  # 2 items
            "--sl", "150.0,160.0,170.0",  # 3 items
            "--az", "45.0,90.0",
            "--el", "10.0,20.0"
        ]
        
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            result = main(argv)
        
        assert result == 1
        error_output = mock_stderr.getvalue()
        assert "Mismatched" in error_output

    def test_main_with_whitespace_in_values(self):
        """Test main() handles whitespace in comma-separated values."""
        argv = [
            "--freq", "100.0 , 200.0",
            "--sl", "150.0 , 160.0",
            "--az", "45.0 , 90.0",
            "--el", "10.0 , 20.0"
        ]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        assert len(lines) == 2

    def test_main_output_format_is_ndjson(self):
        """Test that main() output follows NDJSON format."""
        argv = [
            "--freq", "100.0,200.0",
            "--sl", "150.0,160.0",
            "--az", "45.0,90.0",
            "--el", "10.0,20.0"
        ]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = output.strip().split('\n')
        
        # Each line should be valid JSON
        for line in lines:
            if line:  # Skip empty lines
                json.loads(line)  # Should not raise

    def test_main_with_negative_elevation(self):
        """Test main() with negative elevation values."""
        argv = [
            "--freq", "100.0",
            "--sl", "150.0",
            "--az", "45.0",
            "--el", "-30.0"
        ]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        record = json.loads(output.strip())
        assert record["el"] == -30.0

    def test_main_with_float_precision(self):
        """Test main() preserves float precision."""
        argv = [
            "--freq", "123.456",
            "--sl", "149.789",
            "--az", "44.123",
            "--el", "9.876"
        ]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        record = json.loads(output.strip())
        assert abs(record["freq"] - 123.456) < 1e-6
        assert abs(record["sl"] - 149.789) < 1e-6
