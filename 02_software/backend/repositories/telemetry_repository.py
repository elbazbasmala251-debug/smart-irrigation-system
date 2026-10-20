import sqlite3

from database.connection import get_connection, initialize_database
from models.telemetry import Telemetry


def _validated_data(telemetry):
    """Validate telemetry using the existing Pydantic model."""
    try:
        if isinstance(telemetry, Telemetry):
            model = telemetry
        else:
            model = Telemetry.model_validate(telemetry)

        return model.model_dump()

    except Exception as exc:
        raise ValueError(
            f"Invalid telemetry data: {exc}"
        ) from exc


def save_telemetry(telemetry):
    """Validate and save one telemetry reading."""
    data = _validated_data(telemetry)

    sensors = data["sensors"]
    actuators = data["actuators"]

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO telemetry (
                device_id,
                timestamp,
                soil_moisture_pct,
                soil_temperature_c,
                soil_ph,
                nitrogen_mg_kg,
                phosphorus_mg_kg,
                potassium_mg_kg,
                pump_state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["device_id"],
                data["timestamp"],
                sensors["soil_moisture_pct"],
                sensors["soil_temperature_c"],
                sensors["soil_ph"],
                sensors["nitrogen_mg_kg"],
                sensors["phosphorus_mg_kg"],
                sensors["potassium_mg_kg"],
                int(actuators["pump_state"]),
            ),
        )
        connection.commit()

    except sqlite3.Error as exc:
        connection.rollback()
        raise RuntimeError(
            f"Could not save telemetry: {exc}"
        ) from exc

    finally:
        connection.close()


def get_latest_telemetry(limit=100):
    """Return the latest saved telemetry readings."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer.")

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM telemetry
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_telemetry_by_device(device_id, limit=100):
    """Return the latest readings for one device."""
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("device_id must be a non-empty string.")

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer.")

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM telemetry
            WHERE device_id = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (device_id, limit),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()
        
