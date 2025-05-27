import os
import sys
from typing import List, Any

import servicemanager
import win32event
import win32service
import win32serviceutil

from weather_station.collector import WeatherCollector


class WeatherService(win32serviceutil.ServiceFramework):
    _svc_name_: str = "WeatherStationService"
    _svc_display_name_: str = "Weather Station Data Collector"

    def __init__(self, args: List[str]) -> None:
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        service_dir: str = os.path.dirname(os.path.abspath(sys.argv[0]))
        config_path: str = os.path.join(service_dir, "settings.json")

        self.collector: WeatherCollector = WeatherCollector(config_path)

    def SvcStop(self) -> None:
        """Called when the service is asked to stop"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.collector.running = False

    def SvcDoRun(self) -> None:
        """Called when the service is asked to start"""
        pid_current = getattr(servicemanager, 'PID_CURRENT', 0)

        message: Any = "Weather Station Service Starting"
        
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            pid_current,
            message
        )
        self.collector.run_scheduler()

    def stop_service(self) -> None:
        """Alias for SvcStop for better code readability"""
        self.SvcStop()

    def run_weather_service(self) -> None:
        """Alias for SvcDoRun for better code readability"""
        self.SvcDoRun()
