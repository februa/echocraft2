"""Spectrum plot generator."""

import json
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class SpectrumPlotter:
    """Generates spectrum plots from NDJSON spectrum records.
    
    Supports linear (amplitude in uPa) and log (power in dB) scales.
    For snapshot mode, uses only the last time step's records.
    """

    def __init__(self, scale: str = "log") -> None:
        if scale not in ("linear", "log"):
            raise ValueError(f"Invalid scale: {scale}. Must be 'linear' or 'log'.")
        self.scale = scale

    def load_records(self, input_path: str) -> list[dict]:
        records = []
        with open(input_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("type") == "spectrum":
                    records.append(record)
        return records

    def plot(self, input_path: str, output_path: str) -> None:
        records = self.load_records(input_path)
        if not records:
            logger.warning("No spectrum records found")
            return

        # Use last time step only for snapshot
        times = sorted(set(r.get("time", 0.0) for r in records))
        last_time = times[-1]
        snapshot = [r for r in records if r.get("time", 0.0) == last_time]
        snapshot.sort(key=lambda r: r["freq"])

        freqs = [r["freq"] for r in snapshot]
        power_db = [r["power_db"] for r in snapshot]

        fig, ax = plt.subplots(figsize=(10, 6))

        if self.scale == "log":
            ax.plot(freqs, power_db, linewidth=0.8)
            ax.set_xlabel("Frequency [Hz]")
            ax.set_ylabel("Level [dB]")
            ax.set_title("Frequency Spectrum (Log Scale)")
        else:
            # Convert dB to linear amplitude: 10^(power_db/20)
            amplitudes = [10.0 ** (p / 20.0) for p in power_db]
            ax.plot(freqs, amplitudes, linewidth=0.8)
            ax.set_xlabel("Frequency [Hz]")
            ax.set_ylabel("Amplitude [uPa]")
            ax.set_title("Frequency Spectrum (Linear Scale)")

        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        logger.info(f"Saved spectrum plot to {output_path}")
