"""Unit tests for ec_noise noise module."""

import math
import pytest
from ec_noise.noise import NoiseField
from ec_noise.records import NoiseRecord


class TestNoiseField:
    """Test suite for NoiseField class."""

    def test_valid_creation(self):
        """Test creating a valid NoiseField."""
        noise = NoiseField(nl=75.0)
        assert noise.nl == 75.0

    def test_zero_noise_level(self):
        """Test that zero noise level is valid."""
        noise = NoiseField(nl=0.0)
        assert noise.nl == 0.0

    def test_negative_noise_level(self):
        """Test that negative noise levels are valid (they represent lower levels)."""
        noise = NoiseField(nl=-10.0)
        assert noise.nl == -10.0

    def test_large_noise_level(self):
        """Test that large noise levels are valid."""
        noise = NoiseField(nl=200.0)
        assert noise.nl == 200.0

    def test_inf_raises_value_error(self):
        """Test that inf noise level raises ValueError."""
        with pytest.raises(ValueError, match="Noise level must be finite"):
            NoiseField(nl=math.inf)

    def test_negative_inf_raises_value_error(self):
        """Test that negative inf noise level raises ValueError."""
        with pytest.raises(ValueError, match="Noise level must be finite"):
            NoiseField(nl=-math.inf)

    def test_nan_raises_value_error(self):
        """Test that nan noise level raises ValueError."""
        with pytest.raises(ValueError, match="Noise level must be finite"):
            NoiseField(nl=math.nan)

    def test_to_record_returns_noise_record(self):
        """Test that to_record() returns correct NoiseRecord."""
        noise = NoiseField(nl=80.0)
        record = noise.to_record()
        
        assert isinstance(record, NoiseRecord)
        assert record.nl == 80.0
        assert record.type == "noise"

    def test_to_record_with_various_levels(self):
        """Test to_record() with various noise levels."""
        levels = [0.0, 50.0, 75.0, 100.0, -20.0]
        for level in levels:
            noise = NoiseField(nl=level)
            record = noise.to_record()
            assert record.nl == level


class TestNoiseRecord:
    """Test suite for NoiseRecord class."""

    def test_record_is_frozen(self):
        """Test that NoiseRecord is immutable (frozen)."""
        record = NoiseRecord(nl=75.0)
        
        with pytest.raises(Exception):  # FrozenInstanceError
            record.nl = 80.0

    def test_to_dict_returns_correct_structure(self):
        """Test that to_dict() returns correct dict with type='noise'."""
        record = NoiseRecord(nl=75.0)
        result = record.to_dict()
        
        assert isinstance(result, dict)
        assert result["type"] == "noise"
        assert result["nl"] == 75.0

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict() includes all expected fields."""
        record = NoiseRecord(nl=80.0)
        result = record.to_dict()
        
        expected_keys = {"type", "nl"}
        assert set(result.keys()) == expected_keys

    def test_default_type_field(self):
        """Test that default type field is 'noise'."""
        record = NoiseRecord(nl=75.0)
        assert record.type == "noise"

    def test_record_with_negative_noise_level(self):
        """Test record with negative noise level."""
        record = NoiseRecord(nl=-20.0)
        assert record.nl == -20.0
        assert record.to_dict()["nl"] == -20.0

    def test_record_with_zero_noise_level(self):
        """Test record with zero noise level."""
        record = NoiseRecord(nl=0.0)
        assert record.nl == 0.0
        assert record.to_dict()["nl"] == 0.0

    def test_record_with_decimal_precision(self):
        """Test record preserves decimal precision."""
        record = NoiseRecord(nl=75.123456)
        assert record.nl == 75.123456
        assert record.to_dict()["nl"] == 75.123456
