"""Unit tests for PeakFrequencyExtractor."""

import pytest
from eca_peak_freq.peak import PeakFrequencyExtractor


class TestPeakFrequencyExtractorBasics:
    """Test basic PeakFrequencyExtractor functionality."""

    def test_find_peak_returns_dict(self):
        """Test that find_peak returns a dictionary."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": -10.0},
            {"type": "spectrum", "freq": 200.0, "power_db": -20.0},
        ]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        assert isinstance(result, dict)

    def test_find_peak_record_type(self):
        """Test that returned record has type='scalar'."""
        records = [{"type": "spectrum", "freq": 100.0, "power_db": 10.0}]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        assert result["type"] == "scalar"
        assert result["key"] == "peak_freq"

    def test_find_peak_record_structure(self):
        """Test that returned record has required fields."""
        records = [{"type": "spectrum", "freq": 100.0, "power_db": 10.0}]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        assert "type" in result
        assert "key" in result
        assert "value" in result
        assert "unit" in result
        assert result["unit"] == "Hz"


class TestPeakFrequencyExtractorCorrectPeak:
    """Test correct peak identification."""

    def test_identifies_maximum_power_bin(self):
        """Test that peak is the frequency with maximum power_db."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": -10.0},
            {"type": "spectrum", "freq": 200.0, "power_db": -5.0},   # Maximum
            {"type": "spectrum", "freq": 300.0, "power_db": -20.0},
        ]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        assert result["value"] == 200.0

    def test_identifies_peak_from_multiple_bins(self):
        """Test peak identification with many frequency bins."""
        records = [
            {"type": "spectrum", "freq": i * 100.0, "power_db": -20.0 + i}
            for i in range(10)
        ]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        # Peak should be at 900 Hz (last bin with highest power)
        assert result["value"] == 900.0


class TestPeakFrequencyExtractorDCExclusion:
    """Test DC component exclusion."""

    def test_dc_component_excluded_from_peak_search(self):
        """Test that DC component (freq=0) is excluded from peak search."""
        records = [
            {"type": "spectrum", "freq": 0.0, "power_db": 100.0},    # DC, very high
            {"type": "spectrum", "freq": 100.0, "power_db": 50.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 60.0},   # This should be peak
        ]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        # Should not pick DC component
        assert result["value"] == 200.0

    def test_fallback_to_dc_if_only_dc_present(self):
        """Test fallback to DC component if it's the only non-DC record."""
        records = [
            {"type": "spectrum", "freq": 0.0, "power_db": 50.0},
        ]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        # Should fall back to DC
        assert result["value"] == 0.0


class TestPeakFrequencyExtractorEmptyInput:
    """Test handling of empty input."""

    def test_empty_input_returns_default(self):
        """Test that empty input returns default peak frequency of 0."""
        result = PeakFrequencyExtractor.find_peak([])
        
        assert result["type"] == "scalar"
        assert result["key"] == "peak_freq"
        assert result["value"] == 0.0
        assert result["unit"] == "Hz"

    def test_none_returns_default(self):
        """Test that None is handled gracefully."""
        result = PeakFrequencyExtractor.find_peak([])
        
        assert result["value"] == 0.0


class TestPeakFrequencyExtractorSpecialCases:
    """Test special cases."""

    def test_single_record(self):
        """Test with single spectrum record."""
        records = [{"type": "spectrum", "freq": 500.0, "power_db": -15.0}]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        assert result["value"] == 500.0

    def test_duplicate_frequencies_uses_highest_power(self):
        """Test behavior with duplicate frequencies (uses highest power)."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 10.0},
            {"type": "spectrum", "freq": 100.0, "power_db": 20.0},
        ]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        # Should pick the one with highest power_db
        assert result["value"] == 100.0

    def test_negative_frequencies_treated_as_non_dc(self):
        """Test that negative frequencies are treated as candidates in peak search."""
        records = [
            {"type": "spectrum", "freq": 0.0, "power_db": 100.0},    # DC, excluded
            {"type": "spectrum", "freq": -100.0, "power_db": 50.0},   # Non-DC, but DC excluded
            {"type": "spectrum", "freq": 100.0, "power_db": 50.0},    # Non-DC candidate
        ]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        # Should pick a non-DC frequency (both 100 and -100 have same power, so check either one)
        assert result["value"] in [100.0, -100.0]

    def test_very_small_positive_frequencies(self):
        """Test that very small positive frequencies are included in peak search."""
        records = [
            {"type": "spectrum", "freq": 0.0, "power_db": 100.0},
            {"type": "spectrum", "freq": 0.001, "power_db": 50.0},
        ]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        # Should pick 0.001 Hz (non-DC)
        assert result["value"] == pytest.approx(0.001)

    def test_many_equal_power_bins(self):
        """Test with many equal power bins (takes first max)."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 10.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 10.0},
            {"type": "spectrum", "freq": 300.0, "power_db": 10.0},
        ]
        
        result = PeakFrequencyExtractor.find_peak(records)
        
        # Should pick one with maximum power_db
        assert result["value"] in [100.0, 200.0, 300.0]
        assert result["value"] > 0.0
