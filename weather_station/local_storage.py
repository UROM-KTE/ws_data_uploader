import json
import logging
import sqlite3
import traceback
import uuid
from typing import List, Optional

from weather_station.logger import get_logger
from weather_station.types import WeatherData, Settings


class LocalStorageManager:
    def __init__(self, db_path: str = "local_cache.db", settings: Optional[Settings] = None) -> None:
        self.db_path: str = db_path

        self.settings: Settings = settings or {}

        self.logger: logging.Logger = get_logger(self.settings)
        self.logger.debug(f"Local storage manager initialized with DB path: {db_path}")

        self.init_db()

    def init_db(self) -> None:
        """Initialize the local SQLite database"""
        try:
            self.logger.debug("Initializing local SQLite database")
            conn: sqlite3.Connection = sqlite3.connect(self.db_path)
            cursor: sqlite3.Cursor = conn.cursor()

            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS weather_data
                           (
                               id
                               TEXT
                               PRIMARY
                               KEY,
                               data
                               TEXT,
                               synced
                               INTEGER
                               DEFAULT
                               0,
                               timestamp
                               TEXT
                           )
                           ''')

            conn.commit()
            conn.close()
            self.logger.info("Local SQLite database initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing local database: {e}")
            self.logger.debug(traceback.format_exc())
            raise

    def save_data(self, data: WeatherData) -> bool:
        """Save data to local storage"""
        try:
            self.logger.debug(f"Saving data to local storage: {data}")
            conn: sqlite3.Connection = sqlite3.connect(self.db_path)
            cursor: sqlite3.Cursor = conn.cursor()

            data_id: str = str(uuid.uuid4())

            data_json: str = json.dumps(data)

            cursor.execute(
                "INSERT INTO weather_data (id, data, timestamp) VALUES (?, ?, datetime('now'))",
                (data_id, data_json)
            )

            conn.commit()
            conn.close()
            self.logger.info(f"Data saved to local storage with ID: {data_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving to local storage: {e}")
            self.logger.debug(traceback.format_exc())
            return False

    def get_pending_data(self, limit: int = 100) -> List[WeatherData]:
        """Get data that hasn't been synced yet"""
        try:
            self.logger.debug(f"Fetching up to {limit} pending records from local storage")
            conn: sqlite3.Connection = sqlite3.connect(self.db_path)
            cursor: sqlite3.Cursor = conn.cursor()

            cursor.execute(
                "SELECT id, data FROM weather_data WHERE synced = 0 ORDER BY timestamp ASC LIMIT ?",
                (limit,)
            )

            results: List[WeatherData] = []
            for row in cursor.fetchall():
                data: WeatherData = json.loads(row[1])
                data['id'] = row[0]
                results.append(data)

            conn.close()
            self.logger.info(f"Retrieved {len(results)} pending records from local storage")
            return results
        except Exception as e:
            self.logger.error(f"Error fetching pending records from local storage: {e}")
            self.logger.debug(traceback.format_exc())
            return []

    def mark_as_synced(self, data_id: str) -> bool:
        """Mark a record as successfully synced"""
        try:
            conn: sqlite3.Connection = sqlite3.connect(self.db_path)
            cursor: sqlite3.Cursor = conn.cursor()

            cursor.execute(
                "UPDATE weather_data SET synced = 1 WHERE id = ?",
                (data_id,)
            )

            conn.commit()
            conn.close()
            self.logger.debug(f"Record {data_id} marked as synced")
            return True
        except Exception as e:
            self.logger.error(f"Error marking record {data_id} as synced: {e}")
            self.logger.debug(traceback.format_exc())
            return False
