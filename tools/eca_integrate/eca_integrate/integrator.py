"""Exponential moving average integration for spectrum records."""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class EmaIntegrator:
    """Exponential moving average integrator for spectrum data.
    
    Maintains running exponential moving average of power spectral density
    values across frequency bins. Applies EMA formula:
    new_avg = alpha * new_value + (1 - alpha) * old_avg
    
    Attributes:
        alpha: Smoothing factor (0 < alpha <= 1).
        spectrum: Dictionary mapping frequency to accumulated power_db.
    """

    def __init__(self, alpha: float) -> None:
        """Initialize EmaIntegrator.
        
        Args:
            alpha: Smoothing factor (0 < alpha <= 1).
                   Higher values give more weight to new samples.
                   
        Raises:
            ValueError: If alpha is not in valid range.
        """
        if not (0 < alpha <= 1.0):
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        
        self.alpha = alpha
        self.spectrum = defaultdict(lambda: None)
        
        logger.debug(f"EmaIntegrator initialized: alpha={alpha}")

    def integrate(self, records: list[dict]) -> list[dict]:
        """Integrate spectrum records using EMA.
        
        Updates accumulated spectrum with exponential moving average,
        returns updated records.
        
        Args:
            records: List of spectrum records with keys:
                - type: "spectrum"
                - freq: Frequency in Hz
                - power_db: Power in dB
                
        Returns:
            List of updated spectrum records in frequency order.
        """
        # Update accumulator with new records
        for record in records:
            if record.get("type") == "spectrum":
                freq = record["freq"]
                new_power = record["power_db"]
                
                # Apply EMA formula
                if self.spectrum[freq] is None:
                    # First sample: use new value directly
                    self.spectrum[freq] = new_power
                else:
                    # EMA: new = alpha * new_value + (1 - alpha) * old
                    self.spectrum[freq] = (
                        self.alpha * new_power +
                        (1.0 - self.alpha) * self.spectrum[freq]
                    )
        
        # Generate output records from accumulated spectrum (sorted by frequency)
        output_records = []
        for freq in sorted(self.spectrum.keys()):
            output_records.append({
                "type": "spectrum",
                "freq": freq,
                "power_db": self.spectrum[freq],
            })
        
        return output_records
