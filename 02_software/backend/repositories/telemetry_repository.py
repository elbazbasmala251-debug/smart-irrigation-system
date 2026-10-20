import sqlite3

from database.connection import get_connection, initialize_database


def save_telemetry(telemetry):
    """Save one telemetry reading to the database."""

    if hasattr(telemetry, "model_dump"):
        data = telemetry.model_dump()
    elif isinstance(telemetry, dict):
        data = telemetry
    else:
        raise ValueError(
            "Telemetry must be a model or dictionary."
        )

    try:
        sensors = data["sensors"]
        actuators = data["actuators"]

        initialize_database()
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
                    sensors.get("nitrogen_mg_kg"),
                    sensors.get("phosphorus_mg_kg"),
                    sensors.get("potassium_mg_kg"),
                    int(actuators["pump_state"]),
                ),
            )
            connection.commit()

        except sqlite3.Error:
            connection.rollback()
            raise

        finally:
            connection.close()

    except (sqlite3.Error, RuntimeError, KeyError, TypeError) as exc:
        raise RuntimeError(
            f"Could not save telemetry: {exc}"
        ) from exc


def get_latest_telemetry(limit=100):
    """Return the latest saved telemetry readings."""

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer.")

    try:
        initialize_database()
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

    except (sqlite3.Error, RuntimeError) as exc:
        raise RuntimeError(
            f"Could not retrieve telemetry: {exc}"
        ) from exc


def get_telemetry_by_device(device_id, limit=100):
    """Return the latest readings for one device."""

    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("device_id must be a non-empty string.")

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer.")

    try:
        initialize_database()
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

    except (sqlite3.Error, RuntimeError) as exc:
        raise RuntimeError(
            f"Could not retrieve telemetry for device {device_id}: {exc}"
        ) from exc
                      
