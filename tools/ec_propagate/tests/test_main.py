"""Unit tests for ec_propagate main module."""

import io
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from ec_propagate.main import parse_args, main


class TestParseArgs:
    """Test suite for parse_args function."""

    def test_parse_args_with_valid_args(self):
        """Test parse_args with valid arguments."""
        argv = ["--env", "/path/to/ocean.json"]
        args = parse_args(argv)
        
        assert args.env == "/path/to/ocean.json"
        assert args.model == "plane-wave"
        assert args.verbose is False

    def test_parse_args_with_lossless_model(self):
        """Test parse_args with lossless model."""
        argv = ["--env", "/path/to/ocean.json", "--model", "lossless"]
        args = parse_args(argv)

        assert args.env == "/path/to/ocean.json"
        assert args.model == "lossless"

    def test_parse_args_with_verbose_flag(self):
        """Test parse_args with verbose flag."""
        argv = ["--env", "/path/to/ocean.json", "--verbose"]
        args = parse_args(argv)
        
        assert args.verbose is True

    def test_parse_args_defaults(self):
        """Test that --env and --scenario default to None."""
        argv = []
        args = parse_args(argv)
        assert args.env is None
        assert args.scenario is None

    def test_parse_args_with_scenario(self):
        """Test parse_args with --scenario flag."""
        argv = ["--scenario", "/path/to/scenario.json"]
        args = parse_args(argv)
        assert args.scenario == "/path/to/scenario.json"
        assert args.env is None


class TestMain:
    """Test suite for main function."""

    def test_main_loads_ocean_json_and_processes_records(self):
        """Test main() loads ocean.json and processes records."""
        # Create temporary ocean.json
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('{"depth": 100.0}')
            
            input_data = '{"type": "source", "freq": 100.0, "sl": 150.0, "az": 45.0, "el": 10.0}\n'
            argv = ["--env", str(ocean_file)]
            
            with patch('sys.stdin', io.StringIO(input_data)):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = main(argv)
            
            assert result == 0
            output = mock_stdout.getvalue()
            lines = [line for line in output.strip().split('\n') if line]
            
            assert len(lines) == 1
            record = json.loads(lines[0])
            assert record["type"] == "source"
            assert "source_id" in record

    def test_main_returns_1_on_missing_ocean_json(self):
        """Test main() returns 1 on missing ocean.json."""
        input_data = ""
        argv = ["--env", "/nonexistent/ocean.json"]
        
        with patch('sys.stdin', io.StringIO(input_data)):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                result = main(argv)
        
        assert result == 1
        error_output = mock_stderr.getvalue()
        assert "not found" in error_output.lower() or "File not found" in error_output

    def test_main_with_multiple_source_records(self):
        """Test main() with multiple source records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('{"depth": 100.0}')
            
            input_data = (
                '{"type": "source", "freq": 100.0, "sl": 150.0, "az": 45.0, "el": 10.0}\n'
                '{"type": "source", "freq": 200.0, "sl": 160.0, "az": 90.0, "el": 20.0}\n'
            )
            argv = ["--env", str(ocean_file)]
            
            with patch('sys.stdin', io.StringIO(input_data)):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = main(argv)
            
            assert result == 0
            output = mock_stdout.getvalue()
            lines = [line for line in output.strip().split('\n') if line]
            
            assert len(lines) == 2
            records = [json.loads(line) for line in lines]
            
            # Check source_ids are sequential
            assert records[0]["source_id"] == 0
            assert records[1]["source_id"] == 1

    def test_main_with_mixed_record_types(self):
        """Test main() with mixed record types (source and noise)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('{"depth": 100.0}')
            
            input_data = (
                '{"type": "source", "freq": 100.0, "sl": 150.0, "az": 45.0, "el": 10.0}\n'
                '{"type": "noise", "nl": 75.0}\n'
                '{"type": "source", "freq": 200.0, "sl": 160.0, "az": 90.0, "el": 20.0}\n'
            )
            argv = ["--env", str(ocean_file)]
            
            with patch('sys.stdin', io.StringIO(input_data)):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = main(argv)
            
            assert result == 0
            output = mock_stdout.getvalue()
            lines = [line for line in output.strip().split('\n') if line]
            
            assert len(lines) == 3
            records = [json.loads(line) for line in lines]
            
            # Check types and source_ids
            assert records[0]["type"] == "source"
            assert records[0]["source_id"] == 0
            assert records[1]["type"] == "noise"
            assert "source_id" not in records[1]
            assert records[2]["type"] == "source"
            assert records[2]["source_id"] == 1

    def test_main_applies_propagation_loss(self):
        """Test main() applies propagation loss to source records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('{"depth": 100.0}')
            
            input_data = '{"type": "source", "freq": 100.0, "sl": 150.0, "az": 45.0, "el": 10.0}\n'
            argv = ["--env", str(ocean_file)]
            
            with patch('sys.stdin', io.StringIO(input_data)):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = main(argv)
            
            assert result == 0
            output = mock_stdout.getvalue()
            record = json.loads(output.strip())
            
            # Thorp at 100 Hz (0.1 kHz): alpha ≈ 0.001 dB/km
            # sl should be slightly less than 150.0
            assert record["sl"] < 150.0
            assert record["sl"] > 149.9  # Loss is very small at 100 Hz

    def test_main_with_empty_stdin(self):
        """Test main() with empty stdin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('{"depth": 100.0}')
            
            input_data = ""
            argv = ["--env", str(ocean_file)]
            
            with patch('sys.stdin', io.StringIO(input_data)):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = main(argv)
            
            assert result == 0
            output = mock_stdout.getvalue().strip()
            # Should produce no output for empty input
            assert output == ""

    def test_main_with_custom_model(self):
        """Test main() with custom propagation model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('{"depth": 100.0}')
            
            input_data = '{"type": "source", "freq": 100.0, "sl": 150.0, "az": 45.0, "el": 10.0}\n'
            argv = ["--env", str(ocean_file), "--model", "lossless"]
            
            with patch('sys.stdin', io.StringIO(input_data)):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = main(argv)
            
            assert result == 0
            output = mock_stdout.getvalue()
            # Should still process records with the specified model
            record = json.loads(output.strip())
            assert record["type"] == "source"

    def test_main_output_format_is_ndjson(self):
        """Test that main() output is valid NDJSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('{"depth": 100.0}')
            
            input_data = (
                '{"type": "source", "freq": 100.0, "sl": 150.0, "az": 45.0, "el": 10.0}\n'
                '{"type": "source", "freq": 200.0, "sl": 160.0, "az": 90.0, "el": 20.0}\n'
            )
            argv = ["--env", str(ocean_file)]
            
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

    def test_main_returns_1_on_invalid_ocean_json(self):
        """Test main() returns 1 on invalid JSON in ocean config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('invalid json {')
            
            input_data = ""
            argv = ["--env", str(ocean_file)]
            
            with patch('sys.stdin', io.StringIO(input_data)):
                with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                    result = main(argv)
            
            assert result == 1
            error_output = mock_stderr.getvalue()
            assert "Invalid JSON" in error_output

    def test_main_with_scenario(self):
        """Test main() resolves ocean path via --scenario."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('{"depth": 100.0}')

            scenario_file = Path(tmpdir) / "scenario.json"
            scenario_file.write_text(json.dumps({"ocean": "ocean.json"}))

            input_data = '{"type": "source", "freq": 100.0, "sl": 150.0, "az": 45.0, "el": 10.0}\n'
            argv = ["--scenario", str(scenario_file)]

            with patch('sys.stdin', io.StringIO(input_data)):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = main(argv)

            assert result == 0
            record = json.loads(mock_stdout.getvalue().strip())
            assert record["type"] == "source"
            assert "source_id" in record

    def test_main_env_overrides_scenario(self):
        """Test that --env takes precedence over --scenario ocean path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('{"depth": 100.0}')

            # Scenario points to nonexistent file
            scenario_file = Path(tmpdir) / "scenario.json"
            scenario_file.write_text(json.dumps({"ocean": "nonexistent.json"}))

            input_data = '{"type": "source", "freq": 100.0, "sl": 150.0, "az": 45.0, "el": 10.0}\n'
            argv = ["--scenario", str(scenario_file), "--env", str(ocean_file)]

            with patch('sys.stdin', io.StringIO(input_data)):
                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                    result = main(argv)

            assert result == 0

    def test_main_returns_1_when_no_env_and_no_scenario(self):
        """Test main() returns 1 when neither --env nor --scenario is given."""
        input_data = '{"type": "source", "freq": 100.0, "sl": 150.0, "az": 45.0, "el": 10.0}\n'
        argv = []

        with patch('sys.stdin', io.StringIO(input_data)):
            result = main(argv)

        assert result == 1

    def test_main_rejects_invalid_record(self):
        """Test main() returns 1 on record missing required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ocean_file = Path(tmpdir) / "ocean.json"
            ocean_file.write_text('{"depth": 100.0}')

            # source record missing 'az' and 'el'
            input_data = '{"type": "source", "freq": 100.0, "sl": 150.0}\n'
            argv = ["--env", str(ocean_file)]

            with patch('sys.stdin', io.StringIO(input_data)):
                result = main(argv)

            assert result == 1
