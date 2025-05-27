import logging
import logging.handlers
import os
import platform
import socket
import sys
from logging.handlers import NTEventLogHandler
from typing import Optional

from weather_station.types import Settings


class LoggerSetup:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        """
        Initialize the logger based on settings.
        
        Settings should contain:
        - log_type: "file" or "syslog" or "both"
        - log_level: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        - log_file: path to the log file (if log_type is "file" or "both")
        - log_max_size: maximum size of the log file in bytes before rotation
        - log_backup_count: number of backup log files to keep
        - log_format: custom log format (optional)
        """
        self.settings: Settings = settings or {}
        self.logger: Optional[logging.Logger] = None
        self.setup_logger()

    def setup_logger(self) -> None:
        """Configure logger based on settings"""
        log_type: str = self.settings.get("log_type", "file")
        log_level_str: str = self.settings.get("log_level", "INFO")
        log_file: str = self.settings.get("log_file", "weather_station.log")
        log_max_size: int = self.settings.get("log_max_size", 5 * 1024 * 1024)  # 5MB default
        log_backup_count: int = self.settings.get("log_backup_count", 3)

        log_level: int = getattr(logging, log_level_str.upper(), logging.INFO)

        logger: logging.Logger = logging.getLogger("weather_station")
        logger.setLevel(log_level)

        if logger.handlers:
            logger.handlers.clear()

        log_format: str = self.settings.get("log_format",
                                            '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
                                            )
        formatter: logging.Formatter = logging.Formatter(log_format)

        if log_type in ["file", "both"]:
            log_dir: str = os.path.dirname(os.path.abspath(log_file))
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler: logging.handlers.RotatingFileHandler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=log_max_size,
                backupCount=log_backup_count
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        if log_type in ["syslog", "both"]:
            if platform.system() == "Windows":
                try:
                    syslog_handler: logging.Handler = NTEventLogHandler("Weather Station")
                    syslog_handler.setFormatter(formatter)
                    logger.addHandler(syslog_handler)
                except ImportError:
                    logger.warning("NTEventLogHandler not available, falling back to file logging")
                    if log_type == "syslog":
                        file_handler = logging.handlers.RotatingFileHandler(
                            log_file,
                            maxBytes=log_max_size,
                            backupCount=log_backup_count
                        )
                        file_handler.setFormatter(formatter)
                        logger.addHandler(file_handler)
            else:
                try:
                    if sys.platform == 'darwin':
                        syslog_handler = logging.handlers.SysLogHandler('/var/run/syslog')
                    else:
                        syslog_handler = logging.handlers.SysLogHandler('/dev/log')

                    syslog_handler.setFormatter(formatter)
                    logger.addHandler(syslog_handler)
                except (OSError, socket.error) as e:
                    logger.warning(f"Could not connect to syslog: {e}")
                    if log_type == "syslog":
                        file_handler = logging.handlers.RotatingFileHandler(
                            log_file,
                            maxBytes=log_max_size,
                            backupCount=log_backup_count
                        )
                        file_handler.setFormatter(formatter)
                        logger.addHandler(file_handler)

        console_handler: logging.StreamHandler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        self.logger = logger

    def get_logger(self) -> logging.Logger:
        """Return the configured logger"""
        if self.logger is None:
            self.setup_logger()
        assert self.logger is not None
        return self.logger


def get_logger(settings: Optional[Settings] = None) -> logging.Logger:
    """Get a configured logger based on settings"""
    logger_setup = LoggerSetup(settings)
    return logger_setup.get_logger()
