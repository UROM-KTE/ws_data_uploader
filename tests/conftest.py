import json
import os
import tempfile
from typing import Any, Generator, Dict
from unittest.mock import MagicMock, patch

import pytest

Settings = Dict[str, Any]
WeatherData = Dict[str, Any]


@pytest.fixture
def sample_settings() -> Settings:
    """Return sample settings for testing"""
    return {
        "station_ip": "192.168.1.100",
        "station_name": "Test Station",
        "station_location": "Test Location",
        "database_host": "localhost",
        "database_port": 5432,
        "database_name": "weather_db",
        "database_user": "user",
        "database_password": "password",
        "database_table": "weather_data",
        "log_type": "console",
        "log_level": "DEBUG",
        "log_file": "weather.log",
        "log_max_size": 10485760,
        "log_backup_count": 5,
        "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }


@pytest.fixture
def temp_settings_file(sample_settings: Dict[str, Any]) -> Generator[str, None, None]:
    """Create a temporary settings file for testing"""
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as f:
        json.dump(sample_settings, f)
    yield path
    os.unlink(path)


@pytest.fixture
def sample_wind_data() -> Dict[str, Any]:
    """Return sample wind data for testing"""
    return {
        "speed": 15,
        "dir": 180,
        "min1max": 18,
        "min1avgspeed": 14,
        "min1dir": 175,
        "forevermax": 35
    }


@pytest.fixture
def sample_sensors_data() -> Dict[str, Any]:
    """Return sample sensors data for testing"""
    return {
        "hom": 22.5,
        "hom2": 23.1,
        "rh": 65.0,
        "p": 1013.2,
        "ap": 1012.8,
        "csap": 0.0,
        "billenes": 0,
        "end": 1
    }


@pytest.fixture
def sample_weather_data() -> Dict[str, Any]:
    """Return sample weather data for testing"""
    return {
        "date": "2023-06-15",
        "time": "12:30:45",
        "wind_speed": 15,
        "wind_direction": 180,
        "wind_min1_max": 18,
        "wind_min1_avg": 14,
        "wind_min1_dir": 175,
        "wind_forever_max": 35,
        "temperature1": 22,
        "temperature2": 23,
        "humidity": 65.4,
        "pressure": 1013.2,
        "avg_pressure": 1012.8,
        "rain": 0.0,
        "billenes": 0,
        "end": 1
    }


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary file path for the SQLite database"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def fast_requests():
    """Patch requests to return predefined responses without any network delay"""
    wind_data = {
        "speed": 10,
        "dir": 180,
        "min1max": 12,
        "min1avgspeed": 9,
        "min1dir": 175,
        "forevermax": 25
    }

    sensors_data = {
        "hom": 22.5,
        "hom2": 21.8,
        "rh": 65,
        "p": 1013.2,
        "ap": 1013.5,
        "csap": 0.5,
        "billenes": 800,
        "end": 0
    }

    def mock_get(url, **kwargs):
        """Fast mock replacement for requests.get that returns canned responses"""
        response = MagicMock()
        response.raise_for_status = MagicMock()

        if 'wind.json' in url:
            response.json.return_value = wind_data
        elif 'sensors.json' in url:
            response.json.return_value = sensors_data
        else:
            response.json.return_value = {}

        return response

    with patch('requests.get', side_effect=mock_get):
        yield
