"""Bearing level plot generator."""

import json
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class BearingLevelPlotter:
    """Generates bearing level plots from NDJSON bearing records.
    
    Uses last time step for snapshot display.
    x-axis: Azimuth [deg] (0-180)
    y-axis: Level [dB/uPa]
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

        azimuths = [r["azimuth"] for r in snapshot]
        levels = [r["level_db"] for r in snapshot]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(azimuths, levels, linewidth=0.8)
        ax.set_xlabel("Azimuth [deg]")
        ax.set_ylabel("Level [dB/uPa]")
        ax.set_title("Bearing Level")
        ax.set_xlim(0, 180)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        logger.info(f"Saved BL plot to {output_path}")
