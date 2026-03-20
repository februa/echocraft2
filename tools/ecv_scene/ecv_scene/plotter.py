"""Scene overview plot generator.

Visualizes array geometry and signal source directions in LOCAL_ENU
(world) coordinates. Converts VESSEL_BODY positions and relative
bearings to world coordinates using vessel heading.
"""

import json
import logging
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def vessel_body_to_local_enu(
    x_body: np.ndarray,
    y_body: np.ndarray,
    heading_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert VESSEL_BODY (x=bow, y=stbd) to LOCAL_ENU (x=east, y=north).

    Args:
        x_body: Bow-direction coordinates [m].
        y_body: Starboard-direction coordinates [m].
        heading_deg: Vessel heading in degrees (true north = 0, clockwise).

    Returns:
        (east, north) arrays in LOCAL_ENU.
    """
    theta = math.radians(heading_deg)
    sin_t = math.sin(theta)
    cos_t = math.cos(theta)
    # R = [[sin(θ), cos(θ)], [cos(θ), -sin(θ)]]
    east = sin_t * x_body + cos_t * y_body
    north = cos_t * x_body - sin_t * y_body
    return east, north


def relative_to_true_bearing(relative_deg: float, heading_deg: float) -> float:
    """Convert VESSEL_BODY relative bearing to true bearing.

    Args:
        relative_deg: Bearing relative to bow (0=bow, 90=starboard).
        heading_deg: Vessel heading in degrees (true north = 0).

    Returns:
        True bearing in degrees [0, 360).
    """
    return (relative_deg + heading_deg) % 360


class ScenePlotter:
    """Generates a top-down scene overview plot in LOCAL_ENU coordinates.

    Shows sensor positions (converted from VESSEL_BODY to LOCAL_ENU)
    and signal arrival directions (converted from relative to true bearing).

    LOCAL_ENU: x = East, y = North.
    True bearing: 0 = North (+y), 90 = East (+x), clockwise.
    """

    def load_array(self, array_path: str) -> list[dict]:
        """Load sensor positions from array.json.

        Sensor positions are in VESSEL_BODY coordinates:
        x = bow (forward), y = starboard, z = up.
        """
        with open(array_path) as f:
            data = json.load(f)
        return data["sensors"]

    def load_sources(self, input_path: str) -> tuple[list[dict], float | None]:
        """Load source and noise records from NDJSON.

        Source azimuth values are VESSEL_BODY relative bearings:
        0 = bow, 90 = starboard.

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
        heading_deg: float = 0.0,
    ) -> None:
        """Generate scene overview plot in LOCAL_ENU coordinates.

        Args:
            array_path: Path to array.json (VESSEL_BODY coords).
            input_path: Path to NDJSON file with source/noise records.
            output_path: Output image path (PNG/SVG).
            heading_deg: Vessel heading in degrees (true north = 0,
                clockwise positive). Default 0 means bow points north.
        """
        sensors = self.load_array(array_path)
        sources, noise_level = self.load_sources(input_path)

        if not sensors:
            logger.warning("No sensors found in array.json")
            return

        # Convert sensor positions: VESSEL_BODY → LOCAL_ENU
        body_x = np.array([s["x"] for s in sensors])
        body_y = np.array([s["y"] for s in sensors])
        enu_east, enu_north = vessel_body_to_local_enu(body_x, body_y, heading_deg)

        # Array center and extent in ENU
        cx, cy = np.mean(enu_east), np.mean(enu_north)
        array_span = max(np.ptp(enu_east), np.ptp(enu_north), 0.01)
        margin = array_span * 3.0
        arrow_len = array_span * 2.0

        fig, ax = plt.subplots(figsize=(10, 10))

        # --- Draw sensors ---
        ax.scatter(enu_east, enu_north, s=80, c="black", zorder=5, label="Sensors")
        for i, s in enumerate(sensors):
            ax.annotate(
                str(s["id"]),
                (enu_east[i], enu_north[i]),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=8,
                color="dimgray",
            )

        # --- Draw bow direction indicator ---
        bow_rad = math.radians(heading_deg)
        bow_dx = math.sin(bow_rad)  # true bearing → ENU: east = sin(θ)
        bow_dy = math.cos(bow_rad)  # true bearing → ENU: north = cos(θ)
        bow_len = array_span * 1.2
        ax.annotate(
            "",
            xy=(cx + bow_dx * bow_len, cy + bow_dy * bow_len),
            xytext=(cx, cy),
            arrowprops=dict(arrowstyle="->,head_width=0.3,head_length=0.2",
                            color="darkgreen", lw=2.0, linestyle="--"),
            zorder=4,
        )
        ax.text(
            cx + bow_dx * bow_len * 1.1,
            cy + bow_dy * bow_len * 1.1,
            f"Bow (hdg={heading_deg:.0f}°)",
            ha="center", va="center", fontsize=9, color="darkgreen",
            fontweight="bold",
        )

        # --- Draw signal arrival directions ---
        colors = plt.cm.tab10.colors
        for i, src in enumerate(sources):
            az_rel = src["az"]  # VESSEL_BODY relative bearing
            el_deg = src.get("el", 0.0)
            freq = src["freq"]
            sl = src["sl"]

            # Convert relative bearing → true bearing
            az_true = relative_to_true_bearing(az_rel, heading_deg)
            az_true_rad = math.radians(az_true)

            # Direction in LOCAL_ENU: true bearing → (east, north)
            dx = math.sin(az_true_rad)  # east component
            dy = math.cos(az_true_rad)  # north component

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
            label = (f"Src {i}: {freq} Hz, {sl} dB\n"
                     f"Rel={az_rel}°, True={az_true:.0f}°, El={el_deg}°")
            ax.annotate(
                label,
                (start_x, start_y),
                textcoords="offset points",
                xytext=(8, 8),
                fontsize=9,
                color=color,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color,
                          alpha=0.8),
                zorder=6,
            )

        # --- Compass rose (LOCAL_ENU: x=East, y=North) ---
        rose_x = cx - margin * 0.85
        rose_y = cy + margin * 0.85
        rose_len = array_span * 0.4
        # North arrow (+y)
        ax.annotate(
            "", xy=(rose_x, rose_y + rose_len),
            xytext=(rose_x, rose_y),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1.5),
        )
        # East arrow (+x)
        ax.annotate(
            "", xy=(rose_x + rose_len, rose_y),
            xytext=(rose_x, rose_y),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1.5),
        )
        ax.text(rose_x, rose_y + rose_len * 1.15, "N",
                ha="center", fontsize=10, color="gray", fontweight="bold")
        ax.text(rose_x + rose_len * 1.15, rose_y, "E",
                ha="left", va="center", fontsize=10, color="gray",
                fontweight="bold")

        # --- Noise annotation ---
        if noise_level is not None:
            ax.text(
                0.02, 0.02,
                f"Noise Level: {noise_level} dB",
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment="bottom",
                bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow",
                          ec="orange"),
            )

        # --- Axis formatting ---
        ax.set_xlim(cx - margin, cx + margin)
        ax.set_ylim(cy - margin, cy + margin)
        ax.set_aspect("equal")
        ax.set_xlabel("East [m]")
        ax.set_ylabel("North [m]")
        ax.set_title("Scene Overview (LOCAL_ENU, Top-Down View)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right")

        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        logger.info(f"Saved scene plot to {output_path}")
