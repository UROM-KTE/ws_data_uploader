#!/usr/bin/env python3

from weather_station import WeatherCollector


def main():
    collector = WeatherCollector("settings.json")
    collector.run_scheduler()


if __name__ == "__main__":
    main()
