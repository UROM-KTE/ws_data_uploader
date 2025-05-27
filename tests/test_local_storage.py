import json
import os
import sqlite3
from unittest.mock import patch, MagicMock

import pytest

from weather_station.local_storage import LocalStorageManager


@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    with patch('weather_station.local_storage.get_logger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


def test_init_db_success(temp_db_path, mock_logger):
    """Test successful database initialization"""
    LocalStorageManager(db_path=temp_db_path, settings={})

    assert os.path.exists(temp_db_path)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weather_data'")
    table_exists = cursor.fetchone() is not None
    conn.close()

    assert table_exists
    mock_logger.info.assert_called_with("Local SQLite database initialized successfully")


def test_save_data_success(temp_db_path, mock_logger, sample_weather_data):
    """Test successful data save"""
    manager = LocalStorageManager(db_path=temp_db_path, settings={})

    result = manager.save_data(sample_weather_data)

    assert result is True

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM weather_data")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1
    mock_logger.debug.assert_any_call(f"Saving data to local storage: {sample_weather_data}")

    assert any("Data saved to local storage with ID:" in args[0] for args, kwargs in mock_logger.info.call_args_list)


def test_mark_as_synced_success(temp_db_path, mock_logger, sample_weather_data):
    """Test marking a record as synced"""
    manager = LocalStorageManager(db_path=temp_db_path, settings={})

    manager.save_data(sample_weather_data)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM weather_data LIMIT 1")
    data_id = cursor.fetchone()[0]
    conn.close()

    result = manager.mark_as_synced(data_id)

    assert result is True

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT synced FROM weather_data WHERE id = ?", (data_id,))
    synced = cursor.fetchone()[0]
    conn.close()

    assert synced == 1
    mock_logger.debug.assert_any_call(f"Record {data_id} marked as synced")


def test_mark_as_synced_error(temp_db_path, mock_logger):
    """Test error when marking a record as synced"""
    manager = LocalStorageManager(db_path=temp_db_path, settings={})

    with patch('sqlite3.connect', side_effect=Exception("Database error")):
        result = manager.mark_as_synced("test-id")

        assert result is False
        mock_logger.error.assert_called_with("Error marking record test-id as synced: Database error")


def test_get_pending_data(temp_db_path, mock_logger, sample_weather_data):
    """Test fetching pending data"""
    manager = LocalStorageManager(db_path=temp_db_path, settings={})

    for i in range(3):
        manager.save_data(sample_weather_data)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM weather_data LIMIT 1")
    data_id = cursor.fetchone()[0]
    cursor.execute("UPDATE weather_data SET synced = 1 WHERE id = ?", (data_id,))
    conn.commit()
    conn.close()

    pending_data = manager.get_pending_data()

    assert len(pending_data) == 2

    for record in pending_data:
        assert 'id' in record

    mock_logger.debug.assert_any_call("Fetching up to 100 pending records from local storage")
    mock_logger.info.assert_any_call("Retrieved 2 pending records from local storage")


def test_init_db_file_access_error(mock_logger):
    """Test handling of file access errors during init_db"""
    with patch('sqlite3.connect', side_effect=sqlite3.OperationalError("Permission denied")):
        with pytest.raises(Exception):
            LocalStorageManager(db_path="/invalid/path/db.sqlite")

        mock_logger.error.assert_called_with("Error initializing local database: Permission denied")

        traceback_calls = [call for call in mock_logger.debug.call_args_list
                           if isinstance(call[0][0], str) and "Traceback" in call[0][0]]
        assert len(traceback_calls) > 0, "Should have logged a traceback"


def test_save_data_with_complex_data(temp_db_path, mock_logger):
    """Test saving data with complex nested structures"""
    manager = LocalStorageManager(db_path=temp_db_path, settings={})

    complex_data = {
        "date": "2023-06-15",
        "time": "12:30:45",
        "nested": {
            "value1": 123,
            "value2": "test",
            "list": [1, 2, 3]
        },
        "end": 1
    }

    result = manager.save_data(complex_data)
    assert result is True

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM weather_data LIMIT 1")
    data_json = cursor.fetchone()[0]
    conn.close()

    saved_data = json.loads(data_json)
    assert saved_data == complex_data
    assert saved_data["nested"]["list"] == [1, 2, 3]


def test_get_pending_data_with_invalid_json(temp_db_path, mock_logger):
    """Test handling of invalid JSON in the database"""

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS weather_data (id TEXT PRIMARY KEY, data TEXT, synced INTEGER DEFAULT 0, timestamp TEXT)"
    )
    cursor.execute(
        "INSERT INTO weather_data (id, data, timestamp) VALUES (?, ?, datetime('now'))",
        ("test-id", "{invalid json")  # Intentionally invalid JSON
    )
    conn.commit()
    conn.close()

    manager = LocalStorageManager(db_path=temp_db_path, settings={})
    pending_data = manager.get_pending_data()

    assert pending_data == []
    mock_logger.error.assert_called_once()
    assert "Error fetching pending records" in mock_logger.error.call_args[0][0]


def test_mark_as_synced_nonexistent_id(temp_db_path, mock_logger):
    """Test marking a non-existent record as synced"""
    manager = LocalStorageManager(db_path=temp_db_path, settings={})

    result = manager.mark_as_synced("non-existent-id")

    assert result is True

    mock_logger.debug.assert_called_with("Record non-existent-id marked as synced")


def test_init_db_table_already_exists(temp_db_path, mock_logger):
    """Test init_db when the table already exists"""
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS weather_data (id TEXT PRIMARY KEY, data TEXT, synced INTEGER DEFAULT 0, timestamp TEXT)"
    )
    conn.commit()
    conn.close()

    LocalStorageManager(db_path=temp_db_path, settings={})

    mock_logger.info.assert_called_with("Local SQLite database initialized successfully")

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weather_data'")
    table_exists = cursor.fetchone() is not None
    conn.close()

    assert table_exists
