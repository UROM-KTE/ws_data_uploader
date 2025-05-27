import json
import sqlite3
from unittest.mock import patch, MagicMock

from weather_station.collector import WeatherCollector
from weather_station.local_storage import LocalStorageManager


def test_collect_and_store_data_flow(temp_settings_file, sample_wind_data, sample_sensors_data, temp_db_path):
    """Integration test for the data collection and storage flow"""
    with open(temp_settings_file, 'r') as f:
        settings = json.load(f)

    with patch('requests.get') as mock_get, \
            patch('psycopg2.connect', side_effect=Exception("DB connection error")):
        wind_response = MagicMock()
        wind_response.json.return_value = sample_wind_data

        sensors_response = MagicMock()
        sensors_response.json.return_value = sample_sensors_data

        mock_get.side_effect = [wind_response, sensors_response]

        local_storage = LocalStorageManager(db_path=temp_db_path, settings=settings)

        with patch('weather_station.collector.LocalStorageManager', return_value=local_storage):
            collector = WeatherCollector(temp_settings_file)

            collector.collect_data()

            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM weather_data WHERE synced = 0")
            records = cursor.fetchall()
            conn.close()

            assert len(records) == 1
            saved_data = json.loads(records[0][0])

            assert saved_data["wind_speed"] == sample_wind_data["speed"]
            assert saved_data["wind_direction"] == sample_wind_data["dir"]
            assert saved_data["temperature1"] == sample_sensors_data["hom"]
            assert saved_data["temperature2"] == sample_sensors_data["hom2"]


def test_sync_from_local_to_db(temp_settings_file, sample_weather_data, temp_db_path):
    """Integration test for syncing data from local storage to the database"""
    with open(temp_settings_file, 'r') as f:
        settings = json.load(f)

    local_storage = LocalStorageManager(db_path=temp_db_path, settings=settings)

    test_data_1 = dict(sample_weather_data)
    test_data_2 = dict(sample_weather_data, temperature1=25.0)
    local_storage.save_data(test_data_1)
    local_storage.save_data(test_data_2)

    mock_db_manager = MagicMock()
    mock_db_manager.is_connected.return_value = True

    mock_db_manager.save_data.side_effect = [True, False]

    with patch('weather_station.collector.DatabaseManager', return_value=mock_db_manager), \
            patch('weather_station.collector.LocalStorageManager', return_value=local_storage):
        collector = WeatherCollector(temp_settings_file)

        collector.sync_pending_data()

        assert mock_db_manager.save_data.call_count == 2

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM weather_data WHERE synced = 1")
        synced_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM weather_data WHERE synced = 0")
        unsynced_count = cursor.fetchone()[0]
        conn.close()

        assert synced_count == 1
        assert unsynced_count == 1
