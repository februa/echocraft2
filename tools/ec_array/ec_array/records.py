"""Data records for array processing tool."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TransferRecord:
    """Represents acoustic transfer from source to sensor.
    
    Attributes:
        source_id: Unique identifier for the source.
        sensor_id: Unique identifier for the sensor.
        delay: Signal arrival delay in seconds.
        loss_db: Path loss in dB.
        freq: Frequency in Hz.
        type: Record type identifier (always "transfer").
    """

    source_id: int
    sensor_id: int
    delay: float
    loss_db: float
    freq: float
    type: str = "transfer"

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary representation.
        
        Returns:
            Dictionary with all record fields.
        """
        return {
            "type": self.type,
            "source_id": self.source_id,
            "sensor_id": self.sensor_id,
            "delay": self.delay,
            "loss_db": self.loss_db,
            "freq": self.freq,
        }
