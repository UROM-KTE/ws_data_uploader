# Weather Station Data Collector

A robust, cross-platform application for collecting, storing, and managing weather station data. This system connects to
weather station hardware created by [Időkép](https://www.idokep.hu), collects environmental data at regular intervals,
and stores it in a PostgreSQL database with
local backup capabilities.

## Key Features

- Automated data collection from compatible weather stations
- Optimized resource management with connection pooling
- Cross-platform support (Windows, macOS, Linux)
- Persistent storage in PostgreSQL with automatic failover
- Local SQLite backup with auto-sync
- Comprehensive logging system
- Service/daemon support on all platforms

## Requirements

- Python 3.12+
- PostgreSQL database (local or remote)
- Weather station hardware with HTTP API support

## Quick Start

1. Install the package:
```shell
pip install weather-station
```

2. Create a `settings.json` file:
```json
{
  "station_ip": "192.168.1.100",
  "log_type": "file",
  "log_level": "INFO",
  "log_file": "weather-station.log",
  "database_host": "localhost",
  "database_port": 5432,
  "database_name": "weather_db",
  "database_user": "weather_user",
  "database_password": "secure_password",
  "database_table": "weather_data",
  "local_storage_path": "local_cache.db"
}
```

3. Run the application:
```shell
weather-station --config settings.json
```

## Running as a Service

### Windows
```shell
python service.py install
python service.py start
```

### Linux/macOS
```shell
sudo cp weather-station.service /etc/systemd/system/
sudo systemctl enable weather-station
sudo systemctl start weather-station
```

## Development Setup

1. Clone and setup environment:
```shell
git clone https://github.com/UROM-KTE/ws_data_uploader
cd ws_data_uploader
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
```

2. Install dependencies:
```shell
pip install -r requirements-dev.txt
```

3. Run tests:
```shell
pytest
```

## Project Structure

```
weather-station/
├── weather_station/      # Core application code
├── tests/               # Test suite
├── main.py             # CLI entry point
├── service.py          # Service implementation
└── settings.json       # Configuration file
```

## Resource Management

The application implements efficient resource handling:
- Database connection pooling
- Proper HTTP session management
- Optimized SQLite connections
- Memory-efficient data processing

## Troubleshooting

Common issues and solutions:

1. **Database Connection Issues**
   - Verify database credentials and connectivity
   - Check PostgreSQL server status
   - Review logs for specific error messages

2. **Weather Station Connection**
   - Confirm station IP address
   - Verify network connectivity
   - Check station API availability

3. **Service/Daemon Issues**
   - Verify service configuration
   - Check system logs
   - Ensure proper permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a Pull Request

## License

MIT License - See `LICENSE` for details.

---

*This is an independent tool designed to work with Időkép weather station hardware. All trademarks and product names are property of their respective owners. For critical applications, always verify weather data with official sources.*
