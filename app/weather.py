from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

import requests

from .database import SessionLocal
from .models import WeatherReport


OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"


def geocode_location(location: str) -> Optional[tuple[float, float]]:
    try:
        resp = requests.get(
            OPEN_METEO_GEOCODE,
            params={"name": location, "count": 1, "language": "en", "format": "json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        if not results:
            return None
        lat = results[0].get("latitude")
        lon = results[0].get("longitude")
        if lat is None or lon is None:
            return None
        return float(lat), float(lon)
    except Exception:
        return None


def fetch_forecast(lat: float, lon: float, tz: str, temp_unit: str | None = None, wind_speed_unit: str | None = None) -> Optional[Dict[str, Any]]:
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset,weathercode",
            "timezone": tz,
        }
        if temp_unit:
            # temp_unit expected 'F' or 'C'
            params["temperature_unit"] = "fahrenheit" if temp_unit.upper() == "F" else "celsius"
        resp = requests.get(OPEN_METEO_FORECAST, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        
        # Convert wind speed units if needed
        # Open-Meteo returns wind speed in mph when temp_unit is F, km/h when C
        # We need to convert if wind_speed_unit preference differs
        if wind_speed_unit and data:
            # Determine what unit the API returned based on temp_unit
            api_wind_unit = "mph" if temp_unit and temp_unit.upper() == "F" else "kmh"
            target_unit = wind_speed_unit.lower()
            
            if api_wind_unit != target_unit:
                # Conversion factors
                if api_wind_unit == "mph" and target_unit == "kmh":
                    # Convert mph to km/h: multiply by 1.60934
                    factor = 1.60934
                elif api_wind_unit == "kmh" and target_unit == "mph":
                    # Convert km/h to mph: multiply by 0.621371
                    factor = 0.621371
                else:
                    factor = 1.0
                
                # Convert current_weather wind speed if present
                if "current_weather" in data and "windspeed" in data["current_weather"]:
                    data["current_weather"]["windspeed"] = data["current_weather"]["windspeed"] * factor
                
                # Convert daily wind_speed_10m_max if present
                if "daily" in data and "wind_speed_10m_max" in data["daily"]:
                    data["daily"]["wind_speed_10m_max"] = [v * factor if v is not None else None for v in data["daily"]["wind_speed_10m_max"]]
        
        return data
    except Exception:
        return None


def update_weather(location: str, tz: str, ai_report: Optional[str] = None, lat: float | None = None, lon: float | None = None, temp_unit: str | None = None, wind_speed_unit: str | None = None) -> Optional[WeatherReport]:
    session = SessionLocal()
    try:
        coords = (lat, lon) if (lat is not None and lon is not None) else geocode_location(location)
        if not coords:
            return None
        lat2, lon2 = coords
        forecast = fetch_forecast(lat2, lon2, tz, temp_unit=temp_unit, wind_speed_unit=wind_speed_unit)
        if not forecast:
            return None
        wr = WeatherReport(
            location=location,
            latitude=lat2,
            longitude=lon2,
            fetched_at=datetime.utcnow(),
            forecast_json=json.dumps(forecast),
            ai_report=ai_report,
        )
        session.add(wr)
        session.commit()
        session.refresh(wr)
        return wr
    finally:
        session.close()
