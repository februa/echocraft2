"""Block sampler for generating synthetic audio signals from transfer functions."""

import logging
import numpy as np
from common.stream import StreamConfig

logger = logging.getLogger(__name__)


class BlockSampler:
    """Generates audio blocks from transfer function and noise parameters.
    
    Simulates narrowband signals with specified frequencies, amplitudes, and delays,
    plus optional Gaussian noise. Outputs blocks in channel-major order.
    
    Attributes:
        transfers: List of transfer function dictionaries (source_id, sensor_id, delay, loss_db, freq).
        noise_level: Noise level in dB, or None for no noise.
        stream_config: StreamConfig object with sample_rate and block_size.
        n_channels: Total number of channels (max sensor_id + 1).
    """

    def __init__(
        self,
        transfers: list[dict],
        noise_level: float | None,
        stream_config: StreamConfig,
        n_channels: int,
    ) -> None:
        """Initialize BlockSampler.
        
        Args:
            transfers: List of transfer dicts with keys:
                - source_id: int, source identifier
                - sensor_id: int, sensor channel index
                - delay: float, delay in seconds
                - loss_db: float, amplitude loss in dB
                - freq: float, frequency in Hz
            noise_level: Noise level in dB, or None for no noise.
            stream_config: StreamConfig instance with sample_rate and block_size.
            n_channels: Number of channels (max sensor_id + 1).
        """
        self.transfers = transfers
        self.noise_level = noise_level
        self.stream_config = stream_config
        self.n_channels = n_channels

    def generate_block(self, block_index: int) -> np.ndarray:
        """Generate a single audio block.
        
        Synthesizes a multi-channel audio block by summing sinusoidal components
        from all transfers, applying delays and loss factors, then adding
        uncorrelated Gaussian noise if specified.
        
        Args:
            block_index: Block index (0-based) for computing time samples.
            
        Returns:
            Shape (n_channels, block_size) float32 numpy array with synthesized
            signals in channel-major order.
        """
        block_size = self.stream_config.block_size
        sample_rate = self.stream_config.sample_rate
        
        # Initialize output array
        block = np.zeros((self.n_channels, block_size), dtype=np.float32)
        
        # Compute sample times for this block
        sample_indices = block_index * block_size + np.arange(block_size)
        t = sample_indices / sample_rate
        
        # Accumulate transfer function contributions
        for transfer in self.transfers:
            sensor_id = transfer["sensor_id"]
            freq = transfer["freq"]
            delay = transfer["delay"]
            loss_db = transfer["loss_db"]

            # Compute peak amplitude from level in dB.
            # Level is defined as 10*log10(mean_square), i.e. RMS-based.
            # For sinusoid: mean(A*sin)^2 = A^2/2, so to get
            # 10*log10(A^2/2) = loss_db, we need A = sqrt(2) * 10^(loss_db/20).
            amplitude = np.sqrt(2.0) * 10.0 ** (loss_db / 20.0)

            # Generate sinusoid: sin(2*pi*f*(t - delay))
            signal = amplitude * np.sin(2.0 * np.pi * freq * (t - delay))
            
            # Add to the appropriate channel
            block[sensor_id, :] += signal.astype(np.float32)
        
        # Add uncorrelated Gaussian noise if specified
        if self.noise_level is not None:
            noise_amplitude = 10.0 ** (self.noise_level / 20.0)
            noise = np.random.normal(0, noise_amplitude, (self.n_channels, block_size))
            block += noise.astype(np.float32)
        
        return block
