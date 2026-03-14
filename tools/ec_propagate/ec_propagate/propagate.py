"""Propagation loss model for acoustic sources."""

from typing import Any


class PlaneWavePropagator:
    """Models plane-wave propagation with absorption loss.
    
    Applies frequency-dependent absorption to source levels based on
    simplified ocean propagation model. Assigns source_id to sources.
    """

    def __init__(self, ocean_config: dict[str, Any], model: str = "plane-wave") -> None:
        """Initialize propagator with ocean configuration.
        
        Args:
            ocean_config: Ocean configuration dictionary (e.g., from ocean.json).
            model: Propagation model name (default "plane-wave").
        """
        self.ocean_config = ocean_config
        self.model = model
        self._source_id_counter = 0

    def propagate(self, source_record: dict[str, Any]) -> dict[str, Any]:
        """Apply propagation loss to a source record.
        
        For plane-wave model:
        - Absorption: alpha = 0.001 * freq (dB/km)
        - Default range: 1 km
        - Adjusted source level: sl_adj = sl - alpha
        - Assigns source_id from internal counter
        
        Args:
            source_record: Source record dictionary with freq, sl fields.
            
        Returns:
            Modified source record with source_id and adjusted sl.
        """
        if source_record.get("type") != "source":
            return source_record
        
        freq = source_record["freq"]
        sl = source_record["sl"]
        
        # Calculate absorption in dB/km
        # Simplified model: alpha = 0.001 * f
        alpha = 0.001 * freq
        
        # Apply to default range of 1 km
        loss_db = alpha
        adjusted_sl = sl - loss_db
        
        # Create new record with source_id and adjusted sl
        result = source_record.copy()
        result["source_id"] = self._source_id_counter
        result["sl"] = adjusted_sl
        
        self._source_id_counter += 1
        
        return result

    def reset(self) -> None:
        """Reset the source_id counter.
        
        Used for testing or when processing multiple independent streams.
        """
        self._source_id_counter = 0
