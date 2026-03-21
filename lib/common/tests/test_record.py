"""Tests for NDJSON record validation."""

import pytest

from lib.common.record import (
    RECORD_SCHEMAS,
    RecordValidationError,
    is_known_type,
    validate_record,
    validate_record_type,
)


class TestRecordSchemas:
    """Tests for schema definitions."""

    def test_all_architecture_types_defined(self) -> None:
        """Verify all types from ARCHITECTURE.md are in the schema."""
        expected_types = {"source", "noise", "transfer", "spectrum", "bearing", "scalar"}
        assert set(RECORD_SCHEMAS.keys()) == expected_types

    def test_source_required_fields(self) -> None:
        assert RECORD_SCHEMAS["source"] == {"freq", "sl", "az", "el"}

    def test_noise_required_fields(self) -> None:
        assert RECORD_SCHEMAS["noise"] == {"nl"}

    def test_transfer_required_fields(self) -> None:
        assert RECORD_SCHEMAS["transfer"] == {"source_id", "sensor_id", "delay", "loss_db"}

    def test_spectrum_required_fields(self) -> None:
        assert RECORD_SCHEMAS["spectrum"] == {"freq", "power_db", "time"}

    def test_bearing_required_fields(self) -> None:
        assert RECORD_SCHEMAS["bearing"] == {"azimuth", "level_db", "time"}

    def test_scalar_required_fields(self) -> None:
        assert RECORD_SCHEMAS["scalar"] == {"key", "value", "unit", "time"}


class TestValidateRecord:
    """Tests for validate_record function."""

    def test_valid_source_record(self) -> None:
        record = {"type": "source", "freq": 100.0, "sl": 0.0, "az": 0.0, "el": 0.0}
        validate_record(record)  # Should not raise

    def test_valid_noise_record(self) -> None:
        record = {"type": "noise", "nl": -20.0}
        validate_record(record)

    def test_valid_transfer_record(self) -> None:
        record = {
            "type": "transfer",
            "source_id": 0,
            "sensor_id": 1,
            "delay": 0.001,
            "loss_db": -3.0,
        }
        validate_record(record)

    def test_valid_spectrum_record(self) -> None:
        record = {"type": "spectrum", "freq": 440.0, "power_db": -10.0, "time": 0.5}
        validate_record(record)

    def test_valid_bearing_record(self) -> None:
        record = {"type": "bearing", "azimuth": 45.0, "level_db": -5.0, "time": 1.0}
        validate_record(record)

    def test_valid_scalar_record(self) -> None:
        record = {"type": "scalar", "key": "snr", "value": 12.3, "unit": "dB", "time": 0.5}
        validate_record(record)

    def test_extra_fields_allowed(self) -> None:
        """Extra fields beyond required should not cause validation failure."""
        record = {
            "type": "source",
            "freq": 100.0,
            "sl": 0.0,
            "az": 0.0,
            "el": 0.0,
            "comment": "test source",
        }
        validate_record(record)  # Should not raise

    def test_missing_type_field(self) -> None:
        record = {"freq": 100.0, "sl": 0.0}
        with pytest.raises(RecordValidationError, match="missing 'type' field"):
            validate_record(record)

    def test_unknown_type(self) -> None:
        record = {"type": "unknown_type", "data": 123}
        with pytest.raises(RecordValidationError, match="Unknown record type"):
            validate_record(record)

    def test_missing_required_field(self) -> None:
        record = {"type": "source", "freq": 100.0, "sl": 0.0}
        # Missing az and el
        with pytest.raises(RecordValidationError, match="missing required fields"):
            validate_record(record)

    def test_error_lists_all_missing_fields(self) -> None:
        record = {"type": "source", "freq": 100.0}
        with pytest.raises(RecordValidationError) as exc_info:
            validate_record(record)
        # Should mention all missing fields
        msg = str(exc_info.value)
        assert "az" in msg
        assert "el" in msg
        assert "sl" in msg

    def test_error_preserves_record(self) -> None:
        record = {"type": "source", "freq": 100.0}
        with pytest.raises(RecordValidationError) as exc_info:
            validate_record(record)
        assert exc_info.value.record is record


class TestValidateRecordType:
    """Tests for validate_record_type function."""

    def test_matching_type(self) -> None:
        record = {"type": "source", "freq": 100.0, "sl": 0.0, "az": 0.0, "el": 0.0}
        validate_record_type(record, "source")  # Should not raise

    def test_mismatched_type(self) -> None:
        record = {"type": "noise", "nl": -20.0}
        with pytest.raises(RecordValidationError, match="Expected record type 'source'"):
            validate_record_type(record, "source")

    def test_validates_fields_before_type_check(self) -> None:
        """If fields are missing, that error should be raised."""
        record = {"type": "source", "freq": 100.0}
        with pytest.raises(RecordValidationError, match="missing required fields"):
            validate_record_type(record, "source")


class TestIsKnownType:
    """Tests for is_known_type function."""

    def test_known_types(self) -> None:
        for type_name in RECORD_SCHEMAS:
            assert is_known_type({"type": type_name}) is True

    def test_unknown_type(self) -> None:
        assert is_known_type({"type": "foobar"}) is False

    def test_missing_type(self) -> None:
        assert is_known_type({"data": 123}) is False

    def test_empty_record(self) -> None:
        assert is_known_type({}) is False
