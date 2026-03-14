"""Spectrum analysis for audio blocks."""

import logging
import numpy as np
from common.stream import StreamConfig

logger = logging.getLogger(__name__)


class SpectrumAnalyzer:
    """Computes power spectrum from audio blocks.
    
    Performs FFT on audio data and computes power spectral density in dB.
    Outputs positive frequencies only.
    
    Attributes:
        stream_config: StreamConfig instance with sample_rate and block_size.
    """

    def __init__(self, stream_config: StreamConfig) -> None:
        """Initialize SpectrumAnalyzer.
        
        Args:
            stream_config: StreamConfig instance.
        """
        self.stream_config = stream_config
        logger.debug(f"SpectrumAnalyzer initialized: "
                    f"sample_rate={stream_config.sample_rate}, "
                    f"block_size={stream_config.block_size}")

    def analyze_block(self, block: np.ndarray) -> list[dict]:
        """Analyze a block and return spectrum records.
        
        Computes FFT of the first channel, converts to power spectral
        density in dB, and returns spectrum records for positive frequencies.
        
        Args:
            block: Shape (n_channels, block_size) float32 array.
            
        Returns:
            List of spectrum records with keys:
                - type: "spectrum"
                - freq: Frequency in Hz (float)
                - power_db: Power in dB (float)
        """
        n_channels, block_size = block.shape
        sample_rate = self.stream_config.sample_rate
        
        # Use first channel only
        signal = block[0, :].astype(np.float64)
        
        # Compute FFT
        X = np.fft.rfft(signal)
        
        # Compute power spectral density in dB
        # PSD = 10 * log10(|X|^2 / block_size)
        power = np.abs(X) ** 2 / block_size
        power_db = 10.0 * np.log10(power + 1e-20)  # Add epsilon to avoid log(0)
        
        # Compute frequency bins (positive frequencies only)
        freqs = np.fft.rfftfreq(block_size, 1.0 / sample_rate)
        
        # Generate records
        records = []
        for freq, pdb in zip(freqs, power_db):
            records.append({
                "type": "spectrum",
                "freq": float(freq),
                "power_db": float(pdb),
            })
        
        return records
