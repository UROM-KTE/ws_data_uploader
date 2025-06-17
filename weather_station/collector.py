import datetime
import json
import logging
import signal
import time
import traceback
import gc
import psutil
from typing import Dict, List, Any, Optional

import requests
import schedule

from weather_station.database import DatabaseManager
from weather_station.local_storage import LocalStorageManager
from weather_station.logger import get_logger
from weather_station.types import WeatherData, Settings


class ResourceMonitor:
    """Monitor system resources and perform cleanup when needed"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.process = psutil.Process()
        self.memory_threshold = 100 * 1024 * 1024  # 100MB
        self.last_cleanup = time.time()
        self.cleanup_interval = 3600  # 1 hour

    def check_resources(self) -> bool:
        """Check if resource cleanup is needed"""
        try:
            memory_info = self.process.memory_info()
            current_time = time.time()

            # Check memory usage
            if memory_info.rss > self.memory_threshold:
                self.logger.warning(f"High memory usage detected: {memory_info.rss / 1024 / 1024:.1f}MB")
                return True

            # Periodic cleanup
            if current_time - self.last_cleanup > self.cleanup_interval:
                self.logger.debug("Performing periodic resource cleanup")
                return True

            return False
        except Exception as e:
            self.logger.error(f"Error checking resources: {e}")
            return False

    def perform_cleanup(self) -> None:
        """Perform resource cleanup"""
        try:
            # Force garbage collection
            collected = gc.collect()
            self.logger.debug(f"Garbage collection freed {collected} objects")

            # Update last cleanup time
            self.last_cleanup = time.time()

        except Exception as e:
            self.logger.error(f"Error during resource cleanup: {e}")


class WeatherCollector:
    def __init__(self, config_path: str) -> None:
        with open(config_path, 'r') as f:
            self.settings: Settings = json.load(f)

        self.logger: logging.Logger = get_logger(self.settings)
        self.logger.info("Weather collector initializing")

        self.running: bool = False

        # Initialize HTTP session for connection reuse
        self.session: requests.Session = requests.Session()
        self.session.timeout = 10

        # Initialize resource monitor
        self.resource_monitor: ResourceMonitor = ResourceMonitor(self.logger)

        try:
            self.db_manager: DatabaseManager = DatabaseManager(self.settings)
            self.local_storage: LocalStorageManager = LocalStorageManager(settings=self.settings)
            self.logger.info("Weather collector initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            self.logger.debug(traceback.format_exc())
            raise

    def _make_request(self, url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Make HTTP request with proper error handling and retry logic"""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                self.logger.warning(f"Request attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    self.logger.error(f"All request attempts failed for {url}")
                    return None
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON response from {url}: {e}")
                return None

    def collect_data(self) -> None:
        """Collect data from the weather station and store it"""
        self.logger.debug("Starting data collection")
        timestamp: datetime.datetime = datetime.datetime.now()
        missing_json_counter = 0

        try:
            self.logger.debug(f"Requesting data from weather station at {self.settings['station_ip']}")

            # Collect wind data
            wind_data: Optional[Dict[str, Any]] = self._make_request(
                f"http://{self.settings['station_ip']}/wind.json"
            )

            if wind_data is None:
                self.logger.error("Failed to retrieve wind data")
                missing_json_counter += 1
                wind_data = {
                    "speed": None,
                    "dir": None,
                    "min1max": None,
                    "min1avgspeed": None,
                    "min1dir": None,
                    "forevermax": None
                }
            else:
                self.logger.debug("Successfully retrieved wind data")

            # Collect sensor data
            sensors_data: Optional[Dict[str, Any]] = self._make_request(
                f"http://{self.settings['station_ip']}/sensors.json"
            )

            if sensors_data is None:
                self.logger.error("Failed to retrieve sensor data")
                missing_json_counter += 1
                sensors_data = {
                    "hom": None,
                    "hom2": None,
                    "rh": None,
                    "p": None,
                    "ap": None,
                    "csap": None,
                    "billenes": None,
                    "end": None
                }
            else:
                self.logger.debug("Successfully retrieved sensor data")

            if missing_json_counter >= 2:
                self.logger.error("Failed to retrieve data from weather station, aborting collection")
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
                # Check if resource cleanup is needed
                if self.resource_monitor.check_resources():
                    self.resource_monitor.perform_cleanup()

                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                self.logger.debug(traceback.format_exc())
                time.sleep(5)  # Wait a bit before retrying

        self.logger.info("Weather collector stopped")

        # Cleanup on shutdown
        self._cleanup()

    def _cleanup(self) -> None:
        """Cleanup resources on shutdown"""
        try:
            # Close HTTP session
            if self.session:
                self.session.close()
                self.logger.debug("HTTP session closed")

            # Perform final resource cleanup
            self.resource_monitor.perform_cleanup()

            # Clean up old local storage records
            deleted_count = self.local_storage.cleanup_old_records()
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old records during shutdown")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        self._cleanup()


if __name__ == "__main__":
    collector: WeatherCollector = WeatherCollector("settings.json")
    collector.run_scheduler()
