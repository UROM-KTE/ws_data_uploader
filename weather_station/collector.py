import datetime
import json
import logging
import signal
import time
import traceback
from typing import Dict, List, Any

import requests
import schedule

from weather_station.database import DatabaseManager
from weather_station.local_storage import LocalStorageManager
from weather_station.logger import get_logger
from weather_station.types import WeatherData, Settings


class WeatherCollector:
    def __init__(self, config_path: str) -> None:
        with open(config_path, 'r') as f:
            self.settings: Settings = json.load(f)

        self.logger: logging.Logger = get_logger(self.settings)
        self.logger.info("Weather collector initializing")

        self.running: bool = False

        try:
            self.db_manager: DatabaseManager = DatabaseManager(self.settings)
            self.local_storage: LocalStorageManager = LocalStorageManager(settings=self.settings)
            self.logger.info("Weather collector initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            self.logger.debug(traceback.format_exc())
            raise

    def collect_data(self) -> None:
        """Collect data from the weather station and store it"""
        self.logger.debug("Starting data collection")
        timestamp: datetime.datetime = datetime.datetime.now()

        try:
            self.logger.debug(f"Requesting data from weather station at {self.settings['station_ip']}")

            try:
                wind_response: requests.Response = requests.get(
                    f"http://{self.settings['station_ip']}/wind.json",
                    timeout=10
                )
                wind_response.raise_for_status()
                wind_data: Dict[str, Any] = wind_response.json()
                self.logger.debug("Successfully retrieved wind data")
            except requests.RequestException as e:
                self.logger.error(f"Error retrieving wind data: {e}")
                return

            try:
                sensors_response: requests.Response = requests.get(
                    f"http://{self.settings['station_ip']}/sensors.json",
                    timeout=10
                )
                sensors_response.raise_for_status()
                sensors_data: Dict[str, Any] = sensors_response.json()
                self.logger.debug("Successfully retrieved sensor data")
            except requests.RequestException as e:
                self.logger.error(f"Error retrieving sensor data: {e}")
                return

            data: WeatherData = {
                "date": timestamp.strftime("%Y-%m-%d"),
                "time": timestamp.strftime("%H:%M:%S"),
                "wind_speed": wind_data.get("speed"),
                "wind_direction": wind_data.get("dir"),
                "wind_min1_max": wind_data.get("min1max"),
                "wind_min1_avg": wind_data.get("min1avgspeed"),
                "wind_min1_dir": wind_data.get("min1dir"),
                "wind_forever_max": wind_data.get("forevermax"),
                "temperature1": sensors_data.get("hom"),
                "temperature2": sensors_data.get("hom2"),
                "humidity": sensors_data.get("rh"),
                "pressure": sensors_data.get("p"),
                "avg_pressure": sensors_data.get("ap"),
                "rain": sensors_data.get("csap"),
                "billenes": sensors_data.get("billenes"),
                "end": sensors_data.get("end"),
            }

            self.logger.debug(f"Collected data: {data}")

            if self.db_manager.is_connected():
                self.logger.debug("Database connected, attempting to save data")
                success: bool = self.db_manager.save_data(data)
                if success:
                    self.logger.info("Data saved to database successfully")
                else:
                    self.logger.warning("Failed to save to database, falling back to local storage")
                    self.local_storage.save_data(data)
            else:
                self.logger.warning("Database not connected, saving to local storage")
                self.local_storage.save_data(data)

            self.sync_pending_data()

        except Exception as e:
            self.logger.error(f"Error in data collection: {e}")
            self.logger.debug(traceback.format_exc())

    def sync_pending_data(self) -> None:
        """Try to sync any locally stored data to the database"""
        try:
            if not self.db_manager.is_connected():
                self.logger.debug("Database not connected, skipping sync")
                return

            pending_data: List[WeatherData] = self.local_storage.get_pending_data()
            if not pending_data:
                self.logger.debug("No pending data to sync")
                return

            self.logger.info(f"Attempting to sync {len(pending_data)} records from local storage")
            synced_count: int = 0

            for data in pending_data:
                if self.db_manager.save_data(data):
                    self.local_storage.mark_as_synced(data['id'])
                    synced_count += 1

            self.logger.info(f"Successfully synced {synced_count}/{len(pending_data)} records")

        except Exception as e:
            self.logger.error(f"Error syncing pending data: {e}")
            self.logger.debug(traceback.format_exc())

    def run_scheduler(self) -> None:
        """Run the collector on a schedule"""
        self.logger.info("Starting weather collector scheduler")

        self.running = True

        def signal_handler(sig: int, _frame: Any) -> None:
            self.logger.info(f"Received signal {sig}, shutting down gracefully...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        schedule.every(1).minutes.do(self.collect_data)
        self.logger.info("Scheduled data collection every 1 minute")

        self.logger.info("Performing initial data collection")
        self.collect_data()

        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                self.logger.debug(traceback.format_exc())
                time.sleep(5)  # Wait a bit before retrying

        self.logger.info("Weather collector stopped")


if __name__ == "__main__":
    collector: WeatherCollector = WeatherCollector("settings.json")
    collector.run_scheduler()
