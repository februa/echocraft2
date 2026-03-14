"""Polar bearing level plot generator."""

import json
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class PolarPlotter:
    """Generates polar plot of bearing level.
    
    Angular axis: Azimuth [deg] (0-360)
    Radial axis: Level [dB/uPa]
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

        times = sorted(set(r.get("time", 0.0) for r in records))
        last_time = times[-1]
        snapshot = [r for r in records if r.get("time", 0.0) == last_time]
        snapshot.sort(key=lambda r: r["azimuth"])

        azimuths_deg = [r["azimuth"] for r in snapshot]
        levels = [r["level_db"] for r in snapshot]

        # Convert to radians for polar plot
        azimuths_rad = np.radians(azimuths_deg)

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})
        ax.plot(azimuths_rad, levels, linewidth=0.8)
        ax.set_theta_zero_location("N")  # 0 degrees at top
        ax.set_theta_direction(-1)  # Clockwise
        ax.set_xlabel("Level [dB/uPa]")
        ax.set_title("Polar Bearing Level", pad=20)
        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        logger.info(f"Saved polar plot to {output_path}")
