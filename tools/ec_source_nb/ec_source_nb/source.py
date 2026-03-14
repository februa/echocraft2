"""Narrowband acoustic source model."""

from ec_source_nb.records import SourceRecord


class NarrowbandSource:
    """Represents a narrowband acoustic source with validation.
    
    Attributes:
        freq: Frequency in Hz.
        sl: Source level in dB re 1 μPa.
        az: Azimuth in degrees.
        el: Elevation in degrees.
    """

    def __init__(self, freq: float, sl: float, az: float, el: float) -> None:
        """Initialize a narrowband source with validation.
        
        Args:
            freq: Frequency in Hz (must be positive).
            sl: Source level in dB re 1 μPa.
            az: Azimuth in degrees.
            el: Elevation in degrees.
            
        Raises:
            ValueError: If freq is not positive.
        """
        if freq <= 0:
            raise ValueError(f"Frequency must be positive, got {freq}")
        
        self.freq = freq
        self.sl = sl
        self.az = az
        self.el = el

    def to_record(self) -> SourceRecord:
        """Create a SourceRecord from this source.
        
        Returns:
            SourceRecord with current parameters.
        """
        return SourceRecord(
            freq=self.freq,
            sl=self.sl,
            az=self.az,
            el=self.el,
        )
