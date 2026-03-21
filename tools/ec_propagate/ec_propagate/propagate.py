"""Propagation loss model for acoustic sources."""

from typing import Any


SUPPORTED_MODELS = ("plane-wave", "lossless")


def _thorp_absorption(freq_hz: float) -> float:
    """Compute absorption in dB/km using Thorp's formula.

    Reference: Thorp (1967), valid for 0.1-50 kHz.

    Args:
        freq_hz: Frequency in Hz.

    Returns:
        Absorption coefficient in dB/km.
    """
    f_khz = freq_hz / 1000.0
    f2 = f_khz * f_khz
    return 0.1 * f2 / (1.0 + f2) + 40.0 * f2 / (4100.0 + f2)


class PlaneWavePropagator:
    """Models plane-wave propagation with configurable loss model.

    Supported models:
        plane-wave: Frequency-dependent absorption using Thorp's formula.
        lossless:   No propagation loss. SL is preserved as-is.

    Both models assign source_id to source records.
    """

    def __init__(self, ocean_config: dict[str, Any], model: str = "plane-wave") -> None:
        """Initialize propagator with ocean configuration.

        Args:
            ocean_config: Ocean configuration dictionary (e.g., from ocean.json).
            model: Propagation model name. One of "plane-wave", "lossless".

        Raises:
            ValueError: If model is not supported.
        """
        if model not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unknown model '{model}'. Supported: {', '.join(SUPPORTED_MODELS)}"
            )
        self.ocean_config = ocean_config
        self.model = model
        self._source_id_counter = 0

    def propagate(self, source_record: dict[str, Any]) -> dict[str, Any]:
        """Apply propagation loss to a source record.

        For plane-wave model:
        - Absorption: Thorp's formula (dB/km), f in kHz:
          alpha = 0.1*f^2/(1+f^2) + 40*f^2/(4100+f^2)
        - Default range: 1 km
        - Adjusted source level: sl_adj = sl - alpha

        For lossless model:
        - No absorption applied. sl_adj = sl.

        Both models assign source_id from internal counter.

        Args:
            source_record: Source record dictionary with freq, sl fields.

        Returns:
            Modified source record with source_id and adjusted sl.
        """
        if source_record.get("type") != "source":
            return source_record

        freq = source_record["freq"]
        sl = source_record["sl"]

        if self.model == "lossless":
            adjusted_sl = sl
        else:
            loss_db = _thorp_absorption(freq)
            adjusted_sl = sl - loss_db

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
