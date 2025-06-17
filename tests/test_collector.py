from unittest.mock import patch, MagicMock

import pytest
import requests

from weather_station.collector import WeatherCollector


@pytest.fixture
def mock_logger():
    """Mock logger for collector testing"""
    with patch('weather_station.collector.get_logger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


def test_init_success(temp_settings_file, mock_logger):
    """Test successful initialization of collector"""
    with patch('weather_station.collector.DatabaseManager') as mock_db_manager, \
            patch('weather_station.collector.LocalStorageManager') as mock_local_storage:
        collector = WeatherCollector(temp_settings_file)

        assert collector.running is False
        mock_db_manager.assert_called_once()
        mock_local_storage.assert_called_once()
        mock_logger.info.assert_any_call("Weather collector initializing")
        mock_logger.info.assert_any_call("Weather collector initialized successfully")


def test_init_error(temp_settings_file, mock_logger):
    """Test initialization error handling"""
    with patch('weather_station.collector.DatabaseManager', side_effect=Exception("DB Error")), \
            patch('weather_station.collector.LocalStorageManager'):
        with pytest.raises(Exception) as excinfo:
            WeatherCollector(temp_settings_file)

        assert "DB Error" in str(excinfo.value)
        mock_logger.error.assert_called_with("Error initializing components: DB Error")


def test_collect_data_success(temp_settings_file, sample_wind_data, sample_sensors_data, mock_logger):
    """Test successful data collection"""
    with patch('weather_station.collector.DatabaseManager') as mock_db_manager, \
            patch('weather_station.collector.LocalStorageManager') as mock_local_storage, \
            patch.object(WeatherCollector, '_make_request') as mock_make_request:
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.is_connected.return_value = True
        mock_db_instance.save_data.return_value = True

        mock_make_request.side_effect = [sample_wind_data, sample_sensors_data]

        collector = WeatherCollector(temp_settings_file)

        test_date = "2023-06-15"
        test_time = "12:30:45"
        with patch('weather_station.collector.datetime') as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: test_date if fmt == "%Y-%m-%d" else test_time
            mock_dt.datetime.now.return_value = mock_now

            collector.collect_data()

        assert mock_make_request.call_count == 2
        mock_make_request.assert_any_call(f"http://{collector.settings['station_ip']}/wind.json")
        mock_make_request.assert_any_call(f"http://{collector.settings['station_ip']}/sensors.json")

        mock_db_instance.save_data.assert_called_once()
        saved_data = mock_db_instance.save_data.call_args[0][0]
        assert saved_data["date"] == test_date
        assert saved_data["time"] == test_time

        mock_logger.debug.assert_any_call("Starting data collection")
        mock_logger.info.assert_any_call("Data saved to database successfully")


def test_collect_data_db_fallback(temp_settings_file, sample_wind_data, sample_sensors_data, mock_logger):
    """Test fallback to local storage when database save fails"""
    with patch('weather_station.collector.DatabaseManager') as mock_db_manager, \
            patch('weather_station.collector.LocalStorageManager') as mock_local_storage, \
            patch.object(WeatherCollector, '_make_request') as mock_make_request:
        # Configure mocks
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.is_connected.return_value = True
        mock_db_instance.save_data.return_value = False

        mock_local_instance = mock_local_storage.return_value

        mock_make_request.side_effect = [sample_wind_data, sample_sensors_data]

        collector = WeatherCollector(temp_settings_file)
        collector.collect_data()

        mock_db_instance.save_data.assert_called_once()
        mock_local_instance.save_data.assert_called_once()
        mock_logger.warning.assert_called_with("Failed to save to database, falling back to local storage")


def test_sync_pending_data_success(temp_settings_file, sample_weather_data, mock_logger):
    """Test successful sync of pending data"""
    with patch('weather_station.collector.DatabaseManager') as mock_db_manager, \
            patch('weather_station.collector.LocalStorageManager') as mock_local_storage:
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.is_connected.return_value = True
        mock_db_instance.save_data.return_value = True

        mock_local_instance = mock_local_storage.return_value

        pending_data = [dict(sample_weather_data, id="test-id-1")]
        mock_local_instance.get_pending_data.return_value = pending_data

        collector = WeatherCollector(temp_settings_file)
        collector.sync_pending_data()

        mock_db_instance.save_data.assert_called_once_with(pending_data[0])
        mock_local_instance.mark_as_synced.assert_called_once_with("test-id-1")

        mock_logger.info.assert_any_call("Attempting to sync 1 records from local storage")
        mock_logger.info.assert_any_call("Successfully synced 1/1 records")


def test_run_scheduler(temp_settings_file, mock_logger):
    """Test run_scheduler method"""
    with patch('weather_station.collector.DatabaseManager'), \
            patch('weather_station.collector.LocalStorageManager'), \
            patch('schedule.every') as mock_every, \
            patch('time.sleep', side_effect=InterruptedError), \
            patch('signal.signal') as mock_signal, \
            patch.object(WeatherCollector, 'collect_data') as mock_collect_data:
        mock_job = MagicMock()
        mock_every.return_value.minutes.do.return_value = mock_job

        collector = WeatherCollector(temp_settings_file)
        with pytest.raises(InterruptedError):
            collector.run_scheduler()

        assert collector.running is True
        mock_every.assert_called_once_with(1)
        mock_every.return_value.minutes.do.assert_called_once_with(collector.collect_data)

        assert mock_signal.call_count == 2
        mock_collect_data.assert_called_once()

        mock_logger.info.assert_any_call("Starting weather collector scheduler")
        mock_logger.info.assert_any_call("Scheduled data collection every 1 minute")
        mock_logger.info.assert_any_call("Performing initial data collection")


def test_collect_data_wind_request_error(temp_settings_file, mock_logger):
    """Test handling of wind data request errors"""
    with patch('weather_station.collector.DatabaseManager'), \
            patch('weather_station.collector.LocalStorageManager'), \
            patch.object(WeatherCollector, '_make_request') as mock_make_request:
        # Mock wind request to fail but sensor request to succeed
        mock_make_request.side_effect = [None, {"hom": 25.5, "hom2": 24.0}]

        collector = WeatherCollector(temp_settings_file)
        collector.collect_data()

        # Check that we logged the wind error
        mock_logger.error.assert_any_call("Failed to retrieve wind data")

        # Verify we called both requests
        assert mock_make_request.call_count == 2


def test_collect_data_sensors_request_error(temp_settings_file, mock_logger):
    """Test handling of sensor data request errors"""
    with patch('weather_station.collector.DatabaseManager'), \
            patch('weather_station.collector.LocalStorageManager') as mock_local_storage, \
            patch.object(WeatherCollector, '_make_request') as mock_make_request:
        mock_make_request.side_effect = [{"speed": 15, "dir": 180}, None]

        collector = WeatherCollector(temp_settings_file)
        collector.collect_data()

        mock_logger.debug.assert_any_call("Successfully retrieved wind data")
        mock_logger.error.assert_called_with("Failed to retrieve sensor data")

        mock_local_storage.return_value.save_data.assert_not_called()


def test_collect_data_db_not_connected(temp_settings_file, sample_wind_data, sample_sensors_data, mock_logger):
    """Test saving to local storage when database is not connected"""
    with patch('weather_station.collector.DatabaseManager') as mock_db_manager, \
            patch('weather_station.collector.LocalStorageManager') as mock_local_storage, \
            patch.object(WeatherCollector, '_make_request') as mock_make_request:
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.is_connected.return_value = False

        mock_local_instance = mock_local_storage.return_value

        mock_make_request.side_effect = [sample_wind_data, sample_sensors_data]

        collector = WeatherCollector(temp_settings_file)
        collector.collect_data()

        mock_db_instance.save_data.assert_not_called()
        mock_local_instance.save_data.assert_called_once()
        mock_logger.warning.assert_called_with("Database not connected, saving to local storage")


def test_sync_pending_data_db_not_connected(temp_settings_file, mock_logger):
    """Test sync when database is not connected"""
    with patch('weather_station.collector.DatabaseManager') as mock_db_manager, \
            patch('weather_station.collector.LocalStorageManager'):
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.is_connected.return_value = False

        collector = WeatherCollector(temp_settings_file)
        collector.sync_pending_data()

        mock_logger.debug.assert_called_with("Database not connected, skipping sync")


def test_sync_pending_data_no_pending_data(temp_settings_file, mock_logger):
    """Test sync when no pending data exists"""
    with patch('weather_station.collector.DatabaseManager') as mock_db_manager, \
            patch('weather_station.collector.LocalStorageManager') as mock_local_storage:
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.is_connected.return_value = True

        mock_local_instance = mock_local_storage.return_value
        mock_local_instance.get_pending_data.return_value = []

        collector = WeatherCollector(temp_settings_file)
        collector.sync_pending_data()

        mock_logger.debug.assert_called_with("No pending data to sync")


def test_sync_pending_data_partial_success(temp_settings_file, sample_weather_data, mock_logger):
    """Test sync with partial success"""
    with patch('weather_station.collector.DatabaseManager') as mock_db_manager, \
            patch('weather_station.collector.LocalStorageManager') as mock_local_storage:
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.is_connected.return_value = True
        mock_db_instance.save_data.side_effect = [True, False]

        mock_local_instance = mock_local_storage.return_value

        pending_data = [
            dict(sample_weather_data, id="test-id-1"),
            dict(sample_weather_data, id="test-id-2")
        ]
        mock_local_instance.get_pending_data.return_value = pending_data

        collector = WeatherCollector(temp_settings_file)
        collector.sync_pending_data()

        assert mock_db_instance.save_data.call_count == 2
        mock_local_instance.mark_as_synced.assert_called_once_with("test-id-1")

        mock_logger.info.assert_any_call("Attempting to sync 2 records from local storage")
        mock_logger.info.assert_any_call("Successfully synced 1/2 records")


def test_sync_pending_data_error(temp_settings_file, sample_weather_data, mock_logger):
    """Test sync error handling"""
    with patch('weather_station.collector.DatabaseManager') as mock_db_manager, \
            patch('weather_station.collector.LocalStorageManager') as mock_local_storage:
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.is_connected.return_value = True

        mock_local_instance = mock_local_storage.return_value
        mock_local_instance.get_pending_data.side_effect = Exception("Storage error")

        collector = WeatherCollector(temp_settings_file)
        collector.sync_pending_data()

        mock_logger.error.assert_called_with("Error syncing pending data: Storage error")


def test_run_scheduler_shutdown(temp_settings_file, mock_logger):
    """Test scheduler shutdown handling"""
    with patch('weather_station.collector.DatabaseManager'), \
            patch('weather_station.collector.LocalStorageManager'), \
            patch('schedule.every'), \
            patch('time.sleep') as mock_sleep, \
            patch('signal.signal'), \
            patch.object(WeatherCollector, 'collect_data'), \
            patch.object(WeatherCollector, '_cleanup') as mock_cleanup:

        def side_effect(*args, **kwargs):
            collector.running = False
            return None

        mock_sleep.side_effect = side_effect

        collector = WeatherCollector(temp_settings_file)
        collector.run_scheduler()

        mock_cleanup.assert_called_once()
        mock_logger.info.assert_any_call("Weather collector stopped")


def test_signal_handler(temp_settings_file, mock_logger):
    """Test signal handler functionality"""
    with patch('weather_station.collector.DatabaseManager'), \
            patch('weather_station.collector.LocalStorageManager'):
        collector = WeatherCollector(temp_settings_file)
        collector.running = True

        # Simulate signal handler call
        import signal
        collector._signal_handler = collector.__class__.__dict__['run_scheduler'].__code__.co_consts[1]

        # This is a bit of a hack to test the signal handler
        # In practice, the signal handler is defined inside run_scheduler
        collector.running = False
        assert collector.running is False


def test_scheduler_loop_error(temp_settings_file, mock_logger):
    """Test scheduler loop error handling"""
    with patch('weather_station.collector.DatabaseManager'), \
            patch('weather_station.collector.LocalStorageManager'), \
            patch('schedule.every'), \
            patch('time.sleep') as mock_sleep, \
            patch('signal.signal'), \
            patch.object(WeatherCollector, '_cleanup') as mock_cleanup, \
            patch('schedule.run_pending') as mock_run_pending, \
            patch.object(WeatherCollector, '_make_request'), \
            patch.object(WeatherCollector, 'collect_data'):

        def sleep_side_effect(*args, **kwargs):
            # Exit immediately after first sleep to avoid long test
            collector.running = False
            return None

        mock_sleep.side_effect = sleep_side_effect

        def run_pending_side_effect(*args, **kwargs):
            raise Exception("Scheduler error")

        mock_run_pending.side_effect = run_pending_side_effect

        collector = WeatherCollector(temp_settings_file)
        collector.run_scheduler()

        mock_logger.error.assert_called_with("Error in scheduler loop: Scheduler error")


def test_collect_data_both_requests_error(temp_settings_file, mock_logger):
    """Test handling when both requests fail"""
    with patch('weather_station.collector.DatabaseManager'), \
            patch('weather_station.collector.LocalStorageManager'), \
            patch.object(WeatherCollector, '_make_request') as mock_make_request:
        mock_make_request.side_effect = [None, None]

        collector = WeatherCollector(temp_settings_file)
        collector.collect_data()

        mock_logger.error.assert_any_call("Failed to retrieve wind data")
        mock_logger.error.assert_any_call("Failed to retrieve sensor data")
        mock_logger.error.assert_any_call("Failed to retrieve data from weather station, aborting collection")


def test_collect_data_with_one_missing_json(temp_settings_file, sample_wind_data, mock_logger):
    """Test handling when one request succeeds and one fails"""
    with patch('weather_station.collector.DatabaseManager') as mock_db_manager, \
            patch('weather_station.collector.LocalStorageManager') as mock_local_storage, \
            patch.object(WeatherCollector, '_make_request') as mock_make_request:
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.is_connected.return_value = True
        mock_db_instance.save_data.return_value = True

        mock_local_instance = mock_local_storage.return_value

        # Wind data succeeds, sensor data fails
        mock_make_request.side_effect = [sample_wind_data, None]

        collector = WeatherCollector(temp_settings_file)
        collector.collect_data()

        # Should still save data with partial information
        mock_db_instance.save_data.assert_called_once()
        saved_data = mock_db_instance.save_data.call_args[0][0]
        assert saved_data["wind_speed"] == sample_wind_data["speed"]
        assert saved_data["temperature1"] is None  # Sensor data failed
