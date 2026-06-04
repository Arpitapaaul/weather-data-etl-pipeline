"""
src/transform.py
----------------
DATA TRANSFORMATION LAYER — Step 2 of the ETL Pipeline.

Responsibilities:
    1. Parse raw JSON API responses into a structured Pandas DataFrame.
    2. Extract only the fields we care about.
    3. Rename columns to clean, consistent names.
    4. Convert and standardise data types.
    5. Add calculated/derived columns for richer analysis.
    6. Save the processed DataFrame as a CSV for the next stage.

Senior Engineer Note:
    Transformation is where raw, messy external data becomes YOUR clean,
    typed, business-ready data. Keep transformations deterministic and
    testable — given the same input, always produce the same output.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from utils import get_logger, get_timestamp

logger = get_logger(__name__)

# Columns we want in the final DataFrame — in display order
FINAL_COLUMNS = [
    "city",
    "country",
    "temperature_c",
    "feels_like_c",
    "temp_min_c",
    "temp_max_c",
    "humidity_pct",
    "pressure_hpa",
    "wind_speed_mps",
    "wind_direction_deg",
    "weather_condition",
    "weather_description",
    "visibility_m",
    "cloudiness_pct",
    "recorded_at",           # Original timestamp from API (UTC)
    "extracted_at",          # When our pipeline fetched the data
    "heat_index_c",          # Derived: feels hotter in humidity
    "comfort_level",         # Derived: human-readable comfort category
]


class WeatherTransformer:
    """
    Transforms raw OpenWeatherMap API responses into a clean DataFrame.
    """

    def transform(self, raw_records: list[dict]) -> pd.DataFrame:
        """
        Main transformation entry point.

        Args:
            raw_records: List of raw API response dicts from the extractor.

        Returns:
            Clean, typed Pandas DataFrame ready for validation and loading.
        """
        if not raw_records:
            logger.warning("[TRANSFORM] No records to transform — empty input")
            return pd.DataFrame()

        logger.info(
            f"[TRANSFORM] Starting transformation of {len(raw_records)} records"
        )

        parsed_rows = []
        failed_count = 0

        for record in raw_records:
            try:
                row = self._parse_record(record)
                parsed_rows.append(row)
            except (KeyError, TypeError, ValueError) as e:
                city = record.get("name", "UNKNOWN")
                logger.error(f"[TRANSFORM] Failed to parse record for {city}: {e}")
                failed_count += 1

        if not parsed_rows:
            logger.error("[TRANSFORM] All records failed to parse")
            return pd.DataFrame()

        df = pd.DataFrame(parsed_rows)
        df = self._cast_types(df)
        df = self._add_derived_columns(df)
        df = self._reorder_columns(df)

        # ── Save processed data to disk ──
        timestamp = get_timestamp()
        out_path = config.PROCESSED_DIR / f"processed_weather_{timestamp}.csv"
        df.to_csv(out_path, index=False)
        logger.info(f"[TRANSFORM] Processed data saved → {out_path}")

        logger.info(
            f"[TRANSFORM] Complete — "
            f"Parsed: {len(parsed_rows)}, Failed: {failed_count}"
        )
        return df

    # ──────────────────────────────────────────────
    # PRIVATE HELPERS
    # ──────────────────────────────────────────────

    def _parse_record(self, r: dict) -> dict:
        """
        Extract fields from a single raw API response dict.

        OpenWeatherMap response structure (abbreviated):
        {
            "name": "Kolkata",
            "sys":  { "country": "IN" },
            "main": { "temp": 32.5, "feels_like": 38.1, ... },
            "wind": { "speed": 3.2, "deg": 180 },
            "weather": [ { "main": "Clouds", "description": "..." } ],
            "dt":   1694784000,   ← Unix timestamp UTC
            ...
        }
        """
        # Safely extract nested dicts
        main    = r.get("main",    {})
        wind    = r.get("wind",    {})
        weather = r.get("weather", [{}])[0]   # First weather condition
        sys_    = r.get("sys",     {})
        clouds  = r.get("clouds",  {})

        # Convert Unix timestamp → readable UTC datetime
        dt_unix = r.get("dt")
        recorded_at = (
            datetime.fromtimestamp(dt_unix, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            if dt_unix else None
        )

        # Parse the extraction timestamp we added during extraction
        extracted_raw = r.get("_extracted_at", "")
        extracted_at = extracted_raw[:19].replace("T", " ") if extracted_raw else None

        return {
            "city":                r.get("name", "").strip(),
            "country":             sys_.get("country", ""),
            "temperature_c":       main.get("temp"),
            "feels_like_c":        main.get("feels_like"),
            "temp_min_c":          main.get("temp_min"),
            "temp_max_c":          main.get("temp_max"),
            "humidity_pct":        main.get("humidity"),
            "pressure_hpa":        main.get("pressure"),
            "wind_speed_mps":      wind.get("speed"),
            "wind_direction_deg":  wind.get("deg"),
            "weather_condition":   weather.get("main", ""),
            "weather_description": weather.get("description", "").title(),
            "visibility_m":        r.get("visibility"),
            "cloudiness_pct":    clouds,
            "recorded_at":         recorded_at,
            "extracted_at":        extracted_at,
        }

    def _cast_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enforce correct data types on every column.
        Using nullable integer/float types so NaN doesn't silently
        become 0 or cause type errors.
        """
        float_cols = [
            "temperature_c", "feels_like_c", "temp_min_c", "temp_max_c",
            "wind_speed_mps",
        ]
        int_cols = [
            "humidity_pct", "pressure_hpa", "wind_direction_deg",
            "visibility_m", "cloudiness_pct",
        ]

        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Float64")

        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        for col in ["recorded_at", "extracted_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        str_cols = ["city", "country", "weather_condition", "weather_description"]
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].astype("string")

        logger.debug("[TRANSFORM] Data types cast successfully")
        return df

    def _add_derived_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create new columns that add analytical value.

        heat_index_c:
            Combines temperature + humidity to estimate perceived temperature.
            Formula: Steadman's simplified heat index approximation.

        comfort_level:
            Categorises temperature into human-readable bands.
            Useful for grouping and filtering in reports.
        """
        # ── Heat Index (simplified Steadman formula) ──
        # Only meaningful above 27°C and 40% humidity
        T = df["temperature_c"].astype(float)
        H = df["humidity_pct"].astype(float)

        df["heat_index_c"] = (
            -8.78469475556
            + 1.61139411       * T
            + 2.33854883889    * H
            - 0.14611605       * T * H
            - 0.012308094      * T**2
            - 0.016424828      * H**2
            + 0.002211732      * T**2 * H
            + 0.00072546       * T * H**2
            - 0.000003582      * T**2 * H**2
        ).round(1)

        # ── Comfort Level ──
        def classify_comfort(temp):
            if pd.isna(temp):
                return "Unknown"
            elif temp < 10:
                return "Cold"
            elif temp < 20:
                return "Cool"
            elif temp < 28:
                return "Comfortable"
            elif temp < 35:
                return "Warm"
            else:
                return "Hot"

        df["comfort_level"] = T.apply(classify_comfort).astype("string")

        logger.debug("[TRANSFORM] Derived columns added: heat_index_c, comfort_level")
        return df

    def _reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only desired columns in the defined order."""
        existing = [c for c in FINAL_COLUMNS if c in df.columns]
        return df[existing]


# ──────────────────────────────────────────────
# STANDALONE TEST
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # Simulate what the extractor would return (mocked data)
    mock_records = [
        {
            "name": "Kolkata",
            "sys":  {"country": "IN"},
            "main": {
                "temp": 34.2, "feels_like": 40.1,
                "temp_min": 30.0, "temp_max": 36.5,
                "humidity": 78, "pressure": 1005,
            },
            "wind":    {"speed": 3.6, "deg": 200},
            "weather": [{"main": "Clouds", "description": "overcast clouds"}],
            "visibility": 6000,
            "clouds": {"all": 90},
            "dt": 1694784000,
            "_extracted_at": "2024-09-15T14:30:00.000000",
        }
    ]
    transformer = WeatherTransformer()
    df = transformer.transform(mock_records)
    print(df.to_string())
    print("\nDtypes:\n", df.dtypes)
