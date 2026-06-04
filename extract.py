"""
src/extract.py
--------------
DATA EXTRACTION LAYER — Step 1 of the ETL Pipeline.

Responsibilities:
    1. Connect to the OpenWeatherMap REST API.
    2. Fetch current weather data for each configured city.
    3. Retry automatically on transient network failures.
    4. Save raw JSON responses to disk for auditing/debugging.
    5. Return collected raw data to the next pipeline stage.

Senior Engineer Note:
    Always save raw API responses BEFORE transforming them. If your
    transformation logic has a bug, you can replay from raw JSON without
    making expensive API calls again. This is called "idempotent extraction."
"""

import time
import requests
from pathlib import Path
from datetime import datetime

import requests
import os

API_KEY = os.getenv("OWM_API_KEY")

def fetch_city_weather(city):
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={API_KEY}&units=metric"
    )

    response = requests.get(url)

    if response.status_code == 200:
        return response.json()

    return None

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from utils import get_logger, get_timestamp, save_json

logger = get_logger(__name__)


class WeatherExtractor:
    """
    Handles all data extraction from the OpenWeatherMap API.

    Attributes:
        api_key  : OpenWeatherMap API key.
        base_url : Base endpoint URL.
        units    : Unit system — 'metric' gives Celsius.
        session  : Persistent requests.Session for connection reuse.
    """

    def __init__(self):
        self.api_key  = config.API_KEY
        self.base_url = config.BASE_URL
        self.units    = config.UNITS
        # Using a Session reuses the underlying TCP connection across
        # multiple requests — faster and more efficient than repeated
        # requests.get() calls.
        self.session  = requests.Session()
        logger.info("WeatherExtractor initialised")

    # ──────────────────────────────────────────────
    # PRIVATE: Fetch weather for a single city
    # ──────────────────────────────────────────────
    def _fetch_city(self, city: str) -> dict | None:
        """
        Call the OpenWeatherMap API for one city.
        Implements exponential-backoff retry on failure.

        Args:
            city: City name string, e.g. "Kolkata".

        Returns:
            Parsed JSON dict on success, or None on total failure.
        """
        params = {
            "q":     city,
            "appid": self.api_key,
            "units": self.units,
        }

        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                logger.debug(
                    f"API call — city: {city}, attempt: {attempt}/{config.MAX_RETRIES}"
                )
                response = self.session.get(
                    self.base_url,
                    params=params,
                    timeout=config.TIMEOUT,
                )

                # Raise HTTPError for 4xx / 5xx responses
                response.raise_for_status()

                data = response.json()
                logger.info(
                    f"[EXTRACT] SUCCESS — {city} | "
                    f"HTTP {response.status_code} | "
                    f"Temp: {data.get('main', {}).get('temp')}°C"
                )
                return data

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else "N/A"
                if status == 401:
                    # Invalid API key — no point retrying
                    logger.error(
                        f"[EXTRACT] AUTH ERROR — Invalid API key. "
                        f"Set OWM_API_KEY environment variable."
                    )
                    return None
                elif status == 404:
                    logger.warning(f"[EXTRACT] City not found: '{city}'")
                    return None
                else:
                    logger.warning(
                        f"[EXTRACT] HTTP {status} for {city} "
                        f"(attempt {attempt}): {e}"
                    )

            except requests.exceptions.ConnectionError:
                logger.warning(
                    f"[EXTRACT] Connection error for {city} "
                    f"(attempt {attempt}). Check internet connection."
                )
            except requests.exceptions.Timeout:
                logger.warning(
                    f"[EXTRACT] Timeout for {city} "
                    f"(attempt {attempt}) after {config.TIMEOUT}s"
                )
            except requests.exceptions.RequestException as e:
                logger.error(f"[EXTRACT] Unexpected error for {city}: {e}")

            # Exponential backoff: wait 2s, then 4s, then 8s …
            if attempt < config.MAX_RETRIES:
                wait = config.RETRY_DELAY * (2 ** (attempt - 1))
                logger.info(f"[EXTRACT] Retrying {city} in {wait}s …")
                time.sleep(wait)

        logger.error(
            f"[EXTRACT] FAILED — {city} after {config.MAX_RETRIES} attempts"
        )
        return None

    # ──────────────────────────────────────────────
    # PUBLIC: Fetch all cities
    # ──────────────────────────────────────────────
    def fetch_all_cities(self, cities: list[str] | None = None) -> list[dict]:
        """
        Fetch weather data for all configured cities.

        Args:
            cities: Optional override list of city names.
                    Defaults to config.CITIES.

        Returns:
            List of raw API response dicts (only successful ones).
        """
        cities = cities or config.CITIES
        logger.info(
            f"[EXTRACT] Starting extraction for {len(cities)} cities: "
            f"{', '.join(cities)}"
        )

        raw_responses = []
        failed_cities = []

        for city in cities:
            data = self._fetch_city(city)
            if data:
                # Tag each record with the extraction timestamp
                data["_extracted_at"] = datetime.utcnow().isoformat()
                raw_responses.append(data)
            else:
                failed_cities.append(city)

        # ── Save raw responses to disk for audit trail ──
        if raw_responses:
            timestamp = get_timestamp()
            raw_filepath = config.RAW_DIR / f"raw_weather_{timestamp}.json"
            save_json(raw_responses, raw_filepath)
            logger.info(f"[EXTRACT] Raw data saved → {raw_filepath}")

        logger.info(
            f"[EXTRACT] Complete — "
            f"Success: {len(raw_responses)}, "
            f"Failed: {len(failed_cities)}"
        )
        if failed_cities:
            logger.warning(f"[EXTRACT] Failed cities: {failed_cities}")

        return raw_responses

    def close(self):
        """Close the underlying HTTP session gracefully."""
        self.session.close()
        logger.debug("HTTP session closed")


# ──────────────────────────────────────────────
# STANDALONE TEST — run this file directly to test extraction
# ──────────────────────────────────────────────
if __name__ == "__main__":
    extractor = WeatherExtractor()
    results = extractor.fetch_all_cities()
    print(f"\nFetched {len(results)} records")
    if results:
        import json
        print(json.dumps(results[0], indent=2))
    extractor.close()
