"""
database.py
-----------
Database facade used by the Streamlit application.

Provides:
    save_weather(df)         — Insert a weather record into MySQL.
    get_all_weather()        — Fetch all records as a DataFrame.
    get_cached_weather(city) — Return the latest DB record for a city if it
                               was inserted within the last 1 minute, else None.
    fetch_search_analytics() — Return city search counts and activity trends.
"""

from datetime import datetime, timedelta, timezone
import pandas as pd
from load import WeatherLoader

loader = WeatherLoader()


def save_weather(df: pd.DataFrame) -> dict:
    """Insert a weather DataFrame into the database."""
    return loader.load(df)


def get_all_weather() -> pd.DataFrame:
    """Fetch all weather records ordered by most recent first."""
    return loader.fetch_all()


def get_cached_weather(city: str) -> dict | None:
    """
    DB-first cache check with a 1-minute freshness window.

    Returns a weather dict (same shape as _call_api in app.py) if a record
    for this city was inserted within the last 60 seconds.
    Returns None if no fresh record exists — caller should hit the API.
    """
    try:
        from sqlalchemy import text

        cutoff = datetime.utcnow() - timedelta(minutes=1)

        query = text("""
            SELECT *
            FROM weather_data
            WHERE LOWER(city) = LOWER(:city)
              AND inserted_at >= :cutoff
            ORDER BY inserted_at DESC
            LIMIT 1
        """)

        with loader.engine.connect() as conn:
            result = conn.execute(query, {"city": city, "cutoff": cutoff})
            row = result.fetchone()

        if row is None:
            return None

        row_dict = dict(row._mapping)

        # Re-map DB columns → the dict shape the UI expects
        return {
            "city":            row_dict.get("city", city),
            "country":         row_dict.get("country", ""),
            "temperature":     int(row_dict.get("temperature_c") or 0),
            "feels_like":      int(row_dict.get("feels_like_c") or 0),
            "humidity":        int(row_dict.get("humidity_pct") or 0),
            "pressure":        int(row_dict.get("pressure_hpa") or 0),
            "wind_speed":      float(row_dict.get("wind_speed_mps") or 0.0),
            "condition":       row_dict.get("weather_condition", "Clear"),
            "description":     row_dict.get("weather_description", ""),
            "visibility":      int(row_dict.get("visibility_m") or 10000),
            "clouds":          int(row_dict.get("cloudiness_pct") or 0),
            "temp_min":        int(row_dict.get("temp_min_c") or row_dict.get("temperature_c") or 0),
            "temp_max":        int(row_dict.get("temp_max_c") or row_dict.get("temperature_c") or 0),
            "timezone_offset": 0,   # Not stored in DB; city-local time will use UTC
            "sunrise_utc":     0,
            "sunset_utc":      0,
        }

    except Exception:
        return None


def fetch_search_analytics() -> dict:
    """
    Returns analytics DataFrames derived from all stored weather records.

    Returns a dict with:
        recent_searches   — Latest 20 records (for the Recent Searches table)
        city_search_counts — Count of searches per city (most searched cities)
        top5_cities        — Top 5 cities by search count
        activity_over_time — Number of searches grouped by hour
    """
    try:
        df = loader.fetch_all()

        if df.empty:
            empty = pd.DataFrame()
            return {
                "recent_searches":    empty,
                "city_search_counts": empty,
                "top5_cities":        empty,
                "activity_over_time": empty,
            }

        # ── Recent Searches (latest 20) ──
        recent_cols = ["inserted_at", "city", "temperature_c",
                        "humidity_pct", "pressure_hpa", "weather_condition"]
        available   = [c for c in recent_cols if c in df.columns]
        recent      = df[available].head(20).copy()
        recent.rename(columns={
            "inserted_at":      "Search Time",
            "city":             "City",
            "temperature_c":    "Temp (°C)",
            "humidity_pct":     "Humidity (%)",
            "pressure_hpa":     "Pressure (hPa)",
            "weather_condition":"Condition",
        }, inplace=True)

        # ── City Search Counts ──
        city_counts = (
            df["city"]
            .value_counts()
            .reset_index()
        )
        city_counts.columns = ["City", "Search Count"]

        # ── Top 5 Cities ──
        top5 = city_counts.head(5).copy()

        # ── Search Activity Over Time (grouped by hour) ──
        if "inserted_at" in df.columns:
            df["inserted_at"] = pd.to_datetime(df["inserted_at"], errors="coerce")
            activity = (
                df.dropna(subset=["inserted_at"])
                .set_index("inserted_at")
                .resample("1h")
                .size()
                .reset_index()
            )
            activity.columns = ["Hour", "Searches"]
        else:
            activity = pd.DataFrame()

        return {
            "recent_searches":    recent,
            "city_search_counts": city_counts,
            "top5_cities":        top5,
            "activity_over_time": activity,
        }

    except Exception:
        empty = pd.DataFrame()
        return {
            "recent_searches":    empty,
            "city_search_counts": empty,
            "top5_cities":        empty,
            "activity_over_time": empty,
        }
