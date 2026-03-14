"""Unit tests for ec_noise main module."""

import io
import json
from unittest.mock import patch

import pytest
from ec_noise.main import parse_args, main


class TestParseArgs:
    """Test suite for parse_args function."""

    def test_parse_args_with_valid_args(self):
        """Test parse_args with valid arguments."""
        argv = ["--nl", "75.0"]
        args = parse_args(argv)
        
        assert args.nl == 75.0
        assert args.verbose is False

    def test_parse_args_with_verbose_flag(self):
        """Test parse_args with verbose flag."""
        argv = ["--nl", "75.0", "--verbose"]
        args = parse_args(argv)
        
        assert args.nl == 75.0
        assert args.verbose is True

    def test_parse_args_requires_nl(self):
        """Test that --nl is required."""
        argv = []
        with pytest.raises(SystemExit):
            parse_args(argv)

    def test_parse_args_with_negative_nl(self):
        """Test parse_args with negative noise level."""
        argv = ["--nl", "-20.0"]
        args = parse_args(argv)
        assert args.nl == -20.0

    def test_parse_args_with_zero_nl(self):
        """Test parse_args with zero noise level."""
        argv = ["--nl", "0.0"]
        args = parse_args(argv)
        assert args.nl == 0.0


class TestMain:
    """Test suite for main function."""

    def test_main_reads_stdin_and_passes_through(self):
        """Test main() reads stdin NDJSON and passes through unchanged."""
        input_data = '{"type": "source", "freq": 100.0}\n'
        argv = ["--nl", "75.0"]
        
        with patch('sys.stdin', io.StringIO(input_data)):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        
        assert len(lines) == 2  # Source record + noise record
        assert json.loads(lines[0]) == {"type": "source", "freq": 100.0}

    def test_main_appends_noise_record_at_end(self):
        """Test main() appends noise record at the end."""
        input_data = '{"type": "source", "freq": 100.0}\n'
        argv = ["--nl", "75.0"]
        
        with patch('sys.stdin', io.StringIO(input_data)):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        
        # Last record should be the noise record
        last_record = json.loads(lines[-1])
        assert last_record["type"] == "noise"
        assert last_record["nl"] == 75.0

    def test_main_with_empty_stdin(self):
        """Test main() with empty stdin still outputs noise record."""
        input_data = ""
        argv = ["--nl", "75.0"]
        
        with patch('sys.stdin', io.StringIO(input_data)):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        
        # Should have exactly one noise record
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["type"] == "noise"
        assert record["nl"] == 75.0

    def test_main_returns_1_on_invalid_nl_inf(self):
        """Test main() returns 1 on invalid nl (inf)."""
        input_data = ""
        argv = ["--nl", "inf"]
        
        with patch('sys.stdin', io.StringIO(input_data)):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                result = main(argv)
        
        assert result == 1
        error_output = mock_stderr.getvalue()
        assert "Error" in error_output

    def test_main_returns_1_on_invalid_nl_nan(self):
        """Test main() returns 1 on invalid nl (nan)."""
        input_data = ""
        argv = ["--nl", "nan"]
        
        with patch('sys.stdin', io.StringIO(input_data)):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                result = main(argv)
        
        assert result == 1
        error_output = mock_stderr.getvalue()
        assert "Error" in error_output

    def test_main_with_multiple_input_records(self):
        """Test main() with multiple input records."""
        input_data = (
            '{"type": "source", "freq": 100.0}\n'
            '{"type": "source", "freq": 200.0}\n'
        )
        argv = ["--nl", "75.0"]
        
        with patch('sys.stdin', io.StringIO(input_data)):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        
        assert len(lines) == 3  # 2 source records + 1 noise record
        
        # Check order: first two should be sources, last should be noise
        records = [json.loads(line) for line in lines]
        assert records[0]["type"] == "source"
        assert records[1]["type"] == "source"
        assert records[2]["type"] == "noise"

    def test_main_preserves_input_record_order(self):
        """Test main() preserves order of input records."""
        input_data = (
            '{"type": "source", "freq": 100.0}\n'
            '{"type": "source", "freq": 200.0}\n'
            '{"type": "source", "freq": 300.0}\n'
        )
        argv = ["--nl", "80.0"]
        
        with patch('sys.stdin', io.StringIO(input_data)):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        records = [json.loads(line) for line in lines]
        
        # Check frequencies are in order
        assert records[0]["freq"] == 100.0
        assert records[1]["freq"] == 200.0
        assert records[2]["freq"] == 300.0

    def test_main_with_negative_noise_level(self):
        """Test main() with negative noise level."""
        input_data = '{"type": "source", "freq": 100.0}\n'
        argv = ["--nl", "-20.0"]
        
        with patch('sys.stdin', io.StringIO(input_data)):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        last_record = json.loads(lines[-1])
        
        assert last_record["type"] == "noise"
        assert last_record["nl"] == -20.0

    def test_main_output_format_is_ndjson(self):
        """Test that main() output is valid NDJSON."""
        input_data = (
            '{"type": "source", "freq": 100.0}\n'
            '{"type": "source", "freq": 200.0}\n'
        )
        argv = ["--nl", "75.0"]
        
        with patch('sys.stdin', io.StringIO(input_data)):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                result = main(argv)
        
        assert result == 0
        output = mock_stdout.getvalue()
        lines = output.strip().split('\n')
        
        # Each line should be valid JSON
        for line in lines:
            if line:  # Skip empty lines
                json.loads(line)  # Should not raise
