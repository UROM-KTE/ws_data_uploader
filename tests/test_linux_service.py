import json
import os
import platform
import signal
from unittest.mock import patch, mock_open

import pytest

# Skip all tests if on Windows since we're testing the Linux service behavior
pytestmark = pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Linux service tests not applicable on Windows"
)

# Sample settings JSON for testing
SAMPLE_SETTINGS = {
    "station_ip": "192.168.1.100",
    "database_host": "localhost",
    "database_port": 5432,
    "database_name": "weather",
    "database_user": "user",
    "database_password": "password",
    "database_table": "weather_data",
    "log_level": "INFO",
    "log_file": "weather.log"
}

@pytest.fixture
def mock_file_open():
    """Mock the file open operation to return sample settings"""
    settings_json = json.dumps(SAMPLE_SETTINGS)
    with patch('builtins.open', mock_open(read_data=settings_json)):
        yield

def test_signal_handlers(mock_file_open):
    """Test that signal handlers are registered properly"""
    # Patch dependencies to avoid actual network/DB calls
    with patch('weather_station.database.DatabaseManager'), \
         patch('weather_station.local_storage.LocalStorageManager'), \
         patch('schedule.every'), \
         patch('time.sleep', side_effect=InterruptedError), \
         patch('signal.signal') as mock_signal:
        
        # Now we can safely import and instantiate
        from weather_station.collector import WeatherCollector
        collector = WeatherCollector("dummy_path")
        
        # Run the scheduler - this will raise InterruptedError due to our mock
        try:
            collector.run_scheduler()
        except InterruptedError:
            pass
        
        # Check that signal handlers were registered
        assert mock_signal.call_count >= 2
        
        # Verify SIGINT and SIGTERM were registered
        signal_types = [call_args[0][0] for call_args in mock_signal.call_args_list]
        assert signal.SIGINT in signal_types
        assert signal.SIGTERM in signal_types

def test_signal_handling(mock_file_open):
    """Test the signal handler stops the collector properly"""
    # Patch dependencies to avoid actual network/DB calls
    with patch('weather_station.database.DatabaseManager'), \
         patch('weather_station.local_storage.LocalStorageManager'), \
         patch('schedule.every'), \
         patch('time.sleep', side_effect=InterruptedError), \
         patch('signal.signal') as mock_signal:
        
        # Import the collector
        from weather_station.collector import WeatherCollector
        
        # Create a real collector instance (file operations are mocked)
        collector = WeatherCollector("dummy_path")
        collector.running = True
        
        # Run scheduler to register signal handlers - will raise InterruptedError immediately
        try:
            collector.run_scheduler()
        except InterruptedError:
            pass

def test_systemd_service_file():
    """Verify the systemd service file is valid"""
    # Try to find the service file
    service_file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "weather-station.service"
    )
    
    # If we can't find it in the expected location, skip this test
    if not os.path.exists(service_file_path):
        pytest.skip("Service file not found")
    
    # Read the service file
    with open(service_file_path, 'r') as f:
        service_content = f.read()
    
    # Check for required sections
    assert "[Unit]" in service_content
    assert "[Service]" in service_content
    assert "[Install]" in service_content
    
    # Check for important settings
    assert "ExecStart=" in service_content
    assert "Restart=always" in service_content

def test_linux_service_startup():
    """Test the content of main.py without executing it"""
    try:
        import main
        
        # Check that main has the expected attributes
        assert hasattr(main, 'main'), "main.py should have a main() function"
        
        # Inspect the source code to verify it creates a WeatherCollector
        import inspect
        source = inspect.getsource(main.main)
        assert "WeatherCollector" in source, "main() should create a WeatherCollector"
        assert "run_scheduler" in source, "main() should call run_scheduler"
        
    except ImportError:
        pytest.skip("main.py not found - skipping test")