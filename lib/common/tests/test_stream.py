"""Tests for StreamConfig."""

import json
import tempfile
from pathlib import Path

import pytest

from lib.common.stream import StreamConfig


class TestStreamConfigConstruction:
    """Tests for StreamConfig construction and validation."""

    def test_valid_construction(self) -> None:
        """Test valid StreamConfig construction."""
        config = StreamConfig(sample_rate=48000, rate=100)
        
        assert config.sample_rate == 48000
        assert config.rate == 100
        assert config.format == "float32"

    def test_valid_construction_with_format(self) -> None:
        """Test valid StreamConfig construction with explicit format."""
        config = StreamConfig(sample_rate=48000, rate=100, format="float32")
        
        assert config.sample_rate == 48000
        assert config.rate == 100
        assert config.format == "float32"

    def test_block_size_property(self) -> None:
        """Test that block_size property is computed correctly."""
        config = StreamConfig(sample_rate=48000, rate=100)
        
        assert config.block_size == 480

    def test_block_size_various_rates(self) -> None:
        """Test block_size calculation with various rates."""
        test_cases = [
            (48000, 100, 480),
            (16000, 50, 320),
            (44100, 441, 100),
            (8000, 8, 1000),
        ]
        
        for sample_rate, rate, expected_block_size in test_cases:
            config = StreamConfig(sample_rate=sample_rate, rate=rate)
            assert config.block_size == expected_block_size

    def test_frozen_dataclass(self) -> None:
        """Test that StreamConfig is immutable (frozen)."""
        config = StreamConfig(sample_rate=48000, rate=100)
        
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            config.sample_rate = 16000  # type: ignore


class TestStreamConfigValidation:
    """Tests for StreamConfig validation."""

    def test_sample_rate_positive(self) -> None:
        """Test that sample_rate must be positive."""
        with pytest.raises(ValueError, match="sample_rate must be positive"):
            StreamConfig(sample_rate=0, rate=100)

    def test_sample_rate_negative(self) -> None:
        """Test that sample_rate cannot be negative."""
        with pytest.raises(ValueError, match="sample_rate must be positive"):
            StreamConfig(sample_rate=-48000, rate=100)

    def test_rate_positive(self) -> None:
        """Test that rate must be positive."""
        with pytest.raises(ValueError, match="rate must be positive"):
            StreamConfig(sample_rate=48000, rate=0)

    def test_rate_negative(self) -> None:
        """Test that rate cannot be negative."""
        with pytest.raises(ValueError, match="rate must be positive"):
            StreamConfig(sample_rate=48000, rate=-100)

    def test_sample_rate_divisible_by_rate(self) -> None:
        """Test that sample_rate must be divisible by rate."""
        with pytest.raises(ValueError, match="must be divisible by"):
            StreamConfig(sample_rate=48001, rate=100)

    def test_sample_rate_not_divisible_error_message(self) -> None:
        """Test error message for indivisible rates."""
        with pytest.raises(ValueError) as exc_info:
            StreamConfig(sample_rate=48001, rate=100)
        
        error_msg = str(exc_info.value)
        assert "48001" in error_msg
        assert "100" in error_msg

    def test_format_must_be_float32(self) -> None:
        """Test that only 'float32' format is supported."""
        with pytest.raises(ValueError, match="Unsupported format"):
            StreamConfig(sample_rate=48000, rate=100, format="float64")

    def test_format_int32_not_supported(self) -> None:
        """Test that int32 format is not supported."""
        with pytest.raises(ValueError, match="Unsupported format"):
            StreamConfig(sample_rate=48000, rate=100, format="int32")

    def test_format_invalid_string_not_supported(self) -> None:
        """Test that arbitrary format strings are not supported."""
        with pytest.raises(ValueError, match="Unsupported format"):
            StreamConfig(sample_rate=48000, rate=100, format="invalid")


class TestStreamConfigFromFile:
    """Tests for StreamConfig.from_file() class method."""

    def test_from_file_valid_json(self) -> None:
        """Test loading StreamConfig from valid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "sample_rate": 48000,
                "rate": 100,
                "format": "float32"
            }, f)
            temp_path = f.name
        
        try:
            config = StreamConfig.from_file(temp_path)
            
            assert config.sample_rate == 48000
            assert config.rate == 100
            assert config.format == "float32"
        finally:
            Path(temp_path).unlink()

    def test_from_file_without_explicit_format(self) -> None:
        """Test loading StreamConfig from JSON without explicit format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "sample_rate": 16000,
                "rate": 50
            }, f)
            temp_path = f.name
        
        try:
            config = StreamConfig.from_file(temp_path)
            
            assert config.sample_rate == 16000
            assert config.rate == 50
            assert config.format == "float32"  # Default value
        finally:
            Path(temp_path).unlink()

    def test_from_file_not_found(self) -> None:
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            StreamConfig.from_file("/nonexistent/path/stream.json")

    def test_from_file_invalid_json(self) -> None:
        """Test that JSONDecodeError is raised for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{invalid json}")
            temp_path = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                StreamConfig.from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_from_file_validation_failure(self) -> None:
        """Test that validation errors are raised for invalid config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "sample_rate": 48000,
                "rate": 101  # Not divisible
            }, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="must be divisible by"):
                StreamConfig.from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_from_file_missing_required_field(self) -> None:
        """Test that TypeError is raised for missing required fields."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "sample_rate": 48000
                # Missing 'rate' field
            }, f)
            temp_path = f.name
        
        try:
            with pytest.raises(TypeError):
                StreamConfig.from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_from_file_empty_json_object(self) -> None:
        """Test that TypeError is raised for empty JSON object."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({}, f)
            temp_path = f.name
        
        try:
            with pytest.raises(TypeError):
                StreamConfig.from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_from_file_various_valid_configs(self) -> None:
        """Test loading various valid StreamConfig combinations."""
        test_cases = [
            {"sample_rate": 48000, "rate": 100},
            {"sample_rate": 16000, "rate": 50},
            {"sample_rate": 44100, "rate": 441},
            {"sample_rate": 8000, "rate": 8},
        ]
        
        for test_data in test_cases:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(test_data, f)
                temp_path = f.name
            
            try:
                config = StreamConfig.from_file(temp_path)
                assert config.sample_rate == test_data["sample_rate"]
                assert config.rate == test_data["rate"]
                assert config.block_size == test_data["sample_rate"] // test_data["rate"]
            finally:
                Path(temp_path).unlink()
