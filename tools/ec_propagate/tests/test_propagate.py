"""Unit tests for ec_propagate propagate module."""

import pytest
from ec_propagate.propagate import PlaneWavePropagator


class TestPlaneWavePropagator:
    """Test suite for PlaneWavePropagator class."""

    def test_initialization(self):
        """Test PlaneWavePropagator initialization."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        assert propagator.ocean_config == ocean_config
        assert propagator.model == "plane-wave"

    def test_initialization_with_custom_model(self):
        """Test PlaneWavePropagator initialization with custom model."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config, model="spherical-wave")
        
        assert propagator.model == "spherical-wave"

    def test_source_record_gets_source_id_assigned(self):
        """Test that source record gets source_id assigned."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        source_record = {
            "type": "source",
            "freq": 100.0,
            "sl": 150.0,
            "az": 45.0,
            "el": 10.0
        }
        
        result = propagator.propagate(source_record)
        
        assert "source_id" in result
        assert result["source_id"] == 0

    def test_absorption_loss_computed_correctly(self):
        """Test that absorption loss is computed correctly (alpha = 0.001 * freq)."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        source_record = {
            "type": "source",
            "freq": 100.0,
            "sl": 150.0,
            "az": 45.0,
            "el": 10.0
        }
        
        result = propagator.propagate(source_record)
        
        # alpha = 0.001 * 100 = 0.1 dB/km
        # loss = 0.1 dB for 1 km
        expected_sl = 150.0 - 0.1
        assert abs(result["sl"] - expected_sl) < 1e-9

    def test_absorption_with_different_frequencies(self):
        """Test absorption loss with different frequencies."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        test_cases = [
            (50.0, 150.0, 150.0 - 0.05),    # alpha = 0.05, sl = 149.95
            (200.0, 160.0, 160.0 - 0.2),    # alpha = 0.2, sl = 159.8
            (1000.0, 170.0, 170.0 - 1.0),   # alpha = 1.0, sl = 169.0
        ]
        
        for freq, sl, expected_sl in test_cases:
            propagator.reset()
            source_record = {
                "type": "source",
                "freq": freq,
                "sl": sl,
                "az": 45.0,
                "el": 10.0
            }
            result = propagator.propagate(source_record)
            assert abs(result["sl"] - expected_sl) < 1e-9

    def test_sequential_source_ids(self):
        """Test that source_ids are assigned sequentially (0, 1, 2...)."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        source_ids = []
        for i in range(5):
            source_record = {
                "type": "source",
                "freq": 100.0 + i * 10,
                "sl": 150.0,
                "az": 45.0,
                "el": 10.0
            }
            result = propagator.propagate(source_record)
            source_ids.append(result["source_id"])
        
        assert source_ids == [0, 1, 2, 3, 4]

    def test_non_source_records_pass_through_unchanged(self):
        """Test that non-source records pass through unchanged."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        noise_record = {
            "type": "noise",
            "nl": 75.0
        }
        
        result = propagator.propagate(noise_record)
        
        # Should be unchanged
        assert result == noise_record
        assert "source_id" not in result

    def test_non_source_record_does_not_increment_counter(self):
        """Test that non-source records don't increment source_id counter."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        # Process non-source record
        noise_record = {"type": "noise", "nl": 75.0}
        propagator.propagate(noise_record)
        
        # Process source record
        source_record = {
            "type": "source",
            "freq": 100.0,
            "sl": 150.0,
            "az": 45.0,
            "el": 10.0
        }
        result = propagator.propagate(source_record)
        
        # source_id should still be 0
        assert result["source_id"] == 0

    def test_reset_resets_counter(self):
        """Test that reset() resets the source_id counter."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        # Process some records
        for i in range(3):
            source_record = {
                "type": "source",
                "freq": 100.0,
                "sl": 150.0,
                "az": 45.0,
                "el": 10.0
            }
            propagator.propagate(source_record)
        
        # Reset counter
        propagator.reset()
        
        # Process another record
        source_record = {
            "type": "source",
            "freq": 100.0,
            "sl": 150.0,
            "az": 45.0,
            "el": 10.0
        }
        result = propagator.propagate(source_record)
        
        # source_id should be 0 again
        assert result["source_id"] == 0

    def test_propagate_preserves_other_fields(self):
        """Test that propagate preserves other fields in source record."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        source_record = {
            "type": "source",
            "freq": 100.0,
            "sl": 150.0,
            "az": 45.0,
            "el": 10.0,
            "extra_field": "extra_value"
        }
        
        result = propagator.propagate(source_record)
        
        assert result["type"] == "source"
        assert result["freq"] == 100.0
        assert result["az"] == 45.0
        assert result["el"] == 10.0
        assert result["extra_field"] == "extra_value"

    def test_propagate_with_zero_frequency(self):
        """Test propagate with zero frequency (alpha = 0)."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        source_record = {
            "type": "source",
            "freq": 0.0,
            "sl": 150.0,
            "az": 45.0,
            "el": 10.0
        }
        
        result = propagator.propagate(source_record)
        
        # alpha = 0, so sl should remain unchanged
        assert result["sl"] == 150.0

    def test_propagate_with_negative_frequency(self):
        """Test propagate with negative frequency (alpha negative)."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)
        
        source_record = {
            "type": "source",
            "freq": -100.0,
            "sl": 150.0,
            "az": 45.0,
            "el": 10.0
        }
        
        result = propagator.propagate(source_record)
        
        # alpha = -0.1, so sl should increase by 0.1
        expected_sl = 150.0 + 0.1
        assert abs(result["sl"] - expected_sl) < 1e-9
