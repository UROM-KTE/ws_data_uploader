# Weather Station Data Collector

A robust, cross-platform application for collecting, storing, and managing weather station data. This system connects to
weather station hardware created by [Időkép](https://www.idokep.hu), collects environmental data at regular intervals,
and stores it in a PostgreSQL database with
local backup capabilities.

## Features

- Automated data collection from compatible weather stations
- Configurable logging with support for file and syslog outputs
- Persistent storage in PostgreSQL database
- Local backup when a database connection is unavailable
- Automatic data synchronization when the connection is restored
- Cross-platform support (Windows, macOS, Linux)
- Run as a service/daemon on all supported platforms

## Installation

### Prerequisites

- Python 3.12
- PostgreSQL database (local or remote)
- Weather station hardware with HTTP API support

**Note:** This application has been primarily developed and tested on Linux environments. While designed to be
cross-platform, the developer has not extensively tested specific Windows and macOS functionality. User feedback for
these platforms is welcomed.

### For End Users

#### Option 1: Install from release packages

1. Get the latest version:

    - [Windows (zip)](https://github.com/UROM-KTE/ws_data_uploader/releases/download/latest/weather_station_windows.zip)
    - [Linux (tar.gz)](https://github.com/UROM-KTE/ws_data_uploader/releases/download/latest/weather_station_linux.tar.gz)
    - [macOS (tar.gz)](https://github.com/UROM-KTE/ws_data_uploader/releases/download/latest/weather_station_macos.tar.gz)

   Or visit the [releases page](https://github.com/UROM-KTE/ws_data_uploader/releases) for older versions.

2. Extract the package contents to your desired location.

3. Configure your `settings.json` file with your weather station and database details (see the Configuration section).

4. Run the application:

**Windows**:

```
weather_station_collector.exe
```

**macOS/Linux**:

```
./weather_station_collector
```

#### Option 2: Install from the Python package

   ```shell script
   pip install weather-station
   ```

Then run the application:

   ```shell script
   weather-station --config /path/to/settings.json
   ```

### Running as a Service

#### Windows

To install as a Windows service:

   ```shell script
   python service.py install
   ```

To start, stop, or remove the service:

   ```
   python service.py start
   python service.py stop
   python service.py remove
   ```

#### Linux/macOS

A systemd service file is provided. To install:

1. Edit the `weather-station.service` file to set the correct paths
2. Copy to systemd directory:

   ```shell script
   sudo cp weather-station.service /etc/systemd/system/
   ```

3. Enable and start the service:

   ```shell script
   sudo systemctl enable weather-station
   sudo systemctl start weather-station
   ```

## Configuration

Create a `settings.json` file with the following structure:

```json
{
  "station_ip": "192.168.1.100",
  "log_type": "file",
  "log_level": "INFO",
  "log_file": "/var/log/weather-station/weather.log",
  "log_max_size": 5242880,
  "log_backup_count": 3,
  "database_host": "localhost",
  "database_port": 5432,
  "database_name": "weather_db",
  "database_user": "weather_user",
  "database_password": "secure_password",
  "database_table": "weather_data",
  "local_storage_path": "local_data.sqlite"
}
```

### Configuration Options

| Option             | Description                                                    | Default                                                                              |
|--------------------|----------------------------------------------------------------|--------------------------------------------------------------------------------------|
| station_ip         | IP address of the weather station                              | -                                                                                    |
| log_type           | Logging output type: "file", "syslog", or "both"               | "file"                                                                               |
| log_level          | Logging level: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" | "INFO"                                                                               |
| log_file           | Path to log file                                               | "weather_station.log"                                                                |
| log_max_size       | Maximum size of log file in bytes before rotation              | 5242880 (5MB)                                                                        |
| log_backup_count   | Number of backup log files to keep                             | 3                                                                                    |
| log_format         | Custom log format                                              | `%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s` |
| database_host      | PostgreSQL database host                                       | -                                                                                    |
| database_port      | PostgreSQL database port                                       | 5432                                                                                 |
| database_name      | PostgreSQL database name                                       | -                                                                                    |
| database_user      | PostgreSQL database username                                   | -                                                                                    |
| database_password  | PostgreSQL database password                                   | -                                                                                    |
| database_table     | Table name for weather data                                    | -                                                                                    |
| local_storage_path | Path to local SQLite backup file                               | "local_cache.db"                                                                     |

## For Developers

### Project Structure

```
weather-station/
├── weather_station/
│   ├── __init__.py
│   ├── collector.py     # Main data collection logic
│   ├── database.py      # Database connection and queries
│   ├── local_storage.py # Local backup storage
│   ├── logger.py        # Logging configuration
│   └── types.py         # Type definitions
├── tests/
│   ├── test_collector.py
│   ├── test_database.py
│   ├── test_local_storage.py
│   └── test_logger.py
├── main.py              # CLI entry point
├── service.py           # Windows service implementation
├── setup.py             # Package configuration
├── requirements.txt     # Dependencies
└── weather-station.service  # Linux/macOS service file
```

### Setting Up Development Environment

1. Clone the repository:
   ```shell script
   git clone [https://github.com/UROM-KTE/ws_data_uploader](https://github.com/UROM-KTE/ws_data_uploader) cd ws_data_uploader
   ```

   ```
   shell script python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:

   a. For production dependencies only:
   ```shell script
   pip install -r requirements.txt
   ```

   b. For development (includes testing tools, linters, etc.):
   ```shell script
   pip install -r requirements-dev.txt
   ```

   c. Alternative method using setup.py with development extras:
   ```shell script
   pip install -e ".[dev]"
   ```

### Development Requirements

The development setup includes these additional tools:

- **pytest & pytest-cov**: For testing and code coverage
- **mypy**: Static type checking
- **flake8**: Code linting
- **build**: For building distribution packages
- **pyinstaller**: For creating standalone executables

### Building and Testing Locally

#### Creating a Local Build

To create a local build for testing:

1. Ensure you have all development dependencies installed:
   ```shell script
   pip install -e ".[dev]"
   ```

2. Run the build process to create distributable packages:
   ```shell script
   python -m build
   ```
   This will create both source distribution (.tar.gz) and wheel (.whl) files in the `dist/` directory.

3. For a standalone executable:
   ```shell script
   pyinstaller --onefile --name weather_station_collector main.py
   ```
   This creates a standalone executable in the `dist/` directory.

#### Testing the Local Build

1. **Testing the Python package**:
   ```shell
   # Install the wheel file locally
   pip install --force-reinstall dist/weather_station-x.y.z-py3-none-any.whl

   # Run the installed package
   weather-station --config test_settings.json
   ```

2. **Testing the executable**:
   ```shell
   # Run the executable with a test configuration
   ./dist/weather_station_collector --config test_settings.json
   ```

3. **Creating a test environment**:
   For full integration testing, you can set up a Docker container with PostgreSQL:
   ```shell
   # Start a PostgreSQL container
   docker run --name weather-db -e POSTGRES_PASSWORD=testpassword -e POSTGRES_USER=weather_user -e POSTGRES_DB=weather_db -p 5432:5432 -d postgres:14

   # Create a test_settings.json file
   cat > test_settings.json << EOL
   {
     "station_ip": "localhost",
     "log_type": "file",
     "log_level": "DEBUG",
     "log_file": "weather_test.log",
     "database_host": "localhost",
     "database_port": 5432,
     "database_name": "weather_db",
     "database_user": "weather_user",
     "database_password": "testpassword",
     "database_table": "weather_data",
     "local_storage_path": "test_local_data.sqlite"
   }
   EOL

   # Set up the database table
   psql -h localhost -U weather_user -d weather_db -c "
   CREATE TABLE weather_data (
     id SERIAL PRIMARY KEY,
     datetime TIMESTAMP,
     wind_speed FLOAT,
     wind_direction INT,
     wind_min1_max FLOAT,
     wind_min1_avg FLOAT,
     wind_min1_dir INT,
     wind_foreveremax FLOAT,
     temperature1 FLOAT,
     temperature2 FLOAT,
     humidity FLOAT,
     pressure FLOAT,
     avg_pressure FLOAT,
     rain FLOAT,
     billenes INT,
     end INT
   );"
   ```

4. **Mock weather station API**:
   For complete testing without actual hardware, create a simple mock server:
   ```shell
   # Install Flask if not already installed
   pip install flask

   # Create a mock_weather_station.py file
   cat > mock_weather_station.py << EOL
   from flask import Flask, jsonify
   import random

   app = Flask(__name__)

   @app.route('/wind.json')
   def wind_data():
       return jsonify({
           "speed": random.uniform(0, 30),
           "dir": random.randint(0, 359),
           "min1max": random.uniform(0, 35),
           "min1avgspeed": random.uniform(0, 25),
           "min1dir": random.randint(0, 359),
           "forevermax": random.uniform(30, 50)
       })

   @app.route('/sensors.json')
   def sensor_data():
       return jsonify({
           "hom": random.uniform(15, 35),
           "hom2": random.uniform(15, 35),
           "rh": random.uniform(30, 90),
           "p": random.uniform(990, 1030),
           "ap": random.uniform(990, 1030),
           "csap": random.uniform(0, 10),
           "billenes": random.randint(0, 10),
           "end": random.randint(0, 1)
       })

   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=80)
   EOL

   # Run the mock server (may require sudo for port 80)
   sudo python mock_weather_station.py

   # Alternatively, run on a higher port and update test_settings.json
   python mock_weather_station.py --port 8080
   # Then set "station_ip": "localhost:8080" in test_settings.json
   ```

#### Cross-Platform Building

For building on different platforms:

- **Windows**:
  ```shell
  pyinstaller --onefile --windowed --icon=resources/icon.ico --name weather_station_collector main.py
  ```

- **macOS**:
  ```shell
  pyinstaller --onefile --windowed --icon=resources/icon.icns --name weather_station_collector main.py
  ```

- **Linux**:
  ```shell
  pyinstaller --onefile --name weather_station_collector main.py
  ```

#### Verifying the Build

To ensure your build works correctly:

1. Test basic functionality:
   ```shell
   ./dist/weather_station_collector --once --config test_settings.json
   ```

2. Check logs for errors:
   ```shell
   cat weather_test.log
   ```

3. Verify data was saved to the database:
   ```shell
   psql -h localhost -U weather_user -d weather_db -c "SELECT * FROM weather_data ORDER BY datetime DESC LIMIT 5;"
   ```

4. Test local storage fallback by stopping the PostgreSQL container:
   ```shell
   docker stop weather-db
   ./dist/weather_station_collector --once --config test_settings.json
   ```

5. Verify data was saved to local storage:
   ```shell
   sqlite3 test_local_data.sqlite "SELECT * FROM weather_data WHERE synced=0;"
   ```

### Development Guidelines

1. **Type Annotations**: Use Python type hints throughout the codebase.
2. **Error Handling**: All external interactions should have proper error handling.
3. **Logging**: Use the logger module for all logging. Don't use print statements.
4. **Testing**: Maintain test coverage above 80%. Write tests for all new features.

### Creating a Release

The project uses GitHub Actions for CI/CD. When you push to the `master` branch, the workflow:

1. Runs all tests
2. Builds packages for Windows, macOS, and Linux
3. Creates a GitHub release with the packages

To create a new release, update the version in `setup.py` and push to master.

## Troubleshooting

### Common Issues

1. **Database Connection Failures**
    - Check your database credentials in settings.json
    - Ensure the PostgreSQL server is running
    - Verify network connectivity to the database host

2. **Weather Station Connection Issues**
    - Verify the station_ip is correct
    - Ensure the weather station is on the same network
    - Check if the weather station API is responding

3. **Log File Access Problems**
    - Verify the application has write access to the log directory
    - For syslog issues, check system log configuration

### Viewing Logs

Check the configured log file or system logs:

- **File logging**: See the path specified in `log_file` setting
- **Windows Event Log**: Check Windows Event Viewer under "Applications"
- **Linux syslog**: Check `/var/log/syslog` or use `journalctl`
- **macOS syslog**: Use `log show --predicate 'sender == "Weather Station"'`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgements

- The logging module is based on Python's built-in logging facilities
- Thanks to all contributors who have helped shape this project

---

*Időkép" and "idokep.hu" are registered trademarks and/or products of Időkép Kft. This project is not affiliated with,
endorsed by, or sponsored by Időkép Kft. All rights to the Időkép name, logo, services, and products belong to
Időkép Kft.*

*This application is designed to work with weather station hardware created by Időkép, but is an independent,
third-party tool. All trademarks, service marks, trade names, and product names referenced in this project
are the property of their respective owners.*

*This project is designed for educational and research purposes. Always verify weather data with official sources for
critical applications.*
