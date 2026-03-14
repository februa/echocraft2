"""Signal-to-noise ratio estimation from spectrum records."""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class SnrEstimator:
    """Estimates signal-to-noise ratio from spectrum data.
    
    Computes SNR as the difference between signal power and noise power
    in dB. Signal is identified as peak (or peak_freq if provided), noise
    is estimated as median of remaining frequencies.
    """

    @staticmethod
    def estimate(
        spectrum_records: list[dict],
        peak_freq: float | None = None,
    ) -> dict:
        """Estimate SNR from spectrum records.
        
        If peak_freq is provided, uses power at that frequency as signal
        and median of other bins as noise. Otherwise, uses maximum power
        as signal and median as noise.
        
        Args:
            spectrum_records: List of spectrum records with keys:
                - type: "spectrum"
                - freq: Frequency in Hz
                - power_db: Power in dB
            peak_freq: Optional peak frequency to use for signal power.
                
        Returns:
            Scalar record with keys:
                - type: "scalar"
                - key: "snr"
                - value: SNR in dB
                - unit: "dB"
        """
        if not spectrum_records:
            logger.warning("No spectrum records provided for SNR estimation")
            return {
                "type": "scalar",
                "key": "snr",
                "value": 0.0,
                "unit": "dB",
            }
        
        powers = np.array([r["power_db"] for r in spectrum_records])
        
        if peak_freq is not None:
            # Find power at peak_freq
            peak_powers = [
                r["power_db"]
                for r in spectrum_records
                if abs(r["freq"] - peak_freq) < 1e-6  # Small tolerance for float comparison
            ]
            if peak_powers:
                signal = peak_powers[0]
            else:
                # Fallback to max if peak_freq not found
                logger.warning(f"Peak frequency {peak_freq} not found in spectrum")
                signal = float(np.max(powers))
            
            # Noise is median of all other bins
            noise = float(np.median(powers))
        else:
            # Signal is maximum power, noise is median
            signal = float(np.max(powers))
            noise = float(np.median(powers))
        
        # SNR = signal - noise (in dB)
        snr = signal - noise
        
        logger.debug(f"SNR estimation: signal={signal:.2f} dB, "
                    f"noise={noise:.2f} dB, snr={snr:.2f} dB")
        
        return {
            "type": "scalar",
            "key": "snr",
            "value": snr,
            "unit": "dB",
        }
