"""Tests for ScenePlotter."""

import json
import math
import os
import tempfile

import pytest
import numpy as np

from ecv_scene.plotter import (
    ScenePlotter,
    vessel_body_to_local_enu,
    relative_to_true_bearing,
)


@pytest.fixture
def plotter():
    return ScenePlotter()


@pytest.fixture
def array_file(tmp_path):
    """Create a minimal array.json."""
    data = {
        "sensors": [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 0.075, "y": 0.0, "z": 0.0},
            {"id": 2, "x": 0.150, "y": 0.0, "z": 0.0},
        ]
    }
    path = tmp_path / "array.json"
    path.write_text(json.dumps(data))
    return str(path)


@pytest.fixture
def sources_file(tmp_path):
    """Create a minimal NDJSON with source and noise records."""
    records = [
        {"type": "source", "freq": 1000, "sl": 0, "az": 90, "el": 0},
        {"type": "source", "freq": 2000, "sl": -5, "az": 45, "el": 10},
        {"type": "noise", "nl": -40},
    ]
    path = tmp_path / "sources.ndjson"
    lines = [json.dumps(r) for r in records]
    path.write_text("\n".join(lines) + "\n")
    return str(path)


class TestLoadArray:
    def test_loads_sensors(self, plotter, array_file):
        sensors = plotter.load_array(array_file)
        assert len(sensors) == 3
        assert sensors[0]["id"] == 0
        assert sensors[1]["x"] == 0.075

    def test_empty_sensors(self, plotter, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text(json.dumps({"sensors": []}))
        sensors = plotter.load_array(str(path))
        assert sensors == []


class TestLoadSources:
    def test_loads_sources_and_noise(self, plotter, sources_file):
        sources, noise_level = plotter.load_sources(sources_file)
        assert len(sources) == 2
        assert sources[0]["freq"] == 1000
        assert sources[1]["az"] == 45
        assert noise_level == -40

    def test_no_noise(self, plotter, tmp_path):
        path = tmp_path / "no_noise.ndjson"
        path.write_text(json.dumps({"type": "source", "freq": 500, "sl": 0, "az": 0, "el": 0}) + "\n")
        sources, noise_level = plotter.load_sources(str(path))
        assert len(sources) == 1
        assert noise_level is None

    def test_empty_lines_skipped(self, plotter, tmp_path):
        path = tmp_path / "sparse.ndjson"
        content = "\n" + json.dumps({"type": "source", "freq": 500, "sl": 0, "az": 0, "el": 0}) + "\n\n"
        path.write_text(content)
        sources, noise_level = plotter.load_sources(str(path))
        assert len(sources) == 1


class TestPlot:
    def test_generates_png(self, plotter, array_file, sources_file, tmp_path):
        output = str(tmp_path / "scene.png")
        plotter.plot(array_file, sources_file, output)
        assert os.path.exists(output)
        assert os.path.getsize(output) > 0

    def test_no_sensors_no_output(self, plotter, sources_file, tmp_path):
        array_path = str(tmp_path / "empty_array.json")
        with open(array_path, "w") as f:
            json.dump({"sensors": []}, f)
        output = str(tmp_path / "scene.png")
        plotter.plot(array_path, sources_file, output)
        assert not os.path.exists(output)

    def test_no_sources(self, plotter, array_file, tmp_path):
        """Plot with sensors but no source records."""
        input_path = str(tmp_path / "empty.ndjson")
        with open(input_path, "w") as f:
            f.write("")
        output = str(tmp_path / "scene.png")
        plotter.plot(array_file, input_path, output)
        assert os.path.exists(output)

    def test_single_sensor(self, plotter, sources_file, tmp_path):
        """Plot with a single sensor (edge case for array_span)."""
        array_path = str(tmp_path / "single.json")
        with open(array_path, "w") as f:
            json.dump({"sensors": [{"id": 0, "x": 0, "y": 0, "z": 0}]}, f)
        output = str(tmp_path / "scene.png")
        plotter.plot(array_path, sources_file, output)
        assert os.path.exists(output)

    def test_with_heading(self, plotter, array_file, sources_file, tmp_path):
        """Plot with non-zero heading generates output."""
        output = str(tmp_path / "scene_headed.png")
        plotter.plot(array_file, sources_file, output, heading_deg=45.0)
        assert os.path.exists(output)
        assert os.path.getsize(output) > 0


class TestVesselBodyToLocalEnu:
    """Tests for VESSEL_BODY → LOCAL_ENU coordinate conversion."""

    def test_heading_zero_bow_is_north(self):
        """Heading=0: bow (+x_body) points north (+y_enu)."""
        x_body = np.array([1.0])
        y_body = np.array([0.0])
        east, north = vessel_body_to_local_enu(x_body, y_body, heading_deg=0.0)
        assert east[0] == pytest.approx(0.0, abs=1e-10)
        assert north[0] == pytest.approx(1.0, abs=1e-10)

    def test_heading_zero_starboard_is_east(self):
        """Heading=0: starboard (+y_body) points east (+x_enu)."""
        x_body = np.array([0.0])
        y_body = np.array([1.0])
        east, north = vessel_body_to_local_enu(x_body, y_body, heading_deg=0.0)
        assert east[0] == pytest.approx(1.0, abs=1e-10)
        assert north[0] == pytest.approx(0.0, abs=1e-10)

    def test_heading_90_bow_is_east(self):
        """Heading=90: bow (+x_body) points east (+x_enu)."""
        x_body = np.array([1.0])
        y_body = np.array([0.0])
        east, north = vessel_body_to_local_enu(x_body, y_body, heading_deg=90.0)
        assert east[0] == pytest.approx(1.0, abs=1e-10)
        assert north[0] == pytest.approx(0.0, abs=1e-10)

    def test_heading_90_starboard_is_south(self):
        """Heading=90: starboard (+y_body) points south (-y_enu)."""
        x_body = np.array([0.0])
        y_body = np.array([1.0])
        east, north = vessel_body_to_local_enu(x_body, y_body, heading_deg=90.0)
        assert east[0] == pytest.approx(0.0, abs=1e-10)
        assert north[0] == pytest.approx(-1.0, abs=1e-10)


class TestRelativeToTrueBearing:
    """Tests for relative → true bearing conversion."""

    def test_heading_zero_passthrough(self):
        assert relative_to_true_bearing(90.0, 0.0) == pytest.approx(90.0)

    def test_heading_offset(self):
        assert relative_to_true_bearing(0.0, 45.0) == pytest.approx(45.0)

    def test_wrap_around(self):
        assert relative_to_true_bearing(350.0, 20.0) == pytest.approx(10.0)

    def test_negative_relative(self):
        result = relative_to_true_bearing(-30.0, 90.0)
        assert result == pytest.approx(60.0)
