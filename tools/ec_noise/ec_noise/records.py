"""Data records for noise tool."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NoiseRecord:
    """Represents ambient acoustic noise.
    
    Attributes:
        nl: Noise level in dB re 1 μPa.
        type: Record type identifier (always "noise").
    """

    nl: float
    type: str = "noise"

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary representation.
        
        Returns:
            Dictionary with all record fields.
        """
        return {
            "type": self.type,
            "nl": self.nl,
        }
