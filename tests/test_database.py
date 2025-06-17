from unittest.mock import patch, MagicMock

import pytest

from weather_station.database import DatabaseManager


@pytest.fixture
def mock_db_logger():
    """Mock logger specifically for the database module"""
    with patch('weather_station.database.get_logger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


def test_database_init(sample_settings, mock_db_logger):
    """Test database manager initialization"""
    db_manager = DatabaseManager(sample_settings)
    assert db_manager.settings == sample_settings
    mock_db_logger.debug.assert_called_with("Database manager initialized")


def test_connect_success(sample_settings, mock_db_logger):
    """Test a successful database connection"""
    with patch.object(DatabaseManager, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_manager = DatabaseManager(sample_settings)
        result = db_manager.connect()

        assert result is True
        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_db_logger.info.assert_any_call(
            f"Connecting to database at {sample_settings['database_host']}:{sample_settings['database_port']}")
        mock_db_logger.info.assert_any_call("Successfully connected to database")


def test_connect_failure(sample_settings, mock_db_logger):
    """Test database connection failure"""
    with patch.object(DatabaseManager, 'get_connection', side_effect=Exception("Connection error")) as mock_get_conn:
        db_manager = DatabaseManager(sample_settings)
        result = db_manager.connect()

        assert result is False
        mock_db_logger.error.assert_called_once_with("Database connection error: Connection error")


def test_is_connected_no_connection(sample_settings, mock_db_logger):
    """Test is_connected when no connection exists"""
    with patch.object(DatabaseManager, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_manager = DatabaseManager(sample_settings)
        result = db_manager.is_connected()

        assert result is True
        mock_cursor.execute.assert_called_once_with("SELECT 1")


def test_is_connected_with_connection(sample_settings, mock_db_logger):
    """Test is_connected with an existing connection (pool always used)"""
    with patch.object(DatabaseManager, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_manager = DatabaseManager(sample_settings)
        result = db_manager.is_connected()

        assert result is True
        mock_cursor.execute.assert_called_once_with("SELECT 1")


def test_is_connected_with_error(sample_settings, mock_db_logger):
    """Test is_connected when connection check fails"""
    with patch.object(DatabaseManager, 'get_connection', side_effect=Exception("Connection lost")) as mock_get_conn:
        db_manager = DatabaseManager(sample_settings)
        result = db_manager.is_connected()
        assert result is False
        mock_db_logger.warning.assert_called_once_with("Database connection check failed: Connection lost")


def test_save_data_not_connected(sample_settings, sample_weather_data, mock_db_logger):
    """Test save_data when not connected to the database"""
    with patch.object(DatabaseManager, 'is_connected', return_value=False):
        db_manager = DatabaseManager(sample_settings)
        result = db_manager.save_data(sample_weather_data)

        assert result is False
        mock_db_logger.warning.assert_called_once_with("Cannot save data: no database connection")


def test_save_data_success(sample_settings, sample_weather_data, mock_db_logger):
    """Test successful data saving"""
    with patch.object(DatabaseManager, 'is_connected', return_value=True), \
         patch.object(DatabaseManager, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_manager = DatabaseManager(sample_settings)
        result = db_manager.save_data(sample_weather_data)

        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_db_logger.debug.assert_any_call(
            f"Executing database insert for datetime: {sample_weather_data['date']} {sample_weather_data['time']}")
        mock_db_logger.debug.assert_any_call("Database insert successful")


def test_save_data_error(sample_settings, sample_weather_data, mock_db_logger):
    """Test data saving with an error"""
    with patch.object(DatabaseManager, 'is_connected', return_value=True), \
         patch.object(DatabaseManager, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("SQL Error")
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_manager = DatabaseManager(sample_settings)
        result = db_manager.save_data(sample_weather_data)

        assert result is False
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_not_called()
        mock_db_logger.error.assert_called_once_with("Error saving to database: SQL Error")


def test_save_data_connection_error(sample_settings, sample_weather_data, mock_db_logger):
    """Test data saving with a connection error and reconnect attempt"""
    with patch.object(DatabaseManager, 'is_connected', return_value=True), \
         patch.object(DatabaseManager, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("connection error")
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_manager = DatabaseManager(sample_settings)
        result = db_manager.save_data(sample_weather_data)

        assert result is False
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_not_called()
        mock_db_logger.error.assert_called_once_with("Error saving to database: connection error")


def test_save_data_no_connection_object(sample_settings, sample_weather_data, mock_db_logger):
    """Test save_data when is_connected is True but the connection object is None (should never happen with pool)"""
    # In the new implementation, this case is not possible, so we just check the warning
    with patch.object(DatabaseManager, 'is_connected', return_value=False):
        db_manager = DatabaseManager(sample_settings)
        result = db_manager.save_data(sample_weather_data)
        assert result is False
        mock_db_logger.warning.assert_called_once_with("Cannot save data: no database connection")


def test_save_data_connection_timeout(sample_settings, sample_weather_data, mock_db_logger):
    """Test data saving with a connection timeout error"""
    with patch.object(DatabaseManager, 'is_connected', return_value=True), \
         patch.object(DatabaseManager, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("connection timeout error")
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        db_manager = DatabaseManager(sample_settings)
        result = db_manager.save_data(sample_weather_data)

        assert result is False
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_not_called()
        mock_db_logger.error.assert_called_once_with("Error saving to database: connection timeout error")


def test_connect_with_settings_validation(sample_settings, mock_db_logger):
    """Test connection with invalid settings"""
    invalid_settings = sample_settings.copy()
    del invalid_settings["database_host"]

    db_manager = DatabaseManager(invalid_settings)
    result = db_manager.connect()

    assert result is False
    mock_db_logger.error.assert_called()
    assert "database_host" in mock_db_logger.error.call_args[0][0]
