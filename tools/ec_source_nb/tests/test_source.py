"""Unit tests for ec_source_nb source module."""

import pytest
from ec_source_nb.source import NarrowbandSource
from ec_source_nb.records import SourceRecord


class TestNarrowbandSource:
    """Test suite for NarrowbandSource class."""

    def test_valid_creation(self):
        """Test creating a valid NarrowbandSource."""
        source = NarrowbandSource(freq=100.0, sl=150.0, az=45.0, el=10.0)
        assert source.freq == 100.0
        assert source.sl == 150.0
        assert source.az == 45.0
        assert source.el == 10.0

    def test_freq_must_be_positive(self):
        """Test that freq <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="Frequency must be positive"):
            NarrowbandSource(freq=0, sl=150.0, az=45.0, el=10.0)
        
        with pytest.raises(ValueError, match="Frequency must be positive"):
            NarrowbandSource(freq=-100.0, sl=150.0, az=45.0, el=10.0)

    def test_to_record_returns_source_record(self):
        """Test that to_record() returns correct SourceRecord."""
        source = NarrowbandSource(freq=50.0, sl=140.0, az=90.0, el=-5.0)
        record = source.to_record()
        
        assert isinstance(record, SourceRecord)
        assert record.freq == 50.0
        assert record.sl == 140.0
        assert record.az == 90.0
        assert record.el == -5.0
        assert record.type == "source"

    def test_freq_with_small_positive_value(self):
        """Test that small positive frequencies are accepted."""
        source = NarrowbandSource(freq=0.001, sl=150.0, az=45.0, el=10.0)
        assert source.freq == 0.001


class TestSourceRecord:
    """Test suite for SourceRecord class."""

    def test_record_is_frozen(self):
        """Test that SourceRecord is immutable (frozen)."""
        record = SourceRecord(freq=100.0, sl=150.0, az=45.0, el=10.0)
        
        with pytest.raises(Exception):  # FrozenInstanceError
            record.freq = 200.0

    def test_to_dict_returns_correct_structure(self):
        """Test that to_dict() returns correct dict with type='source'."""
        record = SourceRecord(freq=75.0, sl=145.0, az=180.0, el=0.0)
        result = record.to_dict()
        
        assert isinstance(result, dict)
        assert result["type"] == "source"
        assert result["freq"] == 75.0
        assert result["sl"] == 145.0
        assert result["az"] == 180.0
        assert result["el"] == 0.0

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict() includes all expected fields."""
        record = SourceRecord(freq=50.0, sl=140.0, az=45.0, el=5.0)
        result = record.to_dict()
        
        expected_keys = {"type", "freq", "sl", "az", "el"}
        assert set(result.keys()) == expected_keys

    def test_default_type_field(self):
        """Test that default type field is 'source'."""
        record = SourceRecord(freq=100.0, sl=150.0, az=45.0, el=10.0)
        assert record.type == "source"

    def test_record_with_negative_elevation(self):
        """Test record creation with negative elevation values."""
        record = SourceRecord(freq=100.0, sl=150.0, az=45.0, el=-45.0)
        assert record.el == -45.0
        assert record.to_dict()["el"] == -45.0

    def test_record_with_large_azimuth(self):
        """Test record creation with azimuth values."""
        record = SourceRecord(freq=100.0, sl=150.0, az=359.9, el=10.0)
        assert record.az == 359.9
        assert record.to_dict()["az"] == 359.9
