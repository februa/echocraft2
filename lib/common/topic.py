"""Topic file management for ec-pub/ec-sub communication.

Manages topic files that allow ec-sub to discover the port where
ec-pub is listening. Topic files are stored in a temporary directory
and cleaned up on normal exit.
"""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


# Default topic directory
_TOPIC_DIR = Path(tempfile.gettempdir()) / "echocraft"


@dataclass(frozen=True)
class TopicInfo:
    """Information stored in a topic file.

    Attributes:
        port: TCP port where ec-pub is listening.
        pid: Process ID of the ec-pub process.
    """

    port: int
    pid: int

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {"port": self.port, "pid": self.pid}

    @classmethod
    def from_dict(cls, data: dict) -> "TopicInfo":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with 'port' and 'pid' keys.

        Returns:
            TopicInfo instance.

        Raises:
            KeyError: If required keys are missing.
            TypeError: If values have wrong types.
        """
        return cls(port=int(data["port"]), pid=int(data["pid"]))


def topic_dir() -> Path:
    """Return the topic directory path.

    Returns:
        Path to the directory where topic files are stored.
    """
    return _TOPIC_DIR


def topic_path(name: str) -> Path:
    """Return the file path for a named topic.

    Args:
        name: Topic name (alphanumeric and hyphens).

    Returns:
        Path to the topic file.

    Raises:
        ValueError: If topic name contains invalid characters.
    """
    _validate_topic_name(name)
    return topic_dir() / f"{name}.topic"


def write_topic(name: str, info: TopicInfo) -> Path:
    """Write a topic file atomically.

    Creates the topic directory if it does not exist.
    Uses atomic write (write to temp file + rename) to prevent
    ec-sub from reading a partially written file.

    Args:
        name: Topic name.
        info: Topic information to write.

    Returns:
        Path to the written topic file.

    Raises:
        ValueError: If topic name is invalid.
    """
    path = topic_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp file in same directory, then rename
    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w") as f:
            json.dump(info.to_dict(), f)
            f.write("\n")
        # os.replace is atomic on POSIX and Windows
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up temp file on any failure
        tmp_path.unlink(missing_ok=True)
        raise

    return path


def read_topic(name: str) -> TopicInfo:
    """Read a topic file.

    Args:
        name: Topic name.

    Returns:
        TopicInfo from the topic file.

    Raises:
        FileNotFoundError: If topic file does not exist.
        ValueError: If topic name is invalid or file content is invalid.
    """
    path = topic_path(name)
    with open(path, "r") as f:
        data = json.load(f)
    return TopicInfo.from_dict(data)


def remove_topic(name: str) -> None:
    """Remove a topic file if it exists.

    Args:
        name: Topic name.
    """
    path = topic_path(name)
    path.unlink(missing_ok=True)


def is_process_alive(pid: int) -> bool:
    """Check if a process with the given PID is alive.

    Args:
        pid: Process ID to check.

    Returns:
        True if the process exists, False otherwise.
    """
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _validate_topic_name(name: str) -> None:
    """Validate topic name.

    Args:
        name: Topic name to validate.

    Raises:
        ValueError: If name is empty or contains invalid characters.
    """
    if not name:
        raise ValueError("Topic name must not be empty")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
    if not set(name.lower()).issubset(allowed):
        raise ValueError(
            f"Topic name must contain only alphanumeric, hyphen, "
            f"or underscore characters, got: {name!r}"
        )
