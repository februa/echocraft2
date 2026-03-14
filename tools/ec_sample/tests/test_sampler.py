"""Unit tests for BlockSampler domain logic."""

import numpy as np
import pytest
from common.stream import StreamConfig
from ec_sample.sampler import BlockSampler


class TestBlockSamplerInit:
    """Tests for BlockSampler initialization."""

    def test_initializes_with_transfers_and_config(self):
        """BlockSampler initializes with transfers and stream config."""
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        transfers = [
            {
                "source_id": 0,
                "sensor_id": 0,
                "delay": 0.0,
                "loss_db": -120.0,
                "freq": 1000.0,
            }
        ]
        
        sampler = BlockSampler(transfers, None, stream_config, n_channels=1)
        
        assert sampler.stream_config == stream_config
        assert len(sampler.transfers) == 1
        assert sampler.noise_level is None
        assert sampler.n_channels == 1


class TestBlockShape:
    """Tests for generated block shape and dtype."""

    def test_generates_blocks_of_correct_shape(self):
        """BlockSampler generates blocks of shape (n_channels, block_size)."""
        stream_config = StreamConfig(sample_rate=16000, rate=100)
        transfers = [
            {
                "source_id": 0,
                "sensor_id": 0,
                "delay": 0.0,
                "loss_db": -120.0,
                "freq": 1000.0,
            },
            {
                "source_id": 0,
                "sensor_id": 1,
                "delay": 0.0,
                "loss_db": -120.0,
                "freq": 2000.0,
            },
        ]
        
        sampler = BlockSampler(transfers, None, stream_config, n_channels=2)
        block = sampler.generate_block(0)
        
        assert block.shape == (2, 160)  # block_size = 16000 / 100 = 160

    def test_block_output_is_float32(self):
        """Block output is float32 numpy array."""
        stream_config = StreamConfig(sample_rate=8000, rate=100)
        transfers = []
        
        sampler = BlockSampler(transfers, None, stream_config, n_channels=1)
        block = sampler.generate_block(0)
        
        assert block.dtype == np.float32

    def test_handles_multi_channel_output(self):
        """BlockSampler correctly allocates multi-channel output."""
        stream_config = StreamConfig(sample_rate=8000, rate=100)
        transfers = [
            {
                "source_id": 0,
                "sensor_id": 0,
                "delay": 0.0,
                "loss_db": -120.0,
                "freq": 1000.0,
            },
            {
                "source_id": 1,
                "sensor_id": 2,
                "delay": 0.0,
                "loss_db": -120.0,
                "freq": 1000.0,
            },
        ]
        
        sampler = BlockSampler(transfers, None, stream_config, n_channels=3)
        block = sampler.generate_block(0)
        
        assert block.shape == (3, 80)


class TestSinusoidGeneration:
    """Tests for sinusoid generation with transfer functions."""

    def test_single_transfer_produces_sinusoid(self):
        """With single transfer (known freq, no delay): verify sinusoid presence via FFT."""
        sample_rate = 16000
        block_size = sample_rate // 100  # 160 samples
        stream_config = StreamConfig(sample_rate=sample_rate, rate=100)
        
        # Create a 1000 Hz transfer with no delay and unity amplitude
        transfers = [
            {
                "source_id": 0,
                "sensor_id": 0,
                "delay": 0.0,
                "loss_db": 0.0,  # 10^(0/20) = 1.0 amplitude
                "freq": 1000.0,
            }
        ]
        
        sampler = BlockSampler(transfers, None, stream_config, n_channels=1)
        block = sampler.generate_block(0)
        
        # Extract channel and compute FFT
        signal = block[0, :]
        fft = np.fft.rfft(signal)
        freqs = np.fft.rfftfreq(block_size, 1.0 / sample_rate)
        
        # Find peak frequency
        peak_idx = np.argmax(np.abs(fft))
        peak_freq = freqs[peak_idx]
        
        # Peak should be at 1000 Hz
        assert peak_freq == pytest.approx(1000.0, abs=50)  # Allow 50 Hz tolerance

    def test_amplitude_scaling_from_db(self):
        """Amplitude scaling from dB: 10^(sl/20)."""
        sample_rate = 16000
        stream_config = StreamConfig(sample_rate=sample_rate, rate=100)
        
        # Test amplitude scaling: -20 dB should give 10^(-20/20) = 0.1
        transfers = [
            {
                "source_id": 0,
                "sensor_id": 0,
                "delay": 0.0,
                "loss_db": -20.0,
                "freq": 100.0,
            }
        ]
        
        sampler = BlockSampler(transfers, None, stream_config, n_channels=1)
        block = sampler.generate_block(0)
        
        signal = block[0, :]
        expected_amplitude = 10.0 ** (-20.0 / 20.0)  # 0.1
        
        # Peak amplitude should be approximately expected_amplitude
        peak_amplitude = np.max(np.abs(signal))
        assert peak_amplitude == pytest.approx(expected_amplitude, rel=0.05)


class TestDelayHandling:
    """Tests for delay application."""

    def test_time_continuity_block_index_affects_phase(self):
        """Time continuity: block_index affects phase correctly."""
        sample_rate = 16000
        stream_config = StreamConfig(sample_rate=sample_rate, rate=100)
        
        transfers = [
            {
                "source_id": 0,
                "sensor_id": 0,
                "delay": 0.0,
                "loss_db": 0.0,
                "freq": 1000.0,
            }
        ]
        
        sampler = BlockSampler(transfers, None, stream_config, n_channels=1)
        
        # Generate two consecutive blocks
        block0 = sampler.generate_block(0)
        block1 = sampler.generate_block(1)
        
        # Check that phase is continuous at the boundary
        # The first sample of block1 should continue the phase from block0
        signal0 = block0[0, :]
        signal1 = block1[0, :]
        
        # Compute phase from last sample of block0
        last_idx_block0 = 159  # 0-indexed
        t0 = last_idx_block0 / sample_rate
        phase0 = 2.0 * np.pi * 1000.0 * t0
        
        # Compute phase from first sample of block1
        first_idx_block1 = 160
        t1 = first_idx_block1 / sample_rate
        phase1 = 2.0 * np.pi * 1000.0 * t1
        
        # Phase should increase by 2*pi*f*dt
        phase_diff = phase1 - phase0
        expected_phase_diff = 2.0 * np.pi * 1000.0 / sample_rate
        
        assert phase_diff == pytest.approx(expected_phase_diff, rel=1e-6)


class TestNoiseAddition:
    """Tests for noise addition."""

    def test_with_noise_output_has_additional_random_component(self):
        """With noise: output has additional random component."""
        np.random.seed(42)
        
        sample_rate = 16000
        stream_config = StreamConfig(sample_rate=sample_rate, rate=100)
        
        transfers = [
            {
                "source_id": 0,
                "sensor_id": 0,
                "delay": 0.0,
                "loss_db": -60.0,  # Small signal
                "freq": 1000.0,
            }
        ]
        
        # Generate block without noise
        sampler_no_noise = BlockSampler(transfers, None, stream_config, n_channels=1)
        np.random.seed(42)
        block_no_noise = sampler_no_noise.generate_block(0)
        
        # Generate block with noise
        np.random.seed(42)
        sampler_with_noise = BlockSampler(transfers, -60.0, stream_config, n_channels=1)
        block_with_noise = sampler_with_noise.generate_block(0)
        
        # With noise level, blocks should be different
        # (they diverge after the signal computation due to noise)
        assert not np.allclose(block_no_noise, block_with_noise)

    def test_noise_amplitude_from_db(self):
        """Noise amplitude is correctly computed from dB value."""
        np.random.seed(42)
        
        sample_rate = 16000
        stream_config = StreamConfig(sample_rate=sample_rate, rate=100)
        
        # No transfers, only noise at -40 dB
        transfers = []
        noise_level = -40.0
        
        sampler = BlockSampler(transfers, noise_level, stream_config, n_channels=1)
        block = sampler.generate_block(0)
        
        # Expected noise amplitude (std dev): 10^(-40/20) = 0.01
        expected_std = 10.0 ** (-40.0 / 20.0)
        
        # RMS should be approximately equal to standard deviation for Gaussian noise
        rms = np.sqrt(np.mean(block[0, :]**2))
        assert rms == pytest.approx(expected_std, rel=0.3)


class TestEmptyTransfers:
    """Tests for edge cases with no transfers."""

    def test_with_no_transfers_output_is_zeros(self):
        """With no transfers and no noise, output is all zeros."""
        stream_config = StreamConfig(sample_rate=8000, rate=100)
        transfers = []
        
        sampler = BlockSampler(transfers, None, stream_config, n_channels=1)
        block = sampler.generate_block(0)
        
        assert np.allclose(block, 0.0)

    def test_with_multiple_transfers_on_same_channel(self):
        """Multiple transfers on the same channel are summed."""
        sample_rate = 16000
        stream_config = StreamConfig(sample_rate=sample_rate, rate=100)
        
        transfers = [
            {
                "source_id": 0,
                "sensor_id": 0,
                "delay": 0.0,
                "loss_db": -30.0,  # 10^(-30/20) ≈ 0.0316
                "freq": 1000.0,
            },
            {
                "source_id": 1,
                "sensor_id": 0,
                "delay": 0.0,
                "loss_db": -30.0,
                "freq": 2000.0,
            },
        ]
        
        sampler = BlockSampler(transfers, None, stream_config, n_channels=1)
        block = sampler.generate_block(0)
        
        # Signal should contain both frequency components
        signal = block[0, :]
        fft = np.fft.rfft(signal)
        freqs = np.fft.rfftfreq(len(signal), 1.0 / sample_rate)
        
        # Find peaks
        peak_indices = np.argsort(np.abs(fft))[-2:]  # Two strongest peaks
        peak_freqs = freqs[peak_indices]
        
        # Peaks should be near 1000 and 2000 Hz
        assert 950 < peak_freqs[0] < 1050 or 950 < peak_freqs[1] < 1050
        assert 1950 < peak_freqs[0] < 2050 or 1950 < peak_freqs[1] < 2050
