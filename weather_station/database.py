import logging
import traceback
from typing import Optional
from contextlib import contextmanager

import psycopg2
from psycopg2.pool import SimpleConnectionPool

from weather_station.logger import get_logger
from weather_station.types import WeatherData, Settings


class DatabaseManager:
    def __init__(self, settings: Settings) -> None:
        self.settings: Settings = settings
        self.logger: logging.Logger = get_logger(settings)
        self.pool: Optional[SimpleConnectionPool] = None
        self.logger.debug("Database manager initialized")

    def _create_pool(self) -> SimpleConnectionPool:
        """Create a connection pool for database operations"""
        return SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=self.settings["database_host"],
            port=self.settings["database_port"],
            dbname=self.settings["database_name"],
            user=self.settings["database_user"],
            password=self.settings["database_password"]
        )

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        if self.pool is None:
            self.pool = self._create_pool()

        connection = None
        try:
            connection = self.pool.getconn()
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                self.pool.putconn(connection)

    def connect(self) -> bool:
        """Establish connection to the database"""
        try:
            self.logger.info(
                f"Connecting to database at {self.settings['database_host']}:{self.settings['database_port']}")

            # Test the connection pool
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()

            self.logger.info("Successfully connected to database")
            return True
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            self.logger.debug(traceback.format_exc())
            return False

    def is_connected(self) -> bool:
        """Check if the database is connected"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            return True
        except Exception as e:
            self.logger.warning(f"Database connection check failed: {e}")
            return False

    def save_data(self, data: WeatherData) -> bool:
        """Save data to PostgreSQL database"""
        try:
            # Check if we have a valid connection first
            if not self.is_connected():
                self.logger.warning("Cannot save data: no database connection")
                return False

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    query: str = f"""
                    INSERT INTO {self.settings["database_table"]} (
                        datetime,
                        wind_speed,
                        wind_direction,
                        wind_min1_max,
                        wind_min1_avg,
                        wind_min1_dir,
                        wind_foreveremax,
                        temperature1,
                        temperature2,
                        humidity,
                        pressure,
                        avg_pressure,
                        rain,
                        billenes,
                        "end"
                    ) VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """

                    datetime_str: str = f"{data['date']} {data['time']}"

                    self.logger.debug(f"Executing database insert for datetime: {datetime_str}")

                    cursor.execute(query, (
                        datetime_str,
                        data.get("wind_speed"),
                        data.get("wind_direction"),
                        data.get("wind_min1_max"),
                        data.get("wind_min1_avg"),
                        data.get("wind_min1_dir"),
                        data.get("wind_forever_max"),
                        data.get("temperature1"),
                        data.get("temperature2"),
                        data.get("humidity"),
                        data.get("pressure"),
                        data.get("avg_pressure"),
                        data.get("rain"),
                        data.get("billenes"),
                        data.get("end")
                    ))

                    conn.commit()
                    self.logger.debug("Database insert successful")
                    return True

        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
            self.logger.debug(traceback.format_exc())
            return False

    def __del__(self):
        """Cleanup method to close the connection pool"""
        if self.pool:
            self.pool.closeall()
            self.logger.debug("Database connection pool closed")
