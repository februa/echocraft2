"""Unit tests for EmaIntegrator."""

import pytest
from eca_integrate.integrator import EmaIntegrator


class TestEmaIntegratorValidation:
    """Test EmaIntegrator initialization and validation."""

    def test_valid_alpha_range_lower_bound(self):
        """Test that alpha must be > 0."""
        with pytest.raises(ValueError, match="alpha must be in"):
            EmaIntegrator(0.0)
        
        with pytest.raises(ValueError, match="alpha must be in"):
            EmaIntegrator(-0.1)

    def test_valid_alpha_range_upper_bound(self):
        """Test that alpha must be <= 1.0."""
        with pytest.raises(ValueError, match="alpha must be in"):
            EmaIntegrator(1.1)
        
        with pytest.raises(ValueError, match="alpha must be in"):
            EmaIntegrator(2.0)

    def test_valid_alpha_values(self):
        """Test that valid alpha values are accepted."""
        # Should not raise
        EmaIntegrator(0.1)
        EmaIntegrator(0.5)
        EmaIntegrator(1.0)
        EmaIntegrator(0.001)


class TestEmaIntegratorFirstSample:
    """Test EmaIntegrator behavior on first sample."""

    def test_first_sample_uses_input_value(self):
        """Test that first sample output equals input value (no averaging)."""
        integrator = EmaIntegrator(0.1)
        
        records = [
            {"type": "spectrum", "freq": 100.0, "power_db": -10.0},
            {"type": "spectrum", "freq": 200.0, "power_db": -20.0},
        ]
        
        output = integrator.integrate(records)
        
        # Should have same frequencies and values on first call
        assert len(output) == 2
        assert output[0]["freq"] == 100.0
        assert output[0]["power_db"] == -10.0
        assert output[1]["freq"] == 200.0
        assert output[1]["power_db"] == -20.0


class TestEmaIntegratorFormula:
    """Test the EMA formula implementation."""

    def test_ema_formula_applied_correctly(self):
        """Test that EMA formula is applied: alpha * new + (1-alpha) * old."""
        alpha = 0.4
        integrator = EmaIntegrator(alpha)
        
        # First integration
        records1 = [{"type": "spectrum", "freq": 100.0, "power_db": 10.0}]
        output1 = integrator.integrate(records1)
        assert output1[0]["power_db"] == 10.0
        
        # Second integration: should apply EMA formula
        records2 = [{"type": "spectrum", "freq": 100.0, "power_db": 20.0}]
        output2 = integrator.integrate(records2)
        
        expected = 0.4 * 20.0 + 0.6 * 10.0  # alpha * new + (1-alpha) * old
        assert pytest.approx(output2[0]["power_db"]) == expected

    def test_ema_convergence(self):
        """Test that repeated same values converge to that value."""
        alpha = 0.5
        integrator = EmaIntegrator(alpha)
        
        # Apply same value multiple times
        target_value = 15.0
        for i in range(10):
            records = [{"type": "spectrum", "freq": 100.0, "power_db": target_value}]
            output = integrator.integrate(records)
        
        # Should converge to target value
        assert pytest.approx(output[0]["power_db"], abs=0.01) == target_value

    def test_ema_with_different_alpha_values(self):
        """Test that higher alpha gives more weight to new samples."""
        records1 = [{"type": "spectrum", "freq": 100.0, "power_db": 10.0}]
        records2 = [{"type": "spectrum", "freq": 100.0, "power_db": 30.0}]
        
        # Low alpha (smooth)
        integrator_low = EmaIntegrator(0.1)
        integrator_low.integrate(records1)
        output_low = integrator_low.integrate(records2)
        
        # High alpha (responsive)
        integrator_high = EmaIntegrator(0.9)
        integrator_high.integrate(records1)
        output_high = integrator_high.integrate(records2)
        
        # High alpha should be closer to new value (30)
        diff_low = abs(output_low[0]["power_db"] - 30.0)
        diff_high = abs(output_high[0]["power_db"] - 30.0)
        assert diff_high < diff_low


class TestEmaIntegratorAccumulation:
    """Test accumulation across multiple integrate calls."""

    def test_accumulation_across_calls(self):
        """Test that spectrum state accumulates across multiple integrate calls."""
        integrator = EmaIntegrator(0.5)
        
        # First call: add frequencies
        records1 = [
            {"type": "spectrum", "freq": 100.0, "power_db": 10.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 20.0},
        ]
        output1 = integrator.integrate(records1)
        assert len(output1) == 2
        
        # Second call: add new frequency, update existing
        records2 = [
            {"type": "spectrum", "freq": 100.0, "power_db": 15.0},
            {"type": "spectrum", "freq": 300.0, "power_db": 30.0},
        ]
        output2 = integrator.integrate(records2)
        
        # Should have all three frequencies
        assert len(output2) == 3
        freqs = [r["freq"] for r in output2]
        assert 100.0 in freqs
        assert 200.0 in freqs
        assert 300.0 in freqs

    def test_persistent_spectrum_state(self):
        """Test that spectrum state persists between calls."""
        integrator = EmaIntegrator(0.3)
        
        # Add initial value
        integrator.integrate([{"type": "spectrum", "freq": 100.0, "power_db": 5.0}])
        
        # Call with different record, old frequency should persist
        integrator.integrate([{"type": "spectrum", "freq": 200.0, "power_db": 10.0}])
        
        # Now update both
        output = integrator.integrate([
            {"type": "spectrum", "freq": 100.0, "power_db": 20.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 25.0},
        ])
        
        # Both frequencies should be in output
        assert len(output) == 2


class TestEmaIntegratorOutputOrder:
    """Test output ordering."""

    def test_output_sorted_by_frequency(self):
        """Test that output is sorted by frequency."""
        integrator = EmaIntegrator(0.5)
        
        # Add records in non-sorted order
        records = [
            {"type": "spectrum", "freq": 300.0, "power_db": 5.0},
            {"type": "spectrum", "freq": 100.0, "power_db": 10.0},
            {"type": "spectrum", "freq": 200.0, "power_db": 15.0},
        ]
        
        output = integrator.integrate(records)
        
        # Output should be sorted
        freqs = [r["freq"] for r in output]
        assert freqs == sorted(freqs)
        assert freqs == [100.0, 200.0, 300.0]


class TestEmaIntegratorNonSpectrumRecords:
    """Test handling of non-spectrum records."""

    def test_non_spectrum_records_ignored(self):
        """Test that non-spectrum records are ignored."""
        integrator = EmaIntegrator(0.5)
        
        records = [
            {"type": "scalar", "key": "peak_freq", "value": 100.0},
            {"type": "spectrum", "freq": 100.0, "power_db": 10.0},
            {"type": "metadata", "name": "test"},
            {"type": "spectrum", "freq": 200.0, "power_db": 20.0},
        ]
        
        output = integrator.integrate(records)
        
        # Only spectrum records should be in output
        assert all(r["type"] == "spectrum" for r in output)
        assert len(output) == 2

    def test_empty_spectrum_records_returns_empty(self):
        """Test that input with no spectrum records returns empty."""
        integrator = EmaIntegrator(0.5)
        
        records = [
            {"type": "scalar", "key": "peak_freq", "value": 100.0},
            {"type": "metadata", "name": "test"},
        ]
        
        output = integrator.integrate(records)
        
        assert len(output) == 0

    def test_empty_input_returns_previous_state(self):
        """Test that empty input returns current accumulated state."""
        integrator = EmaIntegrator(0.5)
        
        # Add initial data
        records1 = [{"type": "spectrum", "freq": 100.0, "power_db": 10.0}]
        integrator.integrate(records1)
        
        # Call with empty spectrum records
        records2 = [{"type": "scalar", "key": "other"}]
        output = integrator.integrate(records2)
        
        # Should return current state
        assert len(output) == 1
        assert output[0]["freq"] == 100.0
        assert output[0]["power_db"] == 10.0


class TestEmaIntegratorRecordStructure:
    """Test output record structure."""

    def test_output_record_structure(self):
        """Test that output records have correct structure."""
        integrator = EmaIntegrator(0.5)
        
        records = [{"type": "spectrum", "freq": 100.0, "power_db": 10.0}]
        output = integrator.integrate(records)
        
        record = output[0]
        assert record["type"] == "spectrum"
        assert "freq" in record
        assert "power_db" in record
        assert isinstance(record["freq"], (int, float))
        assert isinstance(record["power_db"], (int, float))
