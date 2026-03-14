"""Scene overview plot generator.

Visualizes array geometry and signal source directions in world coordinates.
Helps verify simulation setup before running the full pipeline.
"""

import json
import logging
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

logger = logging.getLogger(__name__)


class ScenePlotter:
    """Generates a top-down scene overview plot.

    Shows sensor positions from array.json and signal arrival directions
    from NDJSON source records. Coordinate system follows the beamformer
    convention: Azimuth 0 = +y (north), 90 = +x (east).

    The plot uses a top-down (x-y plane) view with:
      - Sensor positions as numbered markers
      - Incoming signals as arrows pointing toward the array center
      - Labels showing frequency, source level, and azimuth per source
      - Noise level annotation if present
    """

    def load_array(self, array_path: str) -> list[dict]:
        """Load sensor positions from array.json."""
        with open(array_path) as f:
            data = json.load(f)
        return data["sensors"]

    def load_sources(self, input_path: str) -> tuple[list[dict], float | None]:
        """Load source and noise records from NDJSON.

        Returns:
            Tuple of (source_records, noise_level_or_none).
        """
        sources = []
        noise_level = None
        with open(input_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("type") == "source":
                    sources.append(record)
                elif record.get("type") == "noise":
                    noise_level = record.get("nl")
        return sources, noise_level

    def plot(
        self,
        array_path: str,
        input_path: str,
        output_path: str,
    ) -> None:
        """Generate scene overview plot.

        Args:
            array_path: Path to array.json.
            input_path: Path to NDJSON file with source/noise records.
            output_path: Output image path (PNG/SVG).
        """
        sensors = self.load_array(array_path)
        sources, noise_level = self.load_sources(input_path)

        if not sensors:
            logger.warning("No sensors found in array.json")
            return

        # Sensor positions
        sx = np.array([s["x"] for s in sensors])
        sy = np.array([s["y"] for s in sensors])

        # Array center and extent
        cx, cy = np.mean(sx), np.mean(sy)
        array_span = max(np.ptp(sx), np.ptp(sy), 0.01)
        margin = array_span * 3.0
        arrow_len = array_span * 2.0

        fig, ax = plt.subplots(figsize=(10, 10))

        # --- Draw sensors ---
        ax.scatter(sx, sy, s=80, c="black", zorder=5, label="Sensors")
        for s in sensors:
            ax.annotate(
                str(s["id"]),
                (s["x"], s["y"]),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=8,
                color="dimgray",
            )

        # --- Draw signal arrival directions ---
        colors = plt.cm.tab10.colors
        for i, src in enumerate(sources):
            az_deg = src["az"]
            el_deg = src.get("el", 0.0)
            freq = src["freq"]
            sl = src["sl"]

            az_rad = math.radians(az_deg)

            # Direction vector (azimuth: 0=+y, 90=+x)
            dx = math.sin(az_rad)
            dy = math.cos(az_rad)

            # Arrow: from far away toward array center
            start_x = cx + dx * arrow_len
            start_y = cy + dy * arrow_len
            end_x = cx + dx * (array_span * 0.3)
            end_y = cy + dy * (array_span * 0.3)

            color = colors[i % len(colors)]

            ax.annotate(
                "",
                xy=(end_x, end_y),
                xytext=(start_x, start_y),
                arrowprops=dict(
                    arrowstyle="->,head_width=0.4,head_length=0.3",
                    color=color,
                    lw=2.0,
                ),
                zorder=3,
            )

            # Label at arrow start
            label = f"Src {i}: {freq} Hz, {sl} dB\nAz={az_deg} deg, El={el_deg} deg"
            ax.annotate(
                label,
                (start_x, start_y),
                textcoords="offset points",
                xytext=(8, 8),
                fontsize=9,
                color=color,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, alpha=0.8),
                zorder=6,
            )

        # --- Compass rose ---
        rose_x = cx - margin * 0.85
        rose_y = cy + margin * 0.85
        rose_len = array_span * 0.4
        ax.annotate(
            "", xy=(rose_x, rose_y + rose_len),
            xytext=(rose_x, rose_y),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1.5),
        )
        ax.annotate(
            "", xy=(rose_x + rose_len, rose_y),
            xytext=(rose_x, rose_y),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1.5),
        )
        ax.text(rose_x, rose_y + rose_len * 1.15, "+Y (Az=0)",
                ha="center", fontsize=8, color="gray")
        ax.text(rose_x + rose_len * 1.15, rose_y, "+X (Az=90)",
                ha="left", va="center", fontsize=8, color="gray")

        # --- Noise annotation ---
        if noise_level is not None:
            ax.text(
                0.02, 0.02,
                f"Noise Level: {noise_level} dB",
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment="bottom",
                bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec="orange"),
            )

        # --- Axis formatting ---
        ax.set_xlim(cx - margin, cx + margin)
        ax.set_ylim(cy - margin, cy + margin)
        ax.set_aspect("equal")
        ax.set_xlabel("X [m]")
        ax.set_ylabel("Y [m]")
        ax.set_title("Scene Overview (Top-Down View)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right")

        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        logger.info(f"Saved scene plot to {output_path}")
