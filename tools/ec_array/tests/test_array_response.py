"""Unit tests for ArrayResponse domain logic."""

import math
import pytest
from ec_array.array_response import ArrayResponse, Sensor
from ec_array.records import TransferRecord


class TestArrayResponseInit:
    """Tests for ArrayResponse initialization."""

    def test_parses_sensor_config_correctly(self):
        """ArrayResponse parses sensor configuration correctly."""
        sensors_config = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 1.0, "y": 2.0, "z": 3.0},
            {"id": 2, "x": -1.5, "y": 0.5, "z": 2.5},
        ]
        
        array_response = ArrayResponse(sensors_config, sound_speed=1500.0)
        
        assert len(array_response.sensors) == 3
        assert array_response.sensors[0].id == 0
        assert array_response.sensors[0].x == 0.0
        assert array_response.sensors[1].id == 1
        assert array_response.sensors[1].x == 1.0
        assert array_response.sensors[1].y == 2.0
        assert array_response.sensors[1].z == 3.0
        assert array_response.sound_speed == 1500.0


class TestComputeTransfers:
    """Tests for compute_transfers method."""

    def test_generates_one_transfer_per_sensor_for_source(self):
        """compute_transfers generates one TransferRecord per sensor for source records."""
        sensors_config = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": 1.0, "y": 0.0, "z": 0.0},
            {"id": 2, "x": 0.0, "y": 1.0, "z": 0.0},
        ]
        
        array_response = ArrayResponse(sensors_config, sound_speed=1500.0)
        
        source_record = {
            "type": "source",
            "source_id": 42,
            "freq": 1000.0,
            "sl": -120.0,
            "az": 0.0,
            "el": 0.0,
        }
        
        transfers = array_response.compute_transfers(source_record)
        
        assert len(transfers) == 3
        assert all(isinstance(t, TransferRecord) for t in transfers)
        assert transfers[0].source_id == 42
        assert transfers[1].source_id == 42
        assert transfers[2].source_id == 42

    def test_returns_empty_list_for_non_source_records(self):
        """compute_transfers returns empty list for non-source records."""
        sensors_config = [{"id": 0, "x": 0.0, "y": 0.0, "z": 0.0}]
        array_response = ArrayResponse(sensors_config)
        
        # Test noise record
        noise_record = {"type": "noise", "level": -80.0}
        assert array_response.compute_transfers(noise_record) == []
        
        # Test unknown record
        unknown_record = {"type": "unknown"}
        assert array_response.compute_transfers(unknown_record) == []
        
        # Test missing type
        missing_type = {"source_id": 1}
        assert array_response.compute_transfers(missing_type) == []


class TestDelayComputation:
    """Tests for delay computation accuracy."""

    def test_delay_for_source_at_zero_with_sensor_on_x_axis(self):
        """Delay computation: source at az=0, el=0 with sensor at (x, 0, 0)."""
        # Source at origin pointing along positive x-axis (az=0, el=0)
        # Sensor at (1.0, 0, 0) should have delay = 1.0 / 1500.0
        sensors_config = [{"id": 0, "x": 1.0, "y": 0.0, "z": 0.0}]
        array_response = ArrayResponse(sensors_config, sound_speed=1500.0)
        
        source_record = {
            "type": "source",
            "source_id": 0,
            "freq": 1000.0,
            "sl": -100.0,
            "az": 0.0,
            "el": 0.0,
        }
        
        transfers = array_response.compute_transfers(source_record)
        assert len(transfers) == 1
        
        expected_delay = 1.0 / 1500.0
        assert transfers[0].delay == pytest.approx(expected_delay, rel=1e-9)

    def test_delay_for_source_at_different_angles(self):
        """Delay computation respects azimuth and elevation angles."""
        # Place sensor at (0, 1, 0) - on y-axis
        # Steering at az=90, el=0 points along positive y-axis
        # So delay should be 1.0 / 1500.0
        sensors_config = [{"id": 0, "x": 0.0, "y": 1.0, "z": 0.0}]
        array_response = ArrayResponse(sensors_config, sound_speed=1500.0)
        
        source_record = {
            "type": "source",
            "source_id": 0,
            "freq": 1000.0,
            "sl": -100.0,
            "az": 90.0,
            "el": 0.0,
        }
        
        transfers = array_response.compute_transfers(source_record)
        expected_delay = 1.0 / 1500.0
        assert transfers[0].delay == pytest.approx(expected_delay, rel=1e-9)

    def test_delay_computation_respects_sound_speed(self):
        """Delay computation uses the configured sound speed."""
        sensors_config = [{"id": 0, "x": 3000.0, "y": 0.0, "z": 0.0}]
        
        # Test with sound_speed = 3000 m/s
        array_response = ArrayResponse(sensors_config, sound_speed=3000.0)
        
        source_record = {
            "type": "source",
            "source_id": 0,
            "freq": 1000.0,
            "sl": -100.0,
            "az": 0.0,
            "el": 0.0,
        }
        
        transfers = array_response.compute_transfers(source_record)
        expected_delay = 3000.0 / 3000.0  # = 1.0 second
        assert transfers[0].delay == pytest.approx(expected_delay, rel=1e-9)


class TestTransferRecord:
    """Tests for TransferRecord properties."""

    def test_transfer_record_is_frozen(self):
        """TransferRecord is frozen (immutable)."""
        transfer = TransferRecord(
            source_id=1,
            sensor_id=0,
            delay=0.001,
            loss_db=-120.0,
            freq=1000.0,
        )
        
        with pytest.raises(AttributeError):
            transfer.delay = 0.002

    def test_transfer_record_to_dict_has_transfer_type(self):
        """TransferRecord.to_dict() includes type='transfer'."""
        transfer = TransferRecord(
            source_id=5,
            sensor_id=3,
            delay=0.0015,
            loss_db=-125.0,
            freq=2000.0,
        )
        
        record_dict = transfer.to_dict()
        
        assert record_dict["type"] == "transfer"
        assert record_dict["source_id"] == 5
        assert record_dict["sensor_id"] == 3
        assert record_dict["delay"] == pytest.approx(0.0015)
        assert record_dict["loss_db"] == pytest.approx(-125.0)
        assert record_dict["freq"] == pytest.approx(2000.0)

    def test_transfer_record_default_type(self):
        """TransferRecord defaults to type='transfer'."""
        transfer = TransferRecord(
            source_id=1,
            sensor_id=0,
            delay=0.001,
            loss_db=-120.0,
            freq=1000.0,
        )
        
        assert transfer.type == "transfer"


class TestSensorClass:
    """Tests for Sensor dataclass."""

    def test_sensor_stores_position_and_id(self):
        """Sensor stores id, x, y, z coordinates."""
        sensor = Sensor(id=5, x=1.5, y=2.5, z=3.5)
        
        assert sensor.id == 5
        assert sensor.x == 1.5
        assert sensor.y == 2.5
        assert sensor.z == 3.5

    def test_sensor_is_frozen(self):
        """Sensor is frozen (immutable)."""
        sensor = Sensor(id=0, x=0.0, y=0.0, z=0.0)
        
        with pytest.raises(AttributeError):
            sensor.x = 1.0
