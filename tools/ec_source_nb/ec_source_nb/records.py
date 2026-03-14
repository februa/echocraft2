"""Data records for narrowband source tool."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceRecord:
    """Represents a narrowband acoustic source.
    
    Attributes:
        freq: Frequency in Hz (must be positive).
        sl: Source level in dB re 1 μPa.
        az: Azimuth in degrees (0-360).
        el: Elevation in degrees (-90 to 90).
        type: Record type identifier (always "source").
    """

    freq: float
    sl: float
    az: float
    el: float
    type: str = "source"

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary representation.
        
        Returns:
            Dictionary with all record fields.
        """
        return {
            "type": self.type,
            "freq": self.freq,
            "sl": self.sl,
            "az": self.az,
            "el": self.el,
        }
