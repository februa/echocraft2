"""WAV file writer for binary audio blocks."""

import logging
import wave
import numpy as np
from common.stream import StreamConfig

logger = logging.getLogger(__name__)


class WavWriter:
    """Writes float32 audio blocks to WAV file.
    
    Converts channel-major binary audio blocks to WAV format with
    interleaved samples. Supports multi-channel audio.
    
    Attributes:
        output_path: Path to output WAV file.
        stream_config: StreamConfig instance.
        n_channels: Number of audio channels.
        wav_file: Opened wave.Wave_write object.
    """

    def __init__(
        self,
        output_path: str,
        stream_config: StreamConfig,
        n_channels: int,
    ) -> None:
        """Initialize WavWriter.
        
        Args:
            output_path: Path to output WAV file.
            stream_config: StreamConfig instance with sample_rate.
            n_channels: Number of audio channels.
        """
        self.output_path = output_path
        self.stream_config = stream_config
        self.n_channels = n_channels
        
        # Open WAV file for writing
        self.wav_file = wave.open(output_path, 'wb')
        self.wav_file.setnchannels(n_channels)
        self.wav_file.setsampwidth(4)  # float32 = 4 bytes
        self.wav_file.setframerate(stream_config.sample_rate)
        
        logger.debug(f"Opened WAV file: {output_path}, "
                    f"channels={n_channels}, "
                    f"sample_rate={stream_config.sample_rate}")

    def write_block(self, block: np.ndarray) -> None:
        """Write audio block to WAV file.
        
        Converts from channel-major (n_channels, block_size) format to
        interleaved format expected by WAV file.
        
        Args:
            block: Shape (n_channels, block_size) float32 array.
        """
        # Ensure correct shape
        if block.shape[0] != self.n_channels:
            raise ValueError(
                f"Block has {block.shape[0]} channels, "
                f"expected {self.n_channels}"
            )
        
        # Interleave: transpose to (block_size, n_channels) then flatten
        interleaved = block.T.flatten()
        
        # Write as float32 bytes
        self.wav_file.writeframes(interleaved.astype(np.float32).tobytes())

    def close(self) -> None:
        """Close the WAV file.
        
        Finalizes the WAV header and closes the file.
        """
        self.wav_file.close()
        logger.debug(f"Closed WAV file: {self.output_path}")
