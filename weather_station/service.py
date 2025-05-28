import json
import os
import sys
from typing import List

import win32event
import win32service
import win32serviceutil

from weather_station.collector import WeatherCollector
from weather_station.logger import get_logger


class WeatherService(win32serviceutil.ServiceFramework):
    _svc_name_: str = "WeatherStationService"
    _svc_display_name_: str = "Weather Station Data Collector"

    def __init__(self, args: List[str]) -> None:
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        service_dir: str = os.path.dirname(os.path.abspath(sys.argv[0]))
        config_path: str = os.path.join(service_dir, "settings.json")

        try:
            with open(config_path, 'r') as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {
                "log_type": "file",
                "log_level": "INFO",
                "log_file": os.path.join(service_dir, "weather_service.log"),
                "log_max_size": 5 * 1024 * 1024,  # 5MB
                "log_backup_count": 3
            }

        self.logger = get_logger(self.settings)
        self.logger.info("Service initializing")

        self.collector: WeatherCollector = WeatherCollector(config_path)

    def SvcStop(self) -> None:
        """Called when the service is asked to stop"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.collector.running = False
        self.logger.info("Service stop requested")

    def SvcDoRun(self) -> None:
        """Called when the service is asked to start"""
        self.logger.info("Weather Station Service Starting")
        self.collector.run_scheduler()

    def stop_service(self) -> None:
        """Alias for SvcStop for better code readability"""
        self.SvcStop()

    def run_weather_service(self) -> None:
        """Alias for SvcDoRun for better code readability"""
        self.SvcDoRun()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager_cmd = 'start'
    else:
        servicemanager_cmd = sys.argv[1]

    if servicemanager_cmd == 'install':
        win32serviceutil.HandleCommandLine(WeatherService)
    elif servicemanager_cmd == 'start':
        win32serviceutil.HandleCommandLine(WeatherService)
    elif servicemanager_cmd == 'stop':
        win32serviceutil.HandleCommandLine(WeatherService)
    elif servicemanager_cmd == 'remove':
        win32serviceutil.HandleCommandLine(WeatherService)
    else:
        win32serviceutil.HandleCommandLine(WeatherService)
