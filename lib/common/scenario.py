"""Scenario configuration for bundling ECHOCRAFT config file paths.

A scenario.json consolidates paths to stream.json, array.json, and ocean.json
into a single file, reducing repetitive CLI arguments across pipeline tools.

Paths in scenario.json are resolved relative to the scenario file's directory.
Individual CLI flags (--stream, --array, --env) override scenario values.

Example scenario.json:
    {
        "stream": "stream.json",
        "array": "array.json",
        "ocean": "ocean.json"
    }
"""

import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScenarioConfig:
    """Resolved paths from a scenario configuration file.

    All paths are absolute, resolved relative to the scenario file's location.
    Fields are optional (None) when not specified in the scenario file.

    Attributes:
        stream: Absolute path to stream.json, or None.
        array: Absolute path to array.json, or None.
        ocean: Absolute path to ocean.json, or None.
    """

    stream: str | None = None
    array: str | None = None
    ocean: str | None = None

    @classmethod
    def from_file(cls, path: str) -> "ScenarioConfig":
        """Load scenario config and resolve paths relative to file location.

        Args:
            path: Path to scenario.json.

        Returns:
            ScenarioConfig with resolved absolute paths.

        Raises:
            FileNotFoundError: If scenario file does not exist.
            json.JSONDecodeError: If JSON is invalid.
            ValueError: If unknown keys are present.
        """
        with open(path, "r") as f:
            data: dict[str, Any] = json.load(f)

        known_keys = {"stream", "array", "ocean"}
        unknown = set(data.keys()) - known_keys
        if unknown:
            raise ValueError(
                f"Unknown keys in scenario config: {', '.join(sorted(unknown))}"
            )

        base_dir = os.path.dirname(os.path.abspath(path))

        def resolve(value: str | None) -> str | None:
            if value is None:
                return None
            if os.path.isabs(value):
                return value
            return os.path.normpath(os.path.join(base_dir, value))

        return cls(
            stream=resolve(data.get("stream")),
            array=resolve(data.get("array")),
            ocean=resolve(data.get("ocean")),
        )


def resolve_config_path(
    explicit: str | None,
    scenario: ScenarioConfig | None,
    field: str,
    required: bool = False,
    tool_name: str = "",
) -> str | None:
    """Resolve a config path from explicit flag or scenario fallback.

    Explicit CLI flag (--stream, --array, --env) takes precedence over
    the scenario value. If neither is provided and required=True, raises.

    Args:
        explicit: Value from CLI flag, or None.
        scenario: ScenarioConfig instance, or None.
        field: Field name in ScenarioConfig ("stream", "array", "ocean").
        required: If True, raise ValueError when path cannot be resolved.
        tool_name: Tool name for error messages.

    Returns:
        Resolved path string, or None if not required and not provided.

    Raises:
        ValueError: If required and no path available from either source.
    """
    if explicit is not None:
        return explicit

    if scenario is not None:
        value = getattr(scenario, field, None)
        if value is not None:
            return value

    if required:
        flag_name = "--env" if field == "ocean" else f"--{field}"
        raise ValueError(
            f"{tool_name}: {flag_name} is required "
            f"(provide directly or via --scenario)"
        )

    return None
