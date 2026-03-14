"""Unit tests for WavWriter."""

import wave
import numpy as np
import pytest
from pathlib import Path
from ec_to_wav.writer import WavWriter
from common.stream import StreamConfig


@pytest.fixture
def stream_config():
    """Create a basic StreamConfig for testing."""
    return StreamConfig(sample_rate=16000, rate=4, format="float32")


@pytest.fixture
def output_file(tmp_path):
    """Create a temporary output file path."""
    return str(tmp_path / "test_output.wav")


class TestWavWriterCreation:
    """Test WavWriter initialization and file creation."""

    def test_wav_writer_creates_file(self, output_file, stream_config):
        """Test that WavWriter creates a valid WAV file."""
        n_channels = 2
        writer = WavWriter(output_file, stream_config, n_channels)
        writer.close()
        
        # Verify file exists
        assert Path(output_file).exists()
        
        # Verify it's a valid WAV file
        with wave.open(output_file, 'rb') as wav_file:
            assert wav_file.getnchannels() == n_channels
            assert wav_file.getsampwidth() == 4  # float32
            assert wav_file.getframerate() == stream_config.sample_rate


class TestWavWriterWriteBlock:
    """Test WavWriter write_block method."""

    def test_write_block_single_channel(self, output_file, stream_config):
        """Test writing a block with a single channel."""
        n_channels = 1
        block_size = stream_config.block_size
        writer = WavWriter(output_file, stream_config, n_channels)
        
        # Create test block
        block = np.array([[0.1, 0.2, 0.3, 0.4]], dtype=np.float32)
        writer.write_block(block)
        writer.close()
        
        # Verify written data
        with wave.open(output_file, 'rb') as wav_file:
            data = wav_file.readframes(wav_file.getnframes())
            written = np.frombuffer(data, dtype=np.float32)
            np.testing.assert_array_almost_equal(written, [0.1, 0.2, 0.3, 0.4])

    def test_write_block_multichannel_interleaving(self, output_file, stream_config):
        """Test that write_block correctly interleaves multiple channels."""
        n_channels = 2
        block_size = 4
        writer = WavWriter(output_file, stream_config, n_channels)
        
        # Create test block: channel 0: [1, 2, 3, 4], channel 1: [5, 6, 7, 8]
        block = np.array([
            [1.0, 2.0, 3.0, 4.0],
            [5.0, 6.0, 7.0, 8.0]
        ], dtype=np.float32)
        writer.write_block(block)
        writer.close()
        
        # Verify interleaving: should be [1, 5, 2, 6, 3, 7, 4, 8]
        with wave.open(output_file, 'rb') as wav_file:
            data = wav_file.readframes(wav_file.getnframes())
            written = np.frombuffer(data, dtype=np.float32)
            expected = np.array([1.0, 5.0, 2.0, 6.0, 3.0, 7.0, 4.0, 8.0])
            np.testing.assert_array_almost_equal(written, expected)

    def test_write_block_three_channels(self, output_file, stream_config):
        """Test interleaving with three channels."""
        n_channels = 3
        block_size = 2
        writer = WavWriter(output_file, stream_config, n_channels)
        
        # Create test block
        block = np.array([
            [1.0, 2.0],
            [3.0, 4.0],
            [5.0, 6.0]
        ], dtype=np.float32)
        writer.write_block(block)
        writer.close()
        
        # Verify interleaving: should be [1, 3, 5, 2, 4, 6]
        with wave.open(output_file, 'rb') as wav_file:
            data = wav_file.readframes(wav_file.getnframes())
            written = np.frombuffer(data, dtype=np.float32)
            expected = np.array([1.0, 3.0, 5.0, 2.0, 4.0, 6.0])
            np.testing.assert_array_almost_equal(written, expected)

    def test_write_multiple_blocks(self, output_file, stream_config):
        """Test writing multiple blocks sequentially."""
        n_channels = 2
        block_size = 2
        writer = WavWriter(output_file, stream_config, n_channels)
        
        block1 = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        block2 = np.array([[5.0, 6.0], [7.0, 8.0]], dtype=np.float32)
        
        writer.write_block(block1)
        writer.write_block(block2)
        writer.close()
        
        # Verify all data
        with wave.open(output_file, 'rb') as wav_file:
            data = wav_file.readframes(wav_file.getnframes())
            written = np.frombuffer(data, dtype=np.float32)
            # Interleaved: [1, 3, 2, 4, 5, 7, 6, 8]
            expected = np.array([1.0, 3.0, 2.0, 4.0, 5.0, 7.0, 6.0, 8.0])
            np.testing.assert_array_almost_equal(written, expected)


class TestWavWriterValidation:
    """Test WavWriter validation."""

    def test_write_block_channel_count_mismatch(self, output_file, stream_config):
        """Test that write_block raises ValueError for mismatched channel count."""
        n_channels = 2
        writer = WavWriter(output_file, stream_config, n_channels)
        
        # Try to write block with wrong number of channels
        block = np.array([[1.0, 2.0]], dtype=np.float32)  # Only 1 channel
        
        with pytest.raises(ValueError, match="Block has 1 channels, expected 2"):
            writer.write_block(block)
        
        writer.close()


class TestWavWriterClose:
    """Test WavWriter close method."""

    def test_close_finalizes_wav_file(self, output_file, stream_config):
        """Test that close properly finalizes the WAV file."""
        n_channels = 1
        writer = WavWriter(output_file, stream_config, n_channels)
        
        block = np.array([[1.0, 2.0]], dtype=np.float32)
        writer.write_block(block)
        writer.close()
        
        # Verify file can be read and has correct properties
        with wave.open(output_file, 'rb') as wav_file:
            assert wav_file.getnframes() == 2
            assert wav_file.getnchannels() == 1

    def test_close_twice_safe(self, output_file, stream_config):
        """Test that closing twice doesn't cause issues."""
        writer = WavWriter(output_file, stream_config, 1)
        writer.close()
        # Should not raise
        writer.close()
