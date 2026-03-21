"""Unit tests for SpectrumAnalyzer."""

import numpy as np
import pytest
from eca_spectrum.spectrum import SpectrumAnalyzer
from common.stream import StreamConfig


@pytest.fixture
def stream_config():
    """Create a StreamConfig for testing."""
    return StreamConfig(sample_rate=16000, rate=4, format="float32")


@pytest.fixture
def analyzer(stream_config):
    """Create a SpectrumAnalyzer instance."""
    return SpectrumAnalyzer(stream_config)


class TestSpectrumAnalyzerBasics:
    """Test basic SpectrumAnalyzer functionality."""

    def test_analyze_block_returns_list_of_dicts(self, analyzer, stream_config):
        """Test that analyze_block returns a list of dicts with spectrum type."""
        block_size = stream_config.block_size
        block = np.zeros((1, block_size), dtype=np.float32)
        
        records = analyzer.analyze_block(block)
        
        assert isinstance(records, list)
        assert len(records) > 0
        assert all(isinstance(r, dict) for r in records)
        assert all(r.get("type") == "spectrum" for r in records)

    def test_analyze_block_has_required_keys(self, analyzer, stream_config):
        """Test that spectrum records have required keys."""
        block_size = stream_config.block_size
        block = np.ones((1, block_size), dtype=np.float32)
        
        records = analyzer.analyze_block(block)
        
        for record in records:
            assert "type" in record
            assert "freq" in record
            assert "power_db" in record

    def test_analyze_block_frequency_bins_count(self, analyzer, stream_config):
        """Test that number of frequency bins equals block_size//2 + 1."""
        block_size = stream_config.block_size
        block = np.zeros((1, block_size), dtype=np.float32)
        
        records = analyzer.analyze_block(block)
        
        expected_bins = block_size // 2 + 1
        assert len(records) == expected_bins

    def test_analyze_block_uses_first_channel_only(self, analyzer, stream_config):
        """Test that analyze_block uses first channel even with multi-channel input."""
        block_size = stream_config.block_size
        # Create multi-channel block: first channel all 1s, second all 2s
        block = np.array([
            np.ones(block_size, dtype=np.float32),
            2.0 * np.ones(block_size, dtype=np.float32)
        ], dtype=np.float32)
        
        records = analyzer.analyze_block(block)
        
        # Analyze only first channel
        signal = np.ones(block_size, dtype=np.float32)
        X = np.fft.rfft(signal)
        expected_power = np.abs(X) ** 2 / block_size
        expected_power_db = 10.0 * np.log10(expected_power + 1e-20)
        
        # Check DC component matches
        assert pytest.approx(records[0]["power_db"], abs=0.1) == expected_power_db[0]


class TestSpectrumAnalyzerSinusoid:
    """Test SpectrumAnalyzer with known sinusoid inputs."""

    def test_known_sinusoid_peak_at_correct_frequency(self, stream_config):
        """Test that a known sinusoid has peak at the correct frequency bin."""
        block_size = stream_config.block_size
        sample_rate = stream_config.sample_rate
        
        # Create sinusoid at 1000 Hz
        target_freq = 1000.0
        t = np.arange(block_size) / sample_rate
        signal = np.sin(2 * np.pi * target_freq * t).astype(np.float32)
        
        block = np.array([signal], dtype=np.float32)
        
        analyzer = SpectrumAnalyzer(stream_config)
        records = analyzer.analyze_block(block)
        
        # Find peak (excluding DC)
        non_dc_records = [r for r in records if r["freq"] > 0]
        peak_record = max(non_dc_records, key=lambda r: r["power_db"])
        
        # Peak should be near 1000 Hz
        assert pytest.approx(peak_record["freq"], abs=10.0) == target_freq

    def test_silence_has_very_low_power(self, analyzer, stream_config):
        """Test that silence (zeros) has very low power."""
        block_size = stream_config.block_size
        block = np.zeros((1, block_size), dtype=np.float32)
        
        records = analyzer.analyze_block(block)
        
        # All power should be very low (near -200 dB or lower)
        for record in records:
            assert record["power_db"] < -100

    def test_dc_component_present_at_zero_frequency(self, analyzer, stream_config):
        """Test that DC component (frequency 0) is present in output."""
        block_size = stream_config.block_size
        # Create constant signal (DC)
        block = np.ones((1, block_size), dtype=np.float32)
        
        records = analyzer.analyze_block(block)
        
        # First record should have freq=0
        assert records[0]["freq"] == pytest.approx(0.0, abs=1e-6)


class TestSpectrumAnalyzerPowerCalculation:
    """Test power calculation in SpectrumAnalyzer."""

    def test_power_calculation_formula(self, analyzer, stream_config):
        """Test that power is calculated correctly with window and coherent gain correction."""
        block_size = stream_config.block_size
        # Simple sinusoid
        amplitude = 1.0
        t = np.arange(block_size) / stream_config.sample_rate
        signal = amplitude * np.sin(2 * np.pi * 100 * t).astype(np.float32)

        block = np.array([signal], dtype=np.float32)
        records = analyzer.analyze_block(block)

        # Manually calculate expected power at DC with window + coherent gain
        sig64 = signal.astype(np.float64)
        window = np.hanning(block_size)
        coherent_gain = np.mean(window)
        windowed = sig64 * window / coherent_gain
        X = np.fft.rfft(windowed)
        power = np.abs(X[0]) ** 2 / block_size
        expected_power_db = 10.0 * np.log10(power + 1e-20)

        # DC component should match
        assert pytest.approx(records[0]["power_db"], abs=0.01) == expected_power_db

    def test_epsilon_avoids_log_zero(self, analyzer, stream_config):
        """Test that epsilon (1e-20) prevents log(0) for very small powers."""
        block_size = stream_config.block_size
        block = np.zeros((1, block_size), dtype=np.float32)
        
        records = analyzer.analyze_block(block)
        
        # Should not have -inf, should have large negative values
        for record in records:
            assert np.isfinite(record["power_db"])
            assert record["power_db"] < -100


class TestSpectrumAnalyzerWindow:
    """Test window function support in SpectrumAnalyzer."""

    def test_rectangular_window_no_modification(self, stream_config):
        """Test that rectangular window produces same result as raw FFT."""
        analyzer = SpectrumAnalyzer(stream_config, window="rectangular")
        block_size = stream_config.block_size
        t = np.arange(block_size) / stream_config.sample_rate
        signal = np.sin(2 * np.pi * 100 * t).astype(np.float32)
        block = np.array([signal], dtype=np.float32)

        records = analyzer.analyze_block(block)

        # Manual raw FFT (rectangular = no window, coherent_gain = 1.0)
        X = np.fft.rfft(signal.astype(np.float64))
        power = np.abs(X) ** 2 / block_size
        expected_db = 10.0 * np.log10(power + 1e-20)

        for i, record in enumerate(records):
            assert pytest.approx(record["power_db"], abs=0.01) == expected_db[i]

    def test_invalid_window_raises(self, stream_config):
        """Test that invalid window name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown window"):
            SpectrumAnalyzer(stream_config, window="invalid_window")

    def test_hanning_reduces_sidelobes(self, stream_config):
        """Test that hanning window reduces spectral leakage vs rectangular."""
        block_size = stream_config.block_size
        t = np.arange(block_size) / stream_config.sample_rate
        # Frequency NOT on an FFT bin to trigger spectral leakage
        freq = 100.5 * stream_config.rate
        signal = np.sin(2 * np.pi * freq * t).astype(np.float32)
        block = np.array([signal], dtype=np.float32)

        rect_analyzer = SpectrumAnalyzer(stream_config, window="rectangular")
        hann_analyzer = SpectrumAnalyzer(stream_config, window="hanning")

        rect_records = rect_analyzer.analyze_block(block)
        hann_records = hann_analyzer.analyze_block(block)

        # Find the peak bin index
        rect_powers = [r["power_db"] for r in rect_records]
        peak_idx = np.argmax(rect_powers)

        # Compare far-from-peak sidelobe levels (e.g. 50 bins away)
        far_idx = min(peak_idx + 50, len(rect_records) - 1)
        assert hann_records[far_idx]["power_db"] < rect_records[far_idx]["power_db"]

    def test_all_windows_produce_output(self, stream_config):
        """Test that all supported windows produce valid output."""
        block_size = stream_config.block_size
        block = np.random.randn(1, block_size).astype(np.float32)

        for window_name in ["rectangular", "hanning", "hamming", "blackman"]:
            analyzer = SpectrumAnalyzer(stream_config, window=window_name)
            records = analyzer.analyze_block(block)
            assert len(records) == block_size // 2 + 1
            for r in records:
                assert np.isfinite(r["power_db"])


class TestSpectrumAnalyzerFrequencies:
    """Test frequency computation in SpectrumAnalyzer."""

    def test_frequencies_ordered_ascending(self, analyzer, stream_config):
        """Test that frequencies are in ascending order."""
        block_size = stream_config.block_size
        block = np.ones((1, block_size), dtype=np.float32)
        
        records = analyzer.analyze_block(block)
        
        freqs = [r["freq"] for r in records]
        assert freqs == sorted(freqs)

    def test_frequency_values_correct(self, analyzer, stream_config):
        """Test that frequency values match rfftfreq calculation."""
        block_size = stream_config.block_size
        sample_rate = stream_config.sample_rate
        
        block = np.ones((1, block_size), dtype=np.float32)
        records = analyzer.analyze_block(block)
        
        expected_freqs = np.fft.rfftfreq(block_size, 1.0 / sample_rate)
        
        for i, record in enumerate(records):
            assert pytest.approx(record["freq"], abs=0.1) == expected_freqs[i]

    def test_nyquist_frequency_present(self, analyzer, stream_config):
        """Test that Nyquist frequency is present in output."""
        block_size = stream_config.block_size
        sample_rate = stream_config.sample_rate
        nyquist = sample_rate / 2
        
        block = np.zeros((1, block_size), dtype=np.float32)
        records = analyzer.analyze_block(block)
        
        # Last record should be at or near Nyquist frequency
        assert pytest.approx(records[-1]["freq"], abs=1.0) == nyquist
