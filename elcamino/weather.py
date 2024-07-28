# --------------------------------------------------------------------
# weather.py
#
# Author: Lain Musgrove (lain.proliant@gmail.com)
# Date: Thursday July 25, 2024
# --------------------------------------------------------------------
from dataclasses import dataclass, field
from datetime import datetime

import openmeteo_requests
import pandas as pd
import requests_cache
from dataclass_wizard import JSONWizard
from retry_requests import retry

from elcamino.config import WeatherConfig

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


# --------------------------------------------------------------------
@dataclass
class Weather(JSONWizard):
    dt: datetime
    code: int
    daytime: bool
    temperature: int
    high_temperature: int
    low_temperature: int
    precipitation: int


# --------------------------------------------------------------------
@dataclass
class WeatherReport(JSONWizard):
    current: Weather
    forecast: list[Weather]


# --------------------------------------------------------------------
def get_weather(config: WeatherConfig):
    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = config.openmeteo_url
    params = {
        "apikey": config.openmeteo_key,
        "latitude": 52.52,
        "longitude": 13.41,
        "current": ["temperature_2m", "is_day", "weather_code"],
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "sunrise",
            "sunset",
            "precipitation_probability_max",
        ],
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation {response.Elevation()} m asl")
    print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    # Current values. The order of variables needs to be the same as requested.
    current = response.Current()
    current_temperature_2m = current.Variables(0).Value()
    current_is_day = current.Variables(1).Value()
    current_weather_code = current.Variables(2).Value()

    print(f"Current time {current.Time()}")
    print(f"Current temperature_2m {current_temperature_2m}")
    print(f"Current is_day {current_is_day}")
    print(f"Current weather_code {current_weather_code}")

    # Process daily data. The order of variables needs to be the same as requested.
    daily = response.Daily()
    daily_weather_code = daily.Variables(0).ValuesAsNumpy()
    daily_temperature_2m_max = daily.Variables(1).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(2).ValuesAsNumpy()
    daily_sunrise = daily.Variables(3).ValuesAsNumpy()
    daily_sunset = daily.Variables(4).ValuesAsNumpy()
    daily_precipitation_probability_max = daily.Variables(5).ValuesAsNumpy()

    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left",
        )
    }
    daily_data["weather_code"] = daily_weather_code
    daily_data["temperature_2m_max"] = daily_temperature_2m_max
    daily_data["temperature_2m_min"] = daily_temperature_2m_min
    daily_data["sunrise"] = daily_sunrise
    daily_data["sunset"] = daily_sunset
    daily_data["precipitation_probability_max"] = daily_precipitation_probability_max

    daily_dataframe = pd.DataFrame(data=daily_data)

    forecast: list[Weather] = []

    for idx, row in daily_dataframe.iterrows():
        forecast.append(
            Weather(
                dt=pd.to_datetime(row["date"]),
                code=row["weather_code"],
                temperature=int(
                    round((row["temperature_2m_min"] + row["temperature_2m_max"]) / 2)
                ),
                high_temperature=int(round(row["temperature_2m_max"])),
                low_temperature=int(round(row["temperature_2m_min"])),
                precipitation=int(round(row["precipitation_probability_max"])),
            )
        )

    current_weather = Weather(
        dt=datetime.now(),
        code=current_weather_code,
        daytime=current_is_day,
        temperature=current_temperature_2m,
        high_temperature=forecast[0].high_temperature,
        low_temperature=forecast[0].low_temperature,
        precipitation=forecast[0].precipitation,
    )

    return WeatherReport(current_weather, forecast)
