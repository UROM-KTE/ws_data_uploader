import logging
import os
import platform
import socket
import tempfile
from logging.handlers import RotatingFileHandler
from unittest.mock import patch, MagicMock

import pytest

from weather_station.logger import LoggerSetup, get_logger


class TestLoggerSetup:
    def test_default_settings(self):
        """Test logger creation with default settings"""
        logger_setup = LoggerSetup()
        logger = logger_setup.get_logger()

        assert logger.name == "weather_station"
        assert logger.level == logging.INFO

        handler_types = [type(h) for h in logger.handlers]
        assert logging.StreamHandler in handler_types
        assert RotatingFileHandler in handler_types

        assert len(logger.handlers) == 2

    def test_custom_log_level(self):
        """Test setting custom log level"""
        settings = {"log_level": "DEBUG"}
        logger_setup = LoggerSetup(settings)
        logger = logger_setup.get_logger()

        assert logger.level == logging.DEBUG

    def test_invalid_log_level(self):
        """Test with invalid log level falls back to INFO"""
        settings = {"log_level": "INVALID_LEVEL"}
        logger_setup = LoggerSetup(settings)
        logger = logger_setup.get_logger()

        assert logger.level == logging.INFO

    def test_custom_log_format(self):
        """Test custom log format"""
        custom_format = '%(levelname)s - %(message)s'
        settings = {"log_format": custom_format}

        logger_setup = LoggerSetup(settings)
        logger = logger_setup.get_logger()

        for handler in logger.handlers:
            assert handler.formatter._fmt == custom_format

    def test_file_logging(self):
        """Test file logging configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_log.log")
            settings = {
                "log_type": "file",
                "log_file": log_file,
                "log_max_size": 1024,
                "log_backup_count": 2
            }

            logger_setup = LoggerSetup(settings)
            logger = logger_setup.get_logger()

            file_handler = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler))

            assert file_handler.baseFilename == log_file
            assert file_handler.maxBytes == 1024
            assert file_handler.backupCount == 2

            assert os.path.exists(log_file)

    def test_syslog_logging_linux(self):
        """Test syslog logging on Linux"""
        if platform.system() != "Linux":
            pytest.skip("Syslog test only applicable on Linux")

        settings = {"log_type": "syslog"}

        with patch('logging.handlers.SysLogHandler', autospec=True) as mock_syslog:
            LoggerSetup(settings)

            mock_syslog.assert_called_once_with('/dev/log')

    def test_syslog_logging_mac(self):
        """Test syslog logging on macOS"""
        if platform.system() != "Darwin":
            pytest.skip("macOS syslog test only applicable on macOS")

        settings = {"log_type": "syslog"}

        with patch('logging.handlers.SysLogHandler', autospec=True) as mock_syslog:
            LoggerSetup(settings)

            mock_syslog.assert_called_once_with('/var/run/syslog')

    def test_syslog_logging_windows(self):
        """Test Windows event log"""
        if platform.system() != "Windows":
            pytest.skip("Windows event log test only applicable on Windows")

        settings = {"log_type": "syslog"}

        with patch('logging.handlers.NTEventLogHandler', autospec=True) as mock_nt_log:
            logger_setup = LoggerSetup(settings)
            logger_setup.get_logger()

            mock_nt_log.assert_called_once_with("Weather Station")

    def test_syslog_fallback_on_error(self):
        """Test fallback to file logging when syslog fails"""
        settings = {"log_type": "syslog", "log_file": "fallback.log"}

        with patch('logging.handlers.SysLogHandler', side_effect=socket.error("Mocked error")), \
                patch('logging.handlers.RotatingFileHandler', autospec=True) as mock_file_handler:
            LoggerSetup(settings)

            mock_file_handler.assert_called_once()
            assert "fallback.log" in mock_file_handler.call_args[0][0]

    def test_windows_syslog_import_error(self):
        """Test Windows event log fallback on ImportError"""
        if platform.system() != "Windows":
            with patch('platform.system', return_value="Windows"):
                settings = {"log_type": "syslog", "log_file": "fallback.log"}

                with patch('weather_station.logger.NTEventLogHandler', side_effect=ImportError("Mocked error")), \
                        patch('logging.handlers.RotatingFileHandler', autospec=True) as mock_file_handler:
                    logger_setup = LoggerSetup(settings)
                    logger = logger_setup.get_logger()

                    mock_file_handler.assert_called_once()
        else:
            settings = {"log_type": "syslog", "log_file": "fallback.log"}

            with patch('weather_station.logger.NTEventLogHandler', side_effect=ImportError("Mocked error")), \
                    patch('logging.handlers.RotatingFileHandler', autospec=True) as mock_file_handler:
                logger_setup = LoggerSetup(settings)
                logger = logger_setup.get_logger()

                mock_file_handler.assert_called_once()

    def test_both_logging_types(self):
        """Test configuration with both file and syslog"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "both.log")
            settings = {"log_type": "both", "log_file": log_file}

            with patch('logging.handlers.SysLogHandler') as mock_syslog:
                mock_handler = MagicMock()
                mock_syslog.return_value = mock_handler

                logger_setup = LoggerSetup(settings)
                logger = logger_setup.get_logger()

                handler_types = [type(h) for h in logger.handlers]

                assert RotatingFileHandler in handler_types
                assert logging.StreamHandler in handler_types

                assert mock_handler in logger.handlers

                assert len(logger.handlers) == 3

    def test_log_directory_creation(self):
        """Test that log directories are created if they don't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = os.path.join(temp_dir, "nested", "logs")
            log_file = os.path.join(nested_dir, "test.log")

            settings = {"log_file": log_file}

            assert not os.path.exists(nested_dir)

            LoggerSetup(settings)

            assert os.path.exists(nested_dir)
            assert os.path.exists(log_file)

    def test_logger_reuse(self):
        """Test that logger handlers aren't duplicated on reuse"""
        logger_setup = LoggerSetup()
        logger1 = logger_setup.get_logger()

        handler_count = len(logger1.handlers)

        logger2 = logger_setup.get_logger()

        assert logger1 is logger2

        assert len(logger2.handlers) == handler_count

    def test_logger_reconfiguration(self):
        """Test that logger can be reconfigured"""
        logger_setup = LoggerSetup()
        logger1 = logger_setup.get_logger()

        new_settings = {"log_level": "ERROR"}
        logger_setup = LoggerSetup(new_settings)
        logger2 = logger_setup.get_logger()

        assert logger1 is logger2

        assert logger2.level == logging.ERROR

    def test_get_logger_function(self):
        """Test the get_logger convenience function"""
        settings = {"log_level": "WARNING"}

        logger = get_logger(settings)

        assert logger.name == "weather_station"
        assert logger.level == logging.WARNING

    def test_makedirs_error(self):
        """Test handling of os.makedirs errors"""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_dir = os.path.join(temp_dir, "nope", "logs")
            log_file = os.path.join(non_existent_dir, "test.log")

        settings = {"log_file": log_file}
        with patch('logging.handlers.RotatingFileHandler', autospec=True) as mock_handler:
            mock_instance = MagicMock()
            mock_handler.return_value = mock_instance

            logger_setup = LoggerSetup(settings)
            logger = logger_setup.get_logger()

            console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
            assert len(console_handlers) > 0

    def test_actual_logging(self):
        """Test that the logger actually logs messages to a file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_actual.log")
            settings = {"log_file": log_file, "log_level": "DEBUG"}

            logger = get_logger(settings)

            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            with open(log_file, 'r') as f:
                log_content = f.read()

            assert "Debug message" in log_content
            assert "Info message" in log_content
            assert "Warning message" in log_content
            assert "Error message" in log_content
