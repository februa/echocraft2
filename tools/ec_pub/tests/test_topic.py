"""Tests for lib/common/topic.py."""

import os

import pytest

from common.topic import (
    TopicInfo,
    topic_path,
    write_topic,
    read_topic,
    remove_topic,
    is_process_alive,
    _validate_topic_name,
)


class TestTopicInfo:
    """Tests for TopicInfo data class."""

    def test_round_trip(self):
        info = TopicInfo(port=12345, pid=9999)
        d = info.to_dict()
        assert d == {"port": 12345, "pid": 9999}
        restored = TopicInfo.from_dict(d)
        assert restored == info

    def test_from_dict_missing_key(self):
        with pytest.raises(KeyError):
            TopicInfo.from_dict({"port": 123})


class TestTopicName:
    """Tests for topic name validation."""

    def test_valid_names(self):
        for name in ["demo", "test-topic", "my_topic_123", "ABC"]:
            _validate_topic_name(name)  # should not raise

    def test_empty_name(self):
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_topic_name("")

    def test_invalid_characters(self):
        with pytest.raises(ValueError, match="alphanumeric"):
            _validate_topic_name("topic/name")


class TestTopicFile:
    """Tests for topic file write/read/remove with explicit_dir."""

    def test_write_and_read(self, tmp_path):
        info = TopicInfo(port=54321, pid=os.getpid())
        path = write_topic("test-topic", info, explicit_dir=str(tmp_path))

        assert path.exists()
        assert path.name == "test-topic.topic"

        loaded = read_topic("test-topic", explicit_dir=str(tmp_path))
        assert loaded == info

    def test_remove(self, tmp_path):
        info = TopicInfo(port=11111, pid=os.getpid())
        write_topic("removable", info, explicit_dir=str(tmp_path))

        remove_topic("removable", explicit_dir=str(tmp_path))
        assert not topic_path("removable", explicit_dir=str(tmp_path)).exists()

    def test_remove_nonexistent(self, tmp_path):
        remove_topic("nonexistent", explicit_dir=str(tmp_path))  # should not raise

    def test_read_nonexistent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_topic("nonexistent", explicit_dir=str(tmp_path))

    def test_atomic_write_overwrites(self, tmp_path):
        d = str(tmp_path)
        write_topic("overwrite", TopicInfo(port=1, pid=1), explicit_dir=d)
        write_topic("overwrite", TopicInfo(port=2, pid=2), explicit_dir=d)

        loaded = read_topic("overwrite", explicit_dir=d)
        assert loaded.port == 2

    def test_env_var_fallback(self, tmp_path, monkeypatch):
        """ECHOCRAFT_TOPIC_DIR env var is used when explicit_dir is None."""
        monkeypatch.setenv("ECHOCRAFT_TOPIC_DIR", str(tmp_path))

        info = TopicInfo(port=99999, pid=os.getpid())
        write_topic("env-test", info)

        loaded = read_topic("env-test")
        assert loaded == info


class TestProcessAlive:
    """Tests for is_process_alive."""

    def test_current_process_is_alive(self):
        assert is_process_alive(os.getpid())

    def test_nonexistent_pid(self):
        # PID 99999999 is very unlikely to exist
        assert not is_process_alive(99999999)
