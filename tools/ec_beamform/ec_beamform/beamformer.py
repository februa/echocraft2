"""Delay-and-sum beamformer using fractional delay via frequency domain."""

import logging
import numpy as np
from common.stream import StreamConfig

logger = logging.getLogger(__name__)


class DelayAndSumBeamformer:
    """Delay-and-sum beamformer with steering direction control.
    
    Implements frequency-domain fractional delay using phase shift.
    Steers toward a specified direction (azimuth, elevation), computes
    steering delays for plane wave arrival, applies fractional delays,
    and sums across all channels.
    
    Attributes:
        sensors: List of sensor position dicts (x, y, z in meters).
        stream_config: StreamConfig instance.
        steer_az: Steering azimuth in degrees.
        steer_el: Steering elevation in degrees.
        steering_delays: Computed delays per sensor.
    """

    def __init__(
        self,
        sensors: list[dict],
        stream_config: StreamConfig,
        steer_az: float = 0.0,
        steer_el: float = 0.0,
    ) -> None:
        """Initialize DelayAndSumBeamformer.
        
        Args:
            sensors: List of sensor dicts with keys:
                - id: int, sensor identifier
                - x, y, z: float, position in meters
            stream_config: StreamConfig instance.
            steer_az: Steering azimuth in degrees (default 0).
            steer_el: Steering elevation in degrees (default 0).
        """
        self.sensors = sensors
        self.stream_config = stream_config
        self.steer_az = steer_az
        self.steer_el = steer_el
        
        # Compute steering delays
        self.steering_delays = self._compute_steering_delays()
        
        logger.debug(f"Beamformer initialized: steer_az={steer_az}, steer_el={steer_el}")
        logger.debug(f"Steering delays: {self.steering_delays}")

    def _compute_steering_delays(self) -> dict[int, float]:
        """Compute steering delays for plane wave arrival.
        
        Converts azimuth and elevation to direction vector, computes dot
        product with sensor positions, divides by sound speed (1500 m/s).
        
        Returns:
            Dictionary mapping sensor_id to delay in seconds.
        """
        # Convert degrees to radians
        az_rad = np.radians(self.steer_az)
        el_rad = np.radians(self.steer_el)
        
        # Compute direction vector (plane wave arrival direction)
        # VESSEL_BODY coordinate: x=bow, y=starboard, z=up
        # Azimuth: 0 = bow (+x), 90 = starboard (+y)
        # Elevation: 0 = horizontal, 90 = zenith (+z)
        direction = np.array([
            np.cos(az_rad) * np.cos(el_rad),
            np.sin(az_rad) * np.cos(el_rad),
            np.sin(el_rad),
        ])
        
        delays = {}
        sound_speed = 1500.0  # m/s
        
        for sensor in self.sensors:
            position = np.array([sensor["x"], sensor["y"], sensor["z"]])
            # Delay = -(position · direction) / sound_speed
            delay = -np.dot(position, direction) / sound_speed
            delays[sensor["id"]] = delay
        
        return delays

    def process_block(self, block: np.ndarray) -> np.ndarray:
        """Process a multi-channel block using delay-and-sum beamforming.
        
        Applies fractional delays to each channel via frequency-domain phase shift,
        then sums all channels to produce a single output beam.
        
        Args:
            block: Shape (n_channels, block_size) float32 array.
            
        Returns:
            Shape (1, block_size) float32 beamformed output.
        """
        n_channels, block_size = block.shape
        sample_rate = self.stream_config.sample_rate
        
        # Prepare output
        output = np.zeros(block_size, dtype=np.complex128)
        
        # Process each channel
        for sensor_id, delay in self.steering_delays.items():
            if sensor_id >= n_channels:
                logger.warning(f"Sensor {sensor_id} exceeds channel count {n_channels}")
                continue
            
            # Get channel signal as real-valued array
            channel_signal = block[sensor_id, :].astype(np.float64)

            # FFT
            X = np.fft.rfft(channel_signal)
            
            # Compute frequency bins
            freqs = np.fft.rfftfreq(block_size, 1.0 / sample_rate)
            
            # Apply phase shift for fractional delay: exp(-j*2*pi*f*delay)
            phase_shift = np.exp(-1j * 2.0 * np.pi * freqs * delay)
            X_delayed = X * phase_shift
            
            # IFFT
            delayed_signal = np.fft.irfft(X_delayed, n=block_size)
            
            # Accumulate
            output += delayed_signal
        
        # Take real part and normalize
        output_real = np.real(output) / n_channels
        
        # Return as (1, block_size) array
        return output_real.astype(np.float32).reshape(1, block_size)
