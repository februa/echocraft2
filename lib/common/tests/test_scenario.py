"""Tests for scenario configuration."""

import json
import os
import tempfile

import pytest

from lib.common.scenario import ScenarioConfig, resolve_config_path


class TestScenarioConfig:
    """Tests for ScenarioConfig dataclass."""

    def test_default_values_are_none(self) -> None:
        config = ScenarioConfig()
        assert config.stream is None
        assert config.array is None
        assert config.ocean is None

    def test_frozen(self) -> None:
        config = ScenarioConfig(stream="/path/to/stream.json")
        with pytest.raises(AttributeError):
            config.stream = "/other/path"  # type: ignore[misc]


class TestScenarioConfigFromFile:
    """Tests for ScenarioConfig.from_file."""

    def _write_scenario(self, tmpdir: str, data: dict) -> str:
        path = os.path.join(tmpdir, "scenario.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_all_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_scenario(tmpdir, {
                "stream": "stream.json",
                "array": "array.json",
                "ocean": "ocean.json",
            })
            config = ScenarioConfig.from_file(path)

            assert config.stream == os.path.join(tmpdir, "stream.json")
            assert config.array == os.path.join(tmpdir, "array.json")
            assert config.ocean == os.path.join(tmpdir, "ocean.json")

    def test_partial_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_scenario(tmpdir, {"stream": "stream.json"})
            config = ScenarioConfig.from_file(path)

            assert config.stream == os.path.join(tmpdir, "stream.json")
            assert config.array is None
            assert config.ocean is None

    def test_empty_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_scenario(tmpdir, {})
            config = ScenarioConfig.from_file(path)

            assert config.stream is None
            assert config.array is None
            assert config.ocean is None

    def test_relative_paths_resolved_from_scenario_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "configs")
            os.makedirs(subdir)
            path = self._write_scenario(subdir, {
                "stream": "../data/stream.json",
            })
            config = ScenarioConfig.from_file(path)

            expected = os.path.normpath(os.path.join(tmpdir, "data", "stream.json"))
            assert config.stream == expected

    def test_absolute_paths_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_scenario(tmpdir, {
                "stream": "/absolute/path/stream.json",
            })
            config = ScenarioConfig.from_file(path)

            assert config.stream == "/absolute/path/stream.json"

    def test_unknown_keys_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_scenario(tmpdir, {
                "stream": "stream.json",
                "unknown_key": "value",
            })
            with pytest.raises(ValueError, match="Unknown keys"):
                ScenarioConfig.from_file(path)

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            ScenarioConfig.from_file("/nonexistent/scenario.json")

    def test_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "scenario.json")
            with open(path, "w") as f:
                f.write("not json")
            with pytest.raises(json.JSONDecodeError):
                ScenarioConfig.from_file(path)


class TestResolveConfigPath:
    """Tests for resolve_config_path function."""

    def test_explicit_takes_precedence(self) -> None:
        scenario = ScenarioConfig(stream="/scenario/stream.json")
        result = resolve_config_path(
            explicit="/explicit/stream.json",
            scenario=scenario,
            field="stream",
        )
        assert result == "/explicit/stream.json"

    def test_falls_back_to_scenario(self) -> None:
        scenario = ScenarioConfig(stream="/scenario/stream.json")
        result = resolve_config_path(
            explicit=None,
            scenario=scenario,
            field="stream",
        )
        assert result == "/scenario/stream.json"

    def test_none_when_neither_provided(self) -> None:
        result = resolve_config_path(
            explicit=None,
            scenario=None,
            field="stream",
        )
        assert result is None

    def test_none_when_scenario_field_missing(self) -> None:
        scenario = ScenarioConfig(array="/some/array.json")
        result = resolve_config_path(
            explicit=None,
            scenario=scenario,
            field="stream",
        )
        assert result is None

    def test_required_raises_when_missing(self) -> None:
        with pytest.raises(ValueError, match="--stream is required"):
            resolve_config_path(
                explicit=None,
                scenario=None,
                field="stream",
                required=True,
                tool_name="ec-sample",
            )

    def test_required_ocean_shows_env_flag(self) -> None:
        with pytest.raises(ValueError, match="--env is required"):
            resolve_config_path(
                explicit=None,
                scenario=None,
                field="ocean",
                required=True,
                tool_name="ec-propagate",
            )

    def test_required_satisfied_by_scenario(self) -> None:
        scenario = ScenarioConfig(stream="/scenario/stream.json")
        result = resolve_config_path(
            explicit=None,
            scenario=scenario,
            field="stream",
            required=True,
        )
        assert result == "/scenario/stream.json"

    def test_no_scenario_object(self) -> None:
        result = resolve_config_path(
            explicit="/explicit/array.json",
            scenario=None,
            field="array",
        )
        assert result == "/explicit/array.json"
