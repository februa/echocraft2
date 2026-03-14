"""Peak frequency extraction from spectrum records."""

import logging

logger = logging.getLogger(__name__)


class PeakFrequencyExtractor:
    """Extracts peak frequency from spectrum records.
    
    Finds the frequency bin with maximum power spectral density
    and returns as a scalar record.
    """

    @staticmethod
    def find_peak(spectrum_records: list[dict]) -> dict:
        """Find peak frequency from spectrum records.
        
        Identifies the frequency with maximum power_db value.
        
        Args:
            spectrum_records: List of spectrum records with keys:
                - type: "spectrum"
                - freq: Frequency in Hz
                - power_db: Power in dB
                
        Returns:
            Scalar record with keys:
                - type: "scalar"
                - key: "peak_freq"
                - value: Peak frequency in Hz
                - unit: "Hz"
        """
        if not spectrum_records:
            logger.warning("No spectrum records provided")
            return {
                "type": "scalar",
                "key": "peak_freq",
                "value": 0.0,
                "unit": "Hz",
            }

        # Exclude DC component (freq == 0) from peak search
        non_dc_records = [r for r in spectrum_records if r.get("freq", 0.0) > 0.0]
        if not non_dc_records:
            non_dc_records = spectrum_records

        # Find record with maximum power_db
        peak_record = max(
            non_dc_records,
            key=lambda r: r.get("power_db", float('-inf'))
        )
        
        return {
            "type": "scalar",
            "key": "peak_freq",
            "value": peak_record["freq"],
            "unit": "Hz",
        }
