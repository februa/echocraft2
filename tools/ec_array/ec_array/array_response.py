"""Array response model for plane-wave beamforming."""

import math
from dataclasses import dataclass
from typing import Any

from ec_array.records import TransferRecord


@dataclass(frozen=True)
class Sensor:
    """Represents a sensor in the array.
    
    Attributes:
        id: Sensor identifier.
        x: X coordinate in meters.
        y: Y coordinate in meters.
        z: Z coordinate in meters.
    """

    id: int
    x: float
    y: float
    z: float


class ArrayResponse:
    """Computes array response for plane-wave sources.
    
    Generates transfer records (delay, loss) for each source-sensor pair
    using plane-wave propagation model.
    """

    def __init__(self, sensors: list[dict[str, Any]], sound_speed: float = 1500.0) -> None:
        """Initialize array response model.
        
        Args:
            sensors: List of sensor dictionaries with id, x, y, z fields.
            sound_speed: Sound speed in m/s (default 1500.0).
        """
        self.sensors = [
            Sensor(
                id=int(s["id"]),
                x=float(s["x"]),
                y=float(s["y"]),
                z=float(s["z"]),
            )
            for s in sensors
        ]
        self.sound_speed = sound_speed

    def compute_transfers(self, source_record: dict[str, Any]) -> list[TransferRecord]:
        """Compute transfer records for a source to all sensors.
        
        For plane-wave propagation:
        - Direction vector from azimuth and elevation (in degrees):
          dx = cos(el_rad) * cos(az_rad)
          dy = cos(el_rad) * sin(az_rad)
          dz = sin(el_rad)
        - Delay for each sensor:
          delay = (sensor.x * dx + sensor.y * dy + sensor.z * dz) / sound_speed
        - Loss: uses source sl (already includes propagation loss)
        
        Args:
            source_record: Source record with source_id, freq, sl, az, el.
            
        Returns:
            List of TransferRecord objects for each sensor.
        """
        if source_record.get("type") != "source":
            return []
        
        source_id = source_record.get("source_id")
        freq = source_record["freq"]
        sl = source_record["sl"]
        az_deg = source_record["az"]
        el_deg = source_record["el"]
        
        # Convert angles to radians
        az_rad = math.radians(az_deg)
        el_rad = math.radians(el_deg)
        
        # Calculate direction vector
        cos_el = math.cos(el_rad)
        dx = cos_el * math.cos(az_rad)
        dy = cos_el * math.sin(az_rad)
        dz = math.sin(el_rad)
        
        # Generate transfer records for each sensor
        transfers = []
        for sensor in self.sensors:
            # Calculate delay
            dot_product = sensor.x * dx + sensor.y * dy + sensor.z * dz
            delay = dot_product / self.sound_speed
            
            # Loss is the source level (already includes propagation loss)
            loss_db = sl
            
            transfer = TransferRecord(
                source_id=source_id,
                sensor_id=sensor.id,
                delay=delay,
                loss_db=loss_db,
                freq=freq,
            )
            transfers.append(transfer)
        
        return transfers
