"""Tests for NdjsonReader and NdjsonWriter."""

import io
import json
from typing import Any

import pytest

from lib.common.ndjson import NdjsonReader, NdjsonWriter


class TestNdjsonReader:
    """Tests for NdjsonReader."""

    def test_read_single_line(self) -> None:
        """Test reading a single JSON line."""
        data = '{"name": "test", "value": 42}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        records = list(reader)
        
        assert len(records) == 1
        assert records[0] == {"name": "test", "value": 42}

    def test_read_multiple_lines(self) -> None:
        """Test reading multiple JSON lines."""
        data = '{"id": 1}\n{"id": 2}\n{"id": 3}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        records = list(reader)
        
        assert len(records) == 3
        assert records[0] == {"id": 1}
        assert records[1] == {"id": 2}
        assert records[2] == {"id": 3}

    def test_skip_empty_lines(self) -> None:
        """Test that empty lines are skipped."""
        data = '{"id": 1}\n\n{"id": 2}\n\n\n{"id": 3}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        records = list(reader)
        
        assert len(records) == 3
        assert records[0] == {"id": 1}
        assert records[1] == {"id": 2}
        assert records[2] == {"id": 3}

    def test_whitespace_only_lines_raise_error(self) -> None:
        """Test that whitespace-only lines are treated as invalid JSON."""
        data = '{"id": 1}\n   \n{"id": 2}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        
        with pytest.raises(ValueError) as exc_info:
            list(reader)
        
        assert "Invalid JSON at line 2" in str(exc_info.value)

    def test_malformed_json_raises_error(self) -> None:
        """Test that malformed JSON raises ValueError with line number."""
        data = '{"id": 1}\n{invalid json}\n{"id": 3}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        
        with pytest.raises(ValueError) as exc_info:
            list(reader)
        
        assert "Invalid JSON at line 2" in str(exc_info.value)

    def test_malformed_json_first_line(self) -> None:
        """Test error on malformed JSON in first line."""
        data = '{bad}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        
        with pytest.raises(ValueError) as exc_info:
            list(reader)
        
        assert "Invalid JSON at line 1" in str(exc_info.value)

    def test_type_preservation_int(self) -> None:
        """Test that integer values are preserved."""
        data = '{"count": 42}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        records = list(reader)
        
        assert isinstance(records[0]["count"], int)
        assert records[0]["count"] == 42

    def test_type_preservation_float(self) -> None:
        """Test that float values are preserved."""
        data = '{"value": 3.14159}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        records = list(reader)
        
        assert isinstance(records[0]["value"], float)
        assert records[0]["value"] == pytest.approx(3.14159)

    def test_type_preservation_string(self) -> None:
        """Test that string values are preserved."""
        data = '{"text": "hello world"}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        records = list(reader)
        
        assert isinstance(records[0]["text"], str)
        assert records[0]["text"] == "hello world"

    def test_type_preservation_nested_dict(self) -> None:
        """Test that nested dictionaries are preserved."""
        data = '{"outer": {"inner": "value"}}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        records = list(reader)
        
        assert isinstance(records[0]["outer"], dict)
        assert records[0]["outer"]["inner"] == "value"

    def test_type_preservation_list(self) -> None:
        """Test that arrays/lists are preserved."""
        data = '{"items": [1, 2, 3]}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        records = list(reader)
        
        assert isinstance(records[0]["items"], list)
        assert records[0]["items"] == [1, 2, 3]

    def test_type_preservation_bool_and_null(self) -> None:
        """Test that boolean and null values are preserved."""
        data = '{"active": true, "deleted": false, "value": null}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        records = list(reader)
        
        assert records[0]["active"] is True
        assert records[0]["deleted"] is False
        assert records[0]["value"] is None

    def test_iterator_protocol(self) -> None:
        """Test that NdjsonReader properly implements iterator protocol."""
        data = '{"id": 1}\n{"id": 2}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        
        iterator = iter(reader)
        record1 = next(iterator)
        assert record1 == {"id": 1}
        
        record2 = next(iterator)
        assert record2 == {"id": 2}
        
        with pytest.raises(StopIteration):
            next(iterator)

    def test_empty_stream(self) -> None:
        """Test reading from empty stream."""
        data = ''
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        records = list(reader)
        
        assert len(records) == 0

    def test_line_number_tracking_with_empty_lines(self) -> None:
        """Test that line numbers are correct even with empty lines."""
        data = '{"id": 1}\n\n{bad}\n'
        stream = io.StringIO(data)
        reader = NdjsonReader(stream)
        
        with pytest.raises(ValueError) as exc_info:
            list(reader)
        
        # Line 3 contains the malformed JSON (after empty line 2)
        assert "Invalid JSON at line 3" in str(exc_info.value)


class TestNdjsonWriter:
    """Tests for NdjsonWriter."""

    def test_write_single_record(self) -> None:
        """Test writing a single JSON record."""
        stream = io.StringIO()
        writer = NdjsonWriter(stream)
        
        writer.write({"id": 1, "name": "test"})
        
        output = stream.getvalue()
        assert output == '{"id": 1, "name": "test"}\n'

    def test_write_multiple_records(self) -> None:
        """Test writing multiple JSON records."""
        stream = io.StringIO()
        writer = NdjsonWriter(stream)
        
        writer.write({"id": 1})
        writer.write({"id": 2})
        writer.write({"id": 3})
        
        output = stream.getvalue()
        lines = output.strip().split('\n')
        
        assert len(lines) == 3
        assert json.loads(lines[0]) == {"id": 1}
        assert json.loads(lines[1]) == {"id": 2}
        assert json.loads(lines[2]) == {"id": 3}

    def test_write_adds_newline(self) -> None:
        """Test that write adds newline after each record."""
        stream = io.StringIO()
        writer = NdjsonWriter(stream)
        
        writer.write({"test": "value"})
        
        output = stream.getvalue()
        assert output.endswith('\n')

    def test_write_auto_flushes(self) -> None:
        """Test that write automatically flushes the stream."""
        stream = io.StringIO()
        writer = NdjsonWriter(stream)
        
        writer.write({"id": 1})
        
        # After write, content should be immediately available
        output = stream.getvalue()
        assert len(output) > 0
        assert json.loads(output.strip()) == {"id": 1}

    def test_write_preserves_types(self) -> None:
        """Test that write preserves JSON types."""
        stream = io.StringIO()
        writer = NdjsonWriter(stream)
        
        record: dict[str, Any] = {
            "int_val": 42,
            "float_val": 3.14,
            "str_val": "text",
            "bool_val": True,
            "null_val": None,
            "list_val": [1, 2, 3],
            "dict_val": {"nested": "value"}
        }
        
        writer.write(record)
        
        output = stream.getvalue()
        loaded = json.loads(output.strip())
        
        assert loaded["int_val"] == 42
        assert loaded["float_val"] == pytest.approx(3.14)
        assert loaded["str_val"] == "text"
        assert loaded["bool_val"] is True
        assert loaded["null_val"] is None
        assert loaded["list_val"] == [1, 2, 3]
        assert loaded["dict_val"] == {"nested": "value"}

    def test_write_complex_nested_structure(self) -> None:
        """Test writing complex nested structures."""
        stream = io.StringIO()
        writer = NdjsonWriter(stream)
        
        record: dict[str, Any] = {
            "data": {
                "samples": [1.0, 2.5, 3.1],
                "metadata": {
                    "device": "sensor-1",
                    "active": True
                }
            }
        }
        
        writer.write(record)
        
        output = stream.getvalue()
        loaded = json.loads(output.strip())
        
        assert loaded == record

    def test_write_empty_dict(self) -> None:
        """Test writing an empty dictionary."""
        stream = io.StringIO()
        writer = NdjsonWriter(stream)
        
        writer.write({})
        
        output = stream.getvalue()
        assert output == '{}\n'


class TestNdjsonRoundTrip:
    """Tests for round-trip write and read operations."""

    def test_round_trip_single_record(self) -> None:
        """Test writing and reading back a single record."""
        original = {"id": 1, "name": "test", "value": 3.14}
        
        # Write
        write_stream = io.StringIO()
        writer = NdjsonWriter(write_stream)
        writer.write(original)
        
        # Read
        write_stream.seek(0)
        reader = NdjsonReader(write_stream)
        records = list(reader)
        
        assert len(records) == 1
        assert records[0] == original

    def test_round_trip_multiple_records(self) -> None:
        """Test writing and reading back multiple records."""
        originals = [
            {"id": 1, "value": 10},
            {"id": 2, "value": 20},
            {"id": 3, "value": 30}
        ]
        
        # Write
        write_stream = io.StringIO()
        writer = NdjsonWriter(write_stream)
        for record in originals:
            writer.write(record)
        
        # Read
        write_stream.seek(0)
        reader = NdjsonReader(write_stream)
        records = list(reader)
        
        assert len(records) == 3
        assert records == originals

    def test_round_trip_complex_types(self) -> None:
        """Test round-trip with various data types."""
        original: dict[str, Any] = {
            "integers": [1, 2, 3],
            "floats": [1.1, 2.2, 3.3],
            "strings": ["a", "b", "c"],
            "booleans": [True, False],
            "null_value": None,
            "nested": {"deep": {"deeper": "value"}}
        }
        
        # Write
        write_stream = io.StringIO()
        writer = NdjsonWriter(write_stream)
        writer.write(original)
        
        # Read
        write_stream.seek(0)
        reader = NdjsonReader(write_stream)
        records = list(reader)
        
        assert records[0] == original
