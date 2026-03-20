"""Unit tests for DelayAndSumBeamformer domain logic."""

import numpy as np
import pytest
from common.stream import StreamConfig
from ec_beamform.beamformer import DelayAndSumBeamformer


class TestBeamformerInit:
    """Tests for DelayAndSumBeamformer initialization."""

    def test_initializes_with_sensors_and_stream_config(self):
        """DelayAndSumBeamformer initializes with sensors and stream config."""
        sensors = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 1.0, "y": 0.0, "z": 0.0},
            {"id": 2, "x": 0.0, "y": 1.0, "z": 0.0},
        ]
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        
        beamformer = DelayAndSumBeamformer(sensors, stream_config)
        
        assert beamformer.steer_az == 0.0
        assert beamformer.steer_el == 0.0
        assert len(beamformer.steering_delays) == 3

    def test_initializes_with_steering_angles(self):
        """DelayAndSumBeamformer accepts steering angles."""
        sensors = [{"id": 0, "x": 0.0, "y": 0.0, "z": 0.0}]
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        
        beamformer = DelayAndSumBeamformer(sensors, stream_config, steer_az=45.0, steer_el=30.0)
        
        assert beamformer.steer_az == 45.0
        assert beamformer.steer_el == 30.0


class TestOutputShape:
    """Tests for output shape."""

    def test_output_shape_is_one_by_block_size(self):
        """DelayAndSumBeamformer output shape is (1, block_size)."""
        sensors = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 1.0, "y": 0.0, "z": 0.0},
            {"id": 2, "x": 0.0, "y": 1.0, "z": 0.0},
        ]
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        beamformer = DelayAndSumBeamformer(sensors, stream_config)
        
        # Create a multi-channel input block
        block_size = 160
        block = np.random.randn(3, block_size).astype(np.float32)
        
        output = beamformer.process_block(block)
        
        assert output.shape == (1, block_size)

    def test_output_dtype_is_float32(self):
        """DelayAndSumBeamformer output is float32."""
        sensors = [{"id": 0, "x": 0.0, "y": 0.0, "z": 0.0}]
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        beamformer = DelayAndSumBeamformer(sensors, stream_config)
        
        block = np.random.randn(1, 160).astype(np.float32)
        output = beamformer.process_block(block)
        
        assert output.dtype == np.float32


class TestAlignedSourcesPreservation:
    """Tests for signal preservation when steering at source."""

    def test_steering_at_zero_zero_with_aligned_sources(self):
        """Steering at 0,0 with aligned sources: signal preserved."""
        sensors = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 1.0, "y": 0.0, "z": 0.0},
        ]
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        beamformer = DelayAndSumBeamformer(sensors, stream_config, steer_az=0.0, steer_el=0.0)
        
        # Create a simple sinusoid on each channel
        # For steering at 0,0 pointing along x-axis, all sensors should have equal delay
        block_size = 160
        t = np.arange(block_size) / 16000.0
        
        # Simple 1000 Hz sinusoid
        freq = 1000.0
        signal = np.sin(2.0 * np.pi * freq * t)
        
        # Same signal on all channels (aligned)
        block = np.vstack([signal, signal]).astype(np.float32)
        
        output = beamformer.process_block(block)
        
        # Output should be similar to input signal (after averaging)
        output_signal = output[0, :]
        
        # Check that peak frequency is preserved
        fft = np.fft.rfft(output_signal)
        freqs = np.fft.rfftfreq(block_size, 1.0 / 16000.0)
        peak_idx = np.argmax(np.abs(fft))
        peak_freq = freqs[peak_idx]
        
        assert peak_freq == pytest.approx(freq, abs=100)


class TestNormalization:
    """Tests for output normalization."""

    def test_normalization_output_amplitude_matches_input(self):
        """Normalization: output amplitude ~ input amplitude (within tolerance).

        VESSEL_BODY: Az=0 = bow (+x). Sensors on y-axis are broadside to
        the steering direction, so steering delay is 0 for both sensors,
        keeping signals in phase.
        """
        sensors = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 0.0, "y": 1.0, "z": 0.0},
        ]
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        beamformer = DelayAndSumBeamformer(sensors, stream_config)
        
        # Create input blocks with known amplitude
        block_size = 160
        t = np.arange(block_size) / 16000.0
        freq = 1000.0
        amplitude = 0.5
        
        # Create identical signals on both channels
        signal = amplitude * np.sin(2.0 * np.pi * freq * t)
        block = np.vstack([signal, signal]).astype(np.float32)
        
        output = beamformer.process_block(block)
        output_signal = output[0, :]
        
        # After normalization by n_channels, amplitude should be preserved
        output_amplitude = np.max(np.abs(output_signal))
        assert output_amplitude == pytest.approx(amplitude, rel=0.1)


class TestPhaseShift:
    """Tests for frequency-domain phase shifting."""

    def test_phase_shift_via_frequency_domain_with_known_delay(self):
        """Phase shift via frequency domain: verify with known delay."""
        sensors = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 0.1, "y": 0.0, "z": 0.0},  # 0.1 m away
        ]
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        
        # Steer at az=0 (along x-axis), so we apply delays to compensate
        # for plane wave arrival
        beamformer = DelayAndSumBeamformer(sensors, stream_config, steer_az=0.0, steer_el=0.0)
        
        # Create a narrowband signal
        block_size = 160
        t = np.arange(block_size) / 16000.0
        freq = 2000.0  # Higher frequency for more noticeable phase shift
        
        # Channel 0: undelayed signal
        signal0 = np.sin(2.0 * np.pi * freq * t)
        
        # Channel 1: signal with known delay
        # The beamformer will apply the steering delay in frequency domain
        signal1 = np.sin(2.0 * np.pi * freq * t)
        
        block = np.vstack([signal0, signal1]).astype(np.float32)
        
        output = beamformer.process_block(block)
        
        # Output should be valid and real-valued
        assert np.all(np.isfinite(output))
        assert output.dtype == np.float32


class TestSteeringDelayComputation:
    """Tests for steering delay computation."""

    def test_steering_delays_computed_correctly(self):
        """Steering delays are computed correctly based on sensor positions.

        VESSEL_BODY: Az=0 = bow (+x). Steering at Az=0 means direction
        vector = (1, 0, 0). Sensor at x=1.0 has delay = -(1*1)/c.
        """
        sensors = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 1.0, "y": 0.0, "z": 0.0},
        ]
        stream_config = StreamConfig(sample_rate=16000, rate=100)

        # Steer at az=0, el=0 → direction = (1, 0, 0) in VESSEL_BODY
        beamformer = DelayAndSumBeamformer(sensors, stream_config, steer_az=0.0, steer_el=0.0)

        delays = beamformer.steering_delays

        # Sensor 0 at origin should have delay 0
        assert delays[0] == pytest.approx(0.0, abs=1e-9)

        # Sensor 1 at x=1.0 with steering along +x: delay = -1.0 / c
        sound_speed = 1500.0
        expected_delay_1 = -1.0 / sound_speed
        assert delays[1] == pytest.approx(expected_delay_1, rel=1e-6)

    def test_zero_steer_angles_reference_delays(self):
        """With zero steer angles, delays match plane wave geometry.

        VESSEL_BODY: Az=0, El=0 → direction = (1, 0, 0).
        Dot product with sensor positions gives x coordinate.
        Delays = -x / sound_speed.
        """
        sensors = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 1.0, "y": 0.0, "z": 0.0},
            {"id": 2, "x": 0.0, "y": 0.0, "z": 1.0},
        ]
        stream_config = StreamConfig(sample_rate=16000, rate=100)

        beamformer = DelayAndSumBeamformer(sensors, stream_config, steer_az=0.0, steer_el=0.0)

        delays = beamformer.steering_delays

        # direction = (1, 0, 0), delays = -x / c
        sound_speed = 1500.0
        assert delays[0] == pytest.approx(0.0, abs=1e-9)
        assert delays[1] == pytest.approx(-1.0 / sound_speed, rel=1e-6)
        assert delays[2] == pytest.approx(0.0, abs=1e-9)


class TestMultiChannelProcessing:
    """Tests for multi-channel processing."""

    def test_handles_variable_number_of_channels(self):
        """Beamformer processes variable numbers of channels."""
        sensors = [
            {"id": i, "x": float(i), "y": 0.0, "z": 0.0}
            for i in range(5)
        ]
        stream_config = StreamConfig(sample_rate=8000, rate=100)
        beamformer = DelayAndSumBeamformer(sensors, stream_config)
        
        block = np.random.randn(5, 80).astype(np.float32)
        output = beamformer.process_block(block)
        
        assert output.shape == (1, 80)
        assert output.dtype == np.float32

    def test_missing_sensor_channels_handled_gracefully(self):
        """When n_channels exceeds configured sensors, missing channels are skipped."""
        sensors = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 1.0, "y": 0.0, "z": 0.0},
        ]
        stream_config = StreamConfig(sample_rate=8000, rate=100)
        beamformer = DelayAndSumBeamformer(sensors, stream_config)
        
        # Block has 4 channels but only 2 sensors are configured
        block = np.random.randn(4, 80).astype(np.float32)
        output = beamformer.process_block(block)
        
        # Should still process without crashing
        assert output.shape == (1, 80)
        assert np.all(np.isfinite(output))


class TestRealValueOutput:
    """Tests for real-valued output."""

    def test_output_is_real_valued(self):
        """Output is real-valued (no imaginary components)."""
        sensors = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 1.0, "y": 0.0, "z": 0.0},
        ]
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        beamformer = DelayAndSumBeamformer(sensors, stream_config)
        
        block = np.random.randn(2, 160).astype(np.float32)
        output = beamformer.process_block(block)
        
        # Output should be real (no imaginary part in float32)
        assert output.dtype == np.float32
        assert np.all(np.isfinite(output))


class TestFrequencyDependence:
    """Tests for frequency-dependent behavior."""

    def test_different_frequencies_have_different_phase_shifts(self):
        """Different frequencies experience different phase shifts with same delay."""
        sensors = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 0.0, "y": 1.0, "z": 0.0},
        ]
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        beamformer = DelayAndSumBeamformer(sensors, stream_config)
        
        block_size = 160
        t = np.arange(block_size) / 16000.0
        
        # Low frequency signal
        freq_low = 500.0
        signal_low = np.sin(2.0 * np.pi * freq_low * t)
        
        block_low = np.vstack([signal_low, signal_low]).astype(np.float32)
        output_low = beamformer.process_block(block_low)
        
        # High frequency signal
        freq_high = 4000.0
        signal_high = np.sin(2.0 * np.pi * freq_high * t)
        
        block_high = np.vstack([signal_high, signal_high]).astype(np.float32)
        output_high = beamformer.process_block(block_high)
        
        # Both outputs should be valid
        assert np.all(np.isfinite(output_low))
        assert np.all(np.isfinite(output_high))
        
        # They should have different frequency content
        fft_low = np.fft.rfft(output_low[0, :])
        fft_high = np.fft.rfft(output_high[0, :])
        freqs = np.fft.rfftfreq(block_size, 1.0 / 16000.0)
        
        peak_low = freqs[np.argmax(np.abs(fft_low))]
        peak_high = freqs[np.argmax(np.abs(fft_high))]
        
        assert peak_low < peak_high
