"""Ambient noise model."""

import math

from ec_noise.records import NoiseRecord


class NoiseField:
    """Represents ambient acoustic noise field with validation.
    
    Attributes:
        nl: Noise level in dB re 1 μPa.
    """

    def __init__(self, nl: float) -> None:
        """Initialize a noise field with validation.
        
        Args:
            nl: Noise level in dB re 1 μPa (must be finite).
            
        Raises:
            ValueError: If nl is not finite (inf or nan).
        """
        if not math.isfinite(nl):
            raise ValueError(f"Noise level must be finite, got {nl}")
        
        self.nl = nl

    def to_record(self) -> NoiseRecord:
        """Create a NoiseRecord from this noise field.
        
        Returns:
            NoiseRecord with current noise level.
        """
        return NoiseRecord(nl=self.nl)
