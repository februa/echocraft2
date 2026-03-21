"""NDJSON record type definitions and validation.

Defines the schema for each record type in the ECHOCRAFT pipeline and provides
validation functions. Record schemas are derived from ARCHITECTURE.md's type
field definition table.
"""

from typing import Any


# Schema: record_type -> set of required field names (excluding "type" itself)
RECORD_SCHEMAS: dict[str, set[str]] = {
    "source": {"freq", "sl", "az", "el"},
    "noise": {"nl"},
    "transfer": {"source_id", "sensor_id", "delay", "loss_db"},
    "spectrum": {"freq", "power_db", "time"},
    "bearing": {"azimuth", "level_db", "time"},
    "scalar": {"key", "value", "unit", "time"},
}


class RecordValidationError(ValueError):
    """Raised when a record fails validation.

    Attributes:
        record: The record that failed validation.
        reason: Human-readable description of the failure.
    """

    def __init__(self, reason: str, record: dict[str, Any] | None = None) -> None:
        self.record = record
        self.reason = reason
        super().__init__(reason)


def validate_record(record: dict[str, Any]) -> None:
    """Validate an NDJSON record against the schema.

    Checks that:
    1. The record has a "type" field.
    2. The "type" value is a known record type.
    3. All required fields for that type are present.

    Args:
        record: Parsed NDJSON record (dictionary).

    Raises:
        RecordValidationError: If validation fails.
    """
    if "type" not in record:
        raise RecordValidationError("Record missing 'type' field", record)

    record_type = record["type"]

    if record_type not in RECORD_SCHEMAS:
        raise RecordValidationError(
            f"Unknown record type: '{record_type}'", record
        )

    required = RECORD_SCHEMAS[record_type]
    missing = required - record.keys()

    if missing:
        raise RecordValidationError(
            f"Record type '{record_type}' missing required fields: "
            f"{', '.join(sorted(missing))}",
            record,
        )


def validate_record_type(record: dict[str, Any], expected_type: str) -> None:
    """Validate a record and check it matches an expected type.

    Convenience function for tools that only process specific record types.

    Args:
        record: Parsed NDJSON record.
        expected_type: The expected value of the "type" field.

    Raises:
        RecordValidationError: If validation fails or type doesn't match.
    """
    validate_record(record)

    if record["type"] != expected_type:
        raise RecordValidationError(
            f"Expected record type '{expected_type}', "
            f"got '{record['type']}'",
            record,
        )


def is_known_type(record: dict[str, Any]) -> bool:
    """Check if a record has a known type without raising.

    Useful for filter-style tools that pass through unknown record types.

    Args:
        record: Parsed NDJSON record.

    Returns:
        True if the record has a known "type" field, False otherwise.
    """
    return record.get("type") in RECORD_SCHEMAS
