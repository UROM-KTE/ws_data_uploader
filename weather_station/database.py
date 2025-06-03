import logging
import traceback
from typing import Optional

import psycopg2

from weather_station.logger import get_logger
from weather_station.types import WeatherData, Settings


class DatabaseManager:
    def __init__(self, settings: Settings) -> None:
        self.settings: Settings = settings
        self.connection: Optional[psycopg2.extensions.connection] = None
        self.logger: logging.Logger = get_logger(settings)
        self.logger.debug("Database manager initialized")

    def connect(self) -> bool:
        """Establish connection to the database"""
        try:
            self.logger.info(
                f"Connecting to database at {self.settings['database_host']}:{self.settings['database_port']}")
            self.connection = psycopg2.connect(
                host=self.settings["database_host"],
                port=self.settings["database_port"],
                dbname=self.settings["database_name"],
                user=self.settings["database_user"],
                password=self.settings["database_password"]
            )
            self.logger.info("Successfully connected to database")
            return True
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            self.logger.debug(traceback.format_exc())
            self.connection = None
            return False

    def is_connected(self) -> bool:
        """Check if the database is connected"""
        if self.connection is None:
            self.logger.debug("No active connection, attempting to connect")
            return self.connect()

        try:
            if self.connection is not None:
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                self.logger.debug("Database connection verified")
                return True
            return False
        except Exception as e:
            self.logger.warning(f"Database connection check failed: {e}")
            self.connection = None
            return self.connect()

    def save_data(self, data: WeatherData) -> bool:
        """Save data to PostgreSQL database"""
        if not self.is_connected() or self.connection is None:
            self.logger.warning("Cannot save data: no database connection")
            return False

        try:
            cursor = self.connection.cursor()

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

            self.connection.commit()
            cursor.close()
            self.logger.debug("Database insert successful")
            return True

        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
            self.logger.debug(traceback.format_exc())

            if "connection" in str(e).lower():
                self.logger.info("Attempting to reconnect to database")
                self.connection = None
                self.is_connected()

            return False
