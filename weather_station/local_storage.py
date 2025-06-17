import json
import logging
import sqlite3
import traceback
import uuid
from typing import List, Optional
from contextlib import contextmanager

from weather_station.logger import get_logger
from weather_station.types import WeatherData, Settings


class LocalStorageManager:
    def __init__(self, db_path: str = "local_cache.db", settings: Optional[Settings] = None) -> None:
        self.db_path: str = db_path
        self.settings: Settings = settings or {}
        self.logger: logging.Logger = get_logger(self.settings)
        self.logger.debug(f"Local storage manager initialized with DB path: {db_path}")
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Context manager for SQLite connections"""
        connection = None
        try:
            connection = sqlite3.connect(self.db_path)
            # Enable foreign keys and set timeout
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                connection.close()

    def init_db(self) -> None:
        """Initialize the local SQLite database"""
        try:
            self.logger.debug("Initializing local SQLite database")
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS weather_data
                    (
                        id TEXT PRIMARY KEY,
                        data TEXT,
                        synced INTEGER DEFAULT 0,
                        timestamp TEXT
                    )
                ''')
                conn.commit()
                cursor.close()
            self.logger.info("Local SQLite database initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing local database: {e}")
            self.logger.debug(traceback.format_exc())
            raise

    def save_data(self, data: WeatherData) -> bool:
        """Save data to local storage"""
        try:
            self.logger.debug(f"Saving data to local storage: {data}")
            data_id: str = str(uuid.uuid4())
            data_json: str = json.dumps(data)

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO weather_data (id, data, timestamp) VALUES (?, ?, datetime('now'))",
                    (data_id, data_json)
                )
                conn.commit()
                cursor.close()

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
            results: List[WeatherData] = []

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, data FROM weather_data WHERE synced = 0 ORDER BY timestamp ASC LIMIT ?",
                    (limit,)
                )

                for row in cursor.fetchall():
                    try:
                        data: WeatherData = json.loads(row[1])
                        data['id'] = row[0]
                        results.append(data)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Invalid JSON in record {row[0]}: {e}")
                        # Mark corrupted record as synced to avoid repeated errors
                        self._mark_corrupted_record(row[0])

                cursor.close()

            self.logger.info(f"Retrieved {len(results)} pending records from local storage")
            return results
        except Exception as e:
            self.logger.error(f"Error fetching pending records from local storage: {e}")
            self.logger.debug(traceback.format_exc())
            return []

    def mark_as_synced(self, data_id: str) -> bool:
        """Mark a record as successfully synced"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE weather_data SET synced = 1 WHERE id = ?",
                    (data_id,)
                )
                conn.commit()
                cursor.close()

            self.logger.debug(f"Record {data_id} marked as synced")
            return True
        except Exception as e:
            self.logger.error(f"Error marking record {data_id} as synced: {e}")
            self.logger.debug(traceback.format_exc())
            return False

    def _mark_corrupted_record(self, data_id: str) -> None:
        """Mark a corrupted record as synced to prevent repeated errors"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE weather_data SET synced = 1 WHERE id = ?",
                    (data_id,)
                )
                conn.commit()
                cursor.close()
            self.logger.warning(f"Corrupted record {data_id} marked as synced to prevent repeated errors")
        except Exception as e:
            self.logger.error(f"Error marking corrupted record {data_id}: {e}")

    def cleanup_old_records(self, days_to_keep: int = 30) -> int:
        """Clean up old synced records to prevent database bloat"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM weather_data WHERE synced = 1 AND timestamp < datetime('now', '-{} days')".format(days_to_keep)
                )
                deleted_count = cursor.rowcount
                conn.commit()
                cursor.close()

            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old synced records")
            return deleted_count
        except Exception as e:
            self.logger.error(f"Error cleaning up old records: {e}")
            return 0

    def get_database_stats(self) -> dict:
        """Get database statistics for monitoring"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM weather_data")
                total_records = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM weather_data WHERE synced = 0")
                pending_records = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM weather_data WHERE synced = 1")
                synced_records = cursor.fetchone()[0]

                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM weather_data")
                time_range = cursor.fetchone()

                cursor.close()

            return {
                'total_records': total_records,
                'pending_records': pending_records,
                'synced_records': synced_records,
                'oldest_record': time_range[0] if time_range[0] else None,
                'newest_record': time_range[1] if time_range[1] else None
            }
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}
