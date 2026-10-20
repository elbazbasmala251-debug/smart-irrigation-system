import os
import sqlite3
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]

DATABASE_PATH = Path(
    os.getenv(
        "TELEMETRY_DB_PATH",
        str(BACKEND_DIR / "telemetry.db"),
    )
)


def get_connection():
    """Open a connection to the SQLite database."""
    try:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(
            str(DATABASE_PATH),
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        return connection

    except (sqlite3.Error, OSError) as exc:
        raise RuntimeError(
            f"Could not connect to database: {exc}"
        ) from exc


def initialize_database():
    """Create the telemetry table if it does not exist."""
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                soil_moisture_pct REAL NOT NULL,
                soil_temperature_c REAL NOT NULL,
                soil_ph REAL NOT NULL,
                nitrogen_mg_kg REAL,
                phosphorus_mg_kg REAL,
                potassium_mg_kg REAL,
                pump_state INTEGER NOT NULL
                    CHECK (pump_state IN (0, 1)),
                UNIQUE (device_id, timestamp)
            )
            """
        )
        connection.commit()

    except sqlite3.Error as exc:
        connection.rollback()
        raise RuntimeError(
            f"Could not initialize database: {exc}"
        ) from exc

    finally:
        connection.close()
  
