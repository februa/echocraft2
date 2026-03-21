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

    def test_initialization_with_lossless_model(self):
        """Test PlaneWavePropagator initialization with lossless model."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config, model="lossless")

        assert propagator.model == "lossless"

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
        """Test Thorp absorption at 1 kHz: alpha ≈ 0.0598 dB/km."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)

        source_record = {
            "type": "source",
            "freq": 1000.0,
            "sl": 150.0,
            "az": 45.0,
            "el": 10.0
        }

        result = propagator.propagate(source_record)

        # Thorp at 1 kHz: alpha = 0.1*1/(1+1) + 40*1/(4100+1) ≈ 0.0598 dB/km
        f_khz = 1.0
        f2 = f_khz ** 2
        expected_alpha = 0.1 * f2 / (1.0 + f2) + 40.0 * f2 / (4100.0 + f2)
        expected_sl = 150.0 - expected_alpha
        assert abs(result["sl"] - expected_sl) < 1e-9

    def test_absorption_with_different_frequencies(self):
        """Test Thorp absorption at various frequencies."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)

        test_freqs = [50.0, 200.0, 1000.0, 5000.0, 10000.0]

        for freq in test_freqs:
            propagator.reset()
            sl = 150.0
            source_record = {
                "type": "source",
                "freq": freq,
                "sl": sl,
                "az": 45.0,
                "el": 10.0
            }
            result = propagator.propagate(source_record)

            f_khz = freq / 1000.0
            f2 = f_khz ** 2
            expected_alpha = 0.1 * f2 / (1.0 + f2) + 40.0 * f2 / (4100.0 + f2)
            expected_sl = sl - expected_alpha
            assert abs(result["sl"] - expected_sl) < 1e-9, (
                f"freq={freq}: expected {expected_sl}, got {result['sl']}"
            )

    def test_absorption_increases_with_frequency(self):
        """Test that absorption increases monotonically with frequency."""
        ocean_config = {"depth": 100.0}
        propagator = PlaneWavePropagator(ocean_config)

        prev_loss = 0.0
        for freq in [100.0, 500.0, 1000.0, 5000.0, 10000.0]:
            propagator.reset()
            source_record = {
                "type": "source",
                "freq": freq,
                "sl": 150.0,
                "az": 45.0,
                "el": 10.0
            }
            result = propagator.propagate(source_record)
            loss = 150.0 - result["sl"]
            assert loss > prev_loss, f"Loss at {freq} Hz ({loss}) not greater than at lower freq ({prev_loss})"
            prev_loss = loss

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
        """Test propagate with negative frequency (Thorp uses f^2, so same loss as positive)."""
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

        # Thorp formula uses f^2, so negative freq gives same absorption as positive
        f_khz = 0.1  # |100| / 1000
        f2 = f_khz ** 2
        expected_alpha = 0.1 * f2 / (1.0 + f2) + 40.0 * f2 / (4100.0 + f2)
        expected_sl = 150.0 - expected_alpha
        assert abs(result["sl"] - expected_sl) < 1e-9


class TestLosslessModel:
    """Test suite for lossless propagation model."""

    def test_lossless_preserves_sl(self):
        """Test that lossless model preserves SL exactly."""
        propagator = PlaneWavePropagator({"depth": 100.0}, model="lossless")

        for freq in [100.0, 1000.0, 10000.0]:
            propagator.reset()
            source = {"type": "source", "freq": freq, "sl": 150.0, "az": 0.0, "el": 0.0}
            result = propagator.propagate(source)
            assert result["sl"] == 150.0, f"SL changed at {freq} Hz"

    def test_lossless_assigns_source_id(self):
        """Test that lossless model still assigns source_id."""
        propagator = PlaneWavePropagator({"depth": 100.0}, model="lossless")
        s1 = propagator.propagate({"type": "source", "freq": 100.0, "sl": 0.0, "az": 0.0, "el": 0.0})
        s2 = propagator.propagate({"type": "source", "freq": 200.0, "sl": 0.0, "az": 0.0, "el": 0.0})
        assert s1["source_id"] == 0
        assert s2["source_id"] == 1

    def test_lossless_passes_through_non_source(self):
        """Test that lossless model passes through non-source records."""
        propagator = PlaneWavePropagator({"depth": 100.0}, model="lossless")
        noise = {"type": "noise", "nl": -40.0}
        assert propagator.propagate(noise) == noise

    def test_unknown_model_raises(self):
        """Test that unknown model name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown model"):
            PlaneWavePropagator({"depth": 100.0}, model="unknown")
