import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import connection as db_connection
from repositories.telemetry_repository import (
    save_telemetry,
    get_latest_telemetry,
    get_telemetry_by_device,
)


def valid_payload():
    return {
        "device_id": "esp32_station_01",
        "timestamp": 1729000000,
        "sensors": {
            "soil_moisture_pct": 45.2,
            "soil_temperature_c": 22.4,
            "soil_ph": 6.8,
            "nitrogen_mg_kg": None,
            "phosphorus_mg_kg": None,
            "potassium_mg_kg": None,
        },
        "actuators": {
            "pump_state": False,
        },
    }


class TestTelemetryRepository(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_telemetry.db"

        self.path_patcher = patch.object(
            db_connection,
            "DATABASE_PATH",
            self.db_path,
        )
        self.path_patcher.start()

        self.repository_path_patcher = patch(
            "repositories.telemetry_repository.initialize_database",
            db_connection.initialize_database,
        )
        self.repository_path_patcher.start()

        db_connection.initialize_database()

    def tearDown(self):
        self.path_patcher.stop()
        self.repository_path_patcher.stop()
        self.temp_dir.cleanup()

    def test_save_and_retrieve_telemetry(self):
        save_telemetry(valid_payload())

        readings = get_latest_telemetry()

        self.assertEqual(len(readings), 1)
        self.assertEqual(readings[0]["device_id"], "esp32_station_01")
        self.assertEqual(readings[0]["soil_moisture_pct"], 45.2)
        self.assertEqual(readings[0]["pump_state"], 0)

    def test_nullable_npk_values_are_saved(self):
        save_telemetry(valid_payload())

        reading = get_latest_telemetry()[0]

        self.assertIsNone(reading["nitrogen_mg_kg"])
        self.assertIsNone(reading["phosphorus_mg_kg"])
        self.assertIsNone(reading["potassium_mg_kg"])

    def test_filter_readings_by_device(self):
        first = valid_payload()
        second = valid_payload()
        second["device_id"] = "esp32_station_02"

        save_telemetry(first)
        save_telemetry(second)

        readings = get_telemetry_by_device("esp32_station_02")

        self.assertEqual(len(readings), 1)
        self.assertEqual(readings[0]["device_id"], "esp32_station_02")

    def test_duplicate_device_timestamp_is_rejected(self):
        save_telemetry(valid_payload())

        with self.assertRaises(RuntimeError):
            save_telemetry(valid_payload())

    def test_data_persists_after_reopening_database(self):
        save_telemetry(valid_payload())

        # Close the connection by opening and closing a fresh one.
        connection = db_connection.get_connection()
        connection.close()

        readings = get_latest_telemetry()

        self.assertEqual(len(readings), 1)
        self.assertEqual(readings[0]["timestamp"], 1729000000)

    def test_invalid_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            get_latest_telemetry(limit=0)


if __name__ == "__main__":
    unittest.main()
  
