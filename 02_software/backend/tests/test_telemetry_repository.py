import json
import os
import subprocess
import sys
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
        self.repository_path_patcher.stop()
        self.path_patcher.stop()
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
        second["timestamp"] += 1

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

        connection = db_connection.get_connection()
        connection.close()

        readings = get_latest_telemetry()

        self.assertEqual(len(readings), 1)
        self.assertEqual(readings[0]["timestamp"], 1729000000)

    def test_invalid_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            get_latest_telemetry(limit=0)

        with self.assertRaises(ValueError):
            get_telemetry_by_device("esp32_station_01", limit=0)

    def test_invalid_pump_state_is_rejected(self):
        payload = valid_payload()
        payload["actuators"]["pump_state"] = 1

        with self.assertRaises(ValueError):
            save_telemetry(payload)

    def test_invalid_telemetry_is_not_saved(self):
        payload = valid_payload()
        payload["sensors"]["soil_ph"] = 20

        with self.assertRaises(ValueError):
            save_telemetry(payload)

        self.assertEqual(get_latest_telemetry(), [])

    def test_data_persists_after_python_restart(self):
        payload = valid_payload()
        save_telemetry(payload)

        script = """
import json
from database.connection import initialize_database
from repositories.telemetry_repository import get_latest_telemetry

initialize_database()
print(json.dumps(get_latest_telemetry()))
"""

        env = os.environ.copy()
        env["TELEMETRY_DB_PATH"] = str(self.db_path)

        backend_dir = Path(__file__).resolve().parents[1]

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        readings = json.loads(result.stdout)

        self.assertEqual(len(readings), 1)

        reading = readings[0]
        self.assertEqual(reading["device_id"], payload["device_id"])
        self.assertEqual(reading["timestamp"], payload["timestamp"])
        self.assertEqual(reading["soil_moisture_pct"], 45.2)
        self.assertEqual(reading["soil_temperature_c"], 22.4)
        self.assertEqual(reading["soil_ph"], 6.8)
        self.assertIsNone(reading["nitrogen_mg_kg"])
        self.assertIsNone(reading["phosphorus_mg_kg"])
        self.assertIsNone(reading["potassium_mg_kg"])
        self.assertEqual(reading["pump_state"], 0)


if __name__ == "__main__":
    unittest.main()
