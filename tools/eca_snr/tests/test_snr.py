"""Unit tests for SnrEstimator."""

import numpy as np
import pytest
from eca_snr.snr import SnrEstimator


class TestSnrEstimatorBasics:
    """Test basic SnrEstimator functionality."""

    def test_estimate_returns_dict(self):
        """Test that estimate returns a dictionary."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": -10.0},
            {"type": "spectrum", "freq": 200.0, "power_db": -20.0},
        ]
        
        result = SnrEstimator.estimate(records)
        
        assert isinstance(result, dict)

    def test_estimate_record_structure(self):
        """Test that returned record has correct structure."""
        records = [{"type": "spectrum", "freq": 100.0, "power_db": 10.0}]
        
        result = SnrEstimator.estimate(records)
        
        assert result["type"] == "scalar"
        assert result["key"] == "snr"
        assert "value" in result
        assert result["unit"] == "dB"

    def test_estimate_returns_float_value(self):
        """Test that SNR value is a float."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 10.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 5.0},
        ]
        
        result = SnrEstimator.estimate(records)
        
        assert isinstance(result["value"], (int, float))


class TestSnrEstimatorWithoutPeakFreq:
    """Test SNR estimation without peak_freq parameter."""

    def test_signal_is_maximum_power(self):
        """Test that signal is identified as maximum power when no peak_freq given."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 5.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 20.0},    # Maximum
            {"type": "spectrum", "freq": 300.0, "power_db": 10.0},
        ]
        
        result = SnrEstimator.estimate(records)
        
        # Signal should be 20 dB, noise should be median (10 dB)
        # SNR = 20 - 10 = 10 dB
        assert pytest.approx(result["value"]) == 10.0

    def test_noise_is_median_power(self):
        """Test that noise is identified as median power."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 5.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 10.0},   # Median
            {"type": "spectrum", "freq": 300.0, "power_db": 15.0},
        ]
        
        result = SnrEstimator.estimate(records)
        
        # Signal = max = 15, Noise = median = 10
        # SNR = 15 - 10 = 5
        assert pytest.approx(result["value"]) == 5.0

    def test_snr_formula_without_peak_freq(self):
        """Test SNR = signal - noise formula without peak_freq."""
        records = [
            {"type": "spectrum", "freq": i * 100.0, "power_db": float(i)}
            for i in range(1, 10)
        ]
        
        result = SnrEstimator.estimate(records)
        
        # Signal = max = 9, Noise = median of [1,2,3,4,5,6,7,8,9] = 5
        # SNR = 9 - 5 = 4
        assert pytest.approx(result["value"]) == 4.0


class TestSnrEstimatorWithPeakFreq:
    """Test SNR estimation with peak_freq parameter."""

    def test_signal_uses_peak_freq_when_provided(self):
        """Test that signal uses power at peak_freq when provided."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 5.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 20.0},
            {"type": "spectrum", "freq": 300.0, "power_db": 10.0},
        ]
        
        # Use 100 Hz as peak, but it's not the max
        result = SnrEstimator.estimate(records, peak_freq=100.0)
        
        # Signal at 100 Hz = 5, Noise = median = 10
        # SNR = 5 - 10 = -5
        assert pytest.approx(result["value"]) == -5.0

    def test_peak_freq_frequency_tolerance(self):
        """Test that peak frequency lookup has small tolerance (1e-6)."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 15.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 5.0},
            {"type": "spectrum", "freq": 300.0, "power_db": 10.0},
        ]
        
        # Try with slightly different peak_freq (within tolerance)
        result1 = SnrEstimator.estimate(records, peak_freq=100.0)
        result2 = SnrEstimator.estimate(records, peak_freq=100.0 + 1e-7)
        
        # Should match within tolerance
        assert pytest.approx(result1["value"]) == result2["value"]

    def test_peak_freq_outside_tolerance_uses_max(self):
        """Test fallback to max when peak_freq not found."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 5.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 20.0},
            {"type": "spectrum", "freq": 300.0, "power_db": 10.0},
        ]
        
        # Use peak_freq that's not in records
        result = SnrEstimator.estimate(records, peak_freq=150.0)
        
        # Should fall back to max = 20
        # Noise = median = 10
        # SNR = 20 - 10 = 10
        assert pytest.approx(result["value"]) == 10.0

    def test_snr_formula_with_peak_freq(self):
        """Test SNR = signal - noise formula with peak_freq."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 10.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 20.0},
            {"type": "spectrum", "freq": 300.0, "power_db": 15.0},
        ]
        
        result = SnrEstimator.estimate(records, peak_freq=200.0)
        
        # Signal at 200 Hz = 20, Noise = median = 15
        # SNR = 20 - 15 = 5
        assert pytest.approx(result["value"]) == 5.0


class TestSnrEstimatorEmptyInput:
    """Test handling of empty input."""

    def test_empty_input_returns_default(self):
        """Test that empty input returns default SNR of 0."""
        result = SnrEstimator.estimate([])
        
        assert result["type"] == "scalar"
        assert result["key"] == "snr"
        assert result["value"] == 0.0
        assert result["unit"] == "dB"

    def test_empty_with_peak_freq_returns_default(self):
        """Test that empty input returns default even with peak_freq."""
        result = SnrEstimator.estimate([], peak_freq=1000.0)
        
        assert result["value"] == 0.0


class TestSnrEstimatorSpecialCases:
    """Test special cases."""

    def test_single_frequency_bin(self):
        """Test SNR with single frequency bin."""
        records = [{"type": "spectrum", "freq": 100.0, "power_db": 10.0}]
        
        result = SnrEstimator.estimate(records)
        
        # Signal = 10, Noise = 10 (median of single value)
        # SNR = 0
        assert pytest.approx(result["value"]) == 0.0

    def test_two_frequency_bins(self):
        """Test SNR with two frequency bins."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 10.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 20.0},
        ]
        
        result = SnrEstimator.estimate(records)
        
        # Signal = max = 20, Noise = median = 15
        # SNR = 5
        assert pytest.approx(result["value"]) == 5.0

    def test_negative_snr_possible(self):
        """Test that negative SNR is possible when signal < noise."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": -20.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 0.0},
            {"type": "spectrum", "freq": 300.0, "power_db": 10.0},
        ]
        
        result = SnrEstimator.estimate(records, peak_freq=100.0)
        
        # Signal at 100 Hz = -20, Noise = median = 0
        # SNR = -20 - 0 = -20
        assert result["value"] < 0

    def test_identical_all_bins(self):
        """Test with all bins having identical power."""
        records = [
            {"type": "spectrum", "freq": float(i) * 100.0, "power_db": 10.0}
            for i in range(1, 6)
        ]
        
        result = SnrEstimator.estimate(records)
        
        # Signal = 10, Noise = 10 (median)
        # SNR = 0
        assert pytest.approx(result["value"]) == 0.0

    def test_very_large_power_values(self):
        """Test with very large power values."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 1000.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 900.0},
            {"type": "spectrum", "freq": 300.0, "power_db": 800.0},
        ]
        
        result = SnrEstimator.estimate(records)
        
        # Signal = 1000, Noise = 900
        # SNR = 100
        assert pytest.approx(result["value"]) == 100.0

    def test_very_small_power_values(self):
        """Test with very small power values."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": -200.0},
            {"type": "spectrum", "freq": 200.0, "power_db": -210.0},
            {"type": "spectrum", "freq": 300.0, "power_db": -220.0},
        ]
        
        result = SnrEstimator.estimate(records)
        
        # Signal = -200, Noise = -210
        # SNR = 10
        assert pytest.approx(result["value"]) == 10.0


class TestSnrEstimatorMedianCalculation:
    """Test median noise calculation."""

    def test_median_with_odd_count(self):
        """Test median calculation with odd number of bins."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 1.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 2.0},
            {"type": "spectrum", "freq": 300.0, "power_db": 3.0},
            {"type": "spectrum", "freq": 400.0, "power_db": 4.0},
            {"type": "spectrum", "freq": 500.0, "power_db": 5.0},
        ]
        
        result = SnrEstimator.estimate(records)
        
        # Signal = 5, Noise = median([1,2,3,4,5]) = 3
        # SNR = 5 - 3 = 2
        assert pytest.approx(result["value"]) == 2.0

    def test_median_with_even_count(self):
        """Test median calculation with even number of bins."""
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": 1.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 2.0},
            {"type": "spectrum", "freq": 300.0, "power_db": 3.0},
            {"type": "spectrum", "freq": 400.0, "power_db": 4.0},
        ]
        
        result = SnrEstimator.estimate(records)
        
        # Signal = 4, Noise = median([1,2,3,4]) = 2.5
        # SNR = 4 - 2.5 = 1.5
        assert pytest.approx(result["value"]) == 1.5
