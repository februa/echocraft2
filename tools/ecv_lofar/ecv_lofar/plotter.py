"""LOFAR (Low Frequency Analysis and Recording) plot generator."""

import json
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class LofarPlotter:
    """Generates LOFAR plot from spectrum records.
    
    x-axis: Frequency [Hz] (0-fs/2)
    y-axis: Time [s] (0-T, inverted)
    z-axis (color): Level [dB/uPa] (jet colormap)
    """

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

        times = sorted(set(r["time"] for r in records))
        freqs = sorted(set(r["freq"] for r in records))

        if len(times) < 2 or len(freqs) < 2:
            logger.warning("Insufficient data for LOFAR plot (need multiple times and frequencies)")
            return

        time_idx = {t: i for i, t in enumerate(times)}
        freq_idx = {f: i for i, f in enumerate(freqs)}
        data = np.full((len(times), len(freqs)), np.nan)

        for r in records:
            ti = time_idx[r["time"]]
            fi = freq_idx[r["freq"]]
            data[ti, fi] = r["power_db"]

        fig, ax = plt.subplots(figsize=(12, 8))
        im = ax.pcolormesh(
            freqs, times, data,
            cmap="jet", shading="auto",
        )
        ax.set_xlabel("Frequency [Hz]")
        ax.set_ylabel("Time [s]")
        ax.set_title("LOFAR (Low Frequency Analysis and Recording)")
        ax.invert_yaxis()
        cbar = fig.colorbar(im, ax=ax, label="Level [dB/uPa]")
        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        logger.info(f"Saved LOFAR plot to {output_path}")
