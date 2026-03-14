"""Bearing level analysis via beam sweeping."""

import logging
import numpy as np
from common.stream import StreamConfig

logger = logging.getLogger(__name__)


class BearingLevelAnalyzer:
    """Computes bearing-level by sweeping DAS beamformer across azimuths.
    
    For each block, sweeps across specified azimuth range and computes
    output power at each bearing angle.
    """

    def __init__(
        self,
        sensors: list[dict],
        stream_config: StreamConfig,
        az_start: float = 0.0,
        az_end: float = 180.0,
        az_step: float = 1.0,
        steer_el: float = 0.0,
    ) -> None:
        self.sensors = sensors
        self.stream_config = stream_config
        self.az_start = az_start
        self.az_end = az_end
        self.az_step = az_step
        self.steer_el = steer_el
        
        # Pre-compute azimuth list
        self.azimuths = np.arange(az_start, az_end + az_step / 2, az_step)
        
        # Pre-compute steering delays for all azimuths
        self._steering_delays = {}
        for az in self.azimuths:
            self._steering_delays[az] = self._compute_delays(az, steer_el)
        
        logger.debug(f"BearingLevelAnalyzer: {len(self.azimuths)} azimuths "
                     f"({az_start} to {az_end} step {az_step})")

    def _compute_delays(self, az_deg: float, el_deg: float) -> dict[int, float]:
        """Compute steering delays for a given direction."""
        az_rad = np.radians(az_deg)
        el_rad = np.radians(el_deg)
        
        direction = np.array([
            np.sin(az_rad) * np.cos(el_rad),
            np.cos(az_rad) * np.cos(el_rad),
            np.sin(el_rad),
        ])
        
        delays = {}
        sound_speed = 1500.0
        
        for sensor in self.sensors:
            position = np.array([sensor["x"], sensor["y"], sensor["z"]])
            delay = -np.dot(position, direction) / sound_speed
            delays[sensor["id"]] = delay
        
        return delays

    def _beamform_power(
        self, block: np.ndarray, delays: dict[int, float]
    ) -> float:
        """Compute beamformed output power for given delays."""
        n_channels, block_size = block.shape
        sample_rate = self.stream_config.sample_rate
        
        output = np.zeros(block_size, dtype=np.float64)
        
        for sensor_id, delay in delays.items():
            if sensor_id >= n_channels:
                continue
            
            channel_signal = block[sensor_id, :].astype(np.float64)
            X = np.fft.rfft(channel_signal)
            freqs = np.fft.rfftfreq(block_size, 1.0 / sample_rate)
            phase_shift = np.exp(-1j * 2.0 * np.pi * freqs * delay)
            delayed = np.fft.irfft(X * phase_shift, n=block_size)
            output += np.real(delayed)
        
        output /= n_channels
        
        # Compute power in dB
        power = np.mean(output ** 2)
        level_db = 10.0 * np.log10(power + 1e-20)
        
        return level_db

    def analyze_block(
        self, block: np.ndarray, block_index: int = 0, rate: int = 1
    ) -> list[dict]:
        """Analyze a block and return bearing records for all azimuths.
        
        Args:
            block: Shape (n_channels, block_size) float32 array.
            block_index: Current block index for time computation.
            rate: Processing rate in Hz for time computation.
            
        Returns:
            List of bearing records.
        """
        time = block_index / rate if rate > 0 else 0.0
        
        records = []
        for az in self.azimuths:
            delays = self._steering_delays[az]
            level_db = self._beamform_power(block, delays)
            records.append({
                "type": "bearing",
                "azimuth": float(az),
                "level_db": float(level_db),
                "time": float(time),
            })
        
        return records
