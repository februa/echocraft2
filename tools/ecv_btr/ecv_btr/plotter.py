"""BTR (Bearing-Time Record) plot generator."""

import json
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

logger = logging.getLogger(__name__)


class BtrPlotter:
    """Generates BTR (Bearing-Time Record) plot.
    
    x-axis: Azimuth [deg] (0-360)
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
                if record.get("type") == "bearing":
                    records.append(record)
        return records

    def plot(self, input_path: str, output_path: str) -> None:
        records = self.load_records(input_path)
        if not records:
            logger.warning("No bearing records found")
            return

        # Extract unique times and azimuths
        times = sorted(set(r["time"] for r in records))
        azimuths = sorted(set(r["azimuth"] for r in records))

        if len(times) < 2 or len(azimuths) < 2:
            logger.warning("Insufficient data for BTR plot (need multiple times and azimuths)")
            return

        # Build 2D array: rows=time, cols=azimuth
        time_idx = {t: i for i, t in enumerate(times)}
        az_idx = {a: i for i, a in enumerate(azimuths)}
        data = np.full((len(times), len(azimuths)), np.nan)

        for r in records:
            ti = time_idx[r["time"]]
            ai = az_idx[r["azimuth"]]
            data[ti, ai] = r["level_db"]

        fig, ax = plt.subplots(figsize=(12, 8))
        im = ax.pcolormesh(
            azimuths, times, data,
            cmap="jet", shading="auto",
        )
        ax.set_xlabel("Azimuth [deg]")
        ax.set_ylabel("Time [s]")
        ax.set_title("BTR (Bearing-Time Record)")
        ax.invert_yaxis()  # Time inverted: top=old, bottom=new
        cbar = fig.colorbar(im, ax=ax, label="Level [dB/uPa]")
        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        logger.info(f"Saved BTR plot to {output_path}")
