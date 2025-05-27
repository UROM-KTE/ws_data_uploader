from typing import TypedDict, Optional, Union


class WeatherData(TypedDict, total=False):
    id: str
    date: str
    time: str
    wind_speed: Optional[int]
    wind_direction: Optional[int]
    wind_min1_max: Optional[int]
    wind_min1_avg: Optional[int]
    wind_min1_dir: Optional[int]
    wind_forever_max: Optional[int]
    temperature1: Optional[float]
    temperature2: Optional[float]
    humidity: Optional[float]
    pressure: Optional[float]
    avg_pressure: Optional[float]
    rain: Optional[float]
    billenes: Optional[int]
    end: Optional[int]


class Settings(TypedDict, total=False):
    station_ip: str
    station_name: str
    station_location: str
    database_host: str
    database_port: Union[str, int]
    database_name: str
    database_user: str
    database_password: str
    database_table: str
    log_type: str
    log_level: str
    log_file: str
    log_max_size: int
    log_backup_count: int
    log_format: str
