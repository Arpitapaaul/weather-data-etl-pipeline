"""
src/load.py
-----------
DATA LOADING LAYER — Step 4 of the ETL Pipeline.

Responsibilities:
    1. Create the MySQL database if it does not exist.
    2. Create required tables automatically using SQLAlchemy ORM.
    3. Insert clean, validated weather records.
    4. Prevent duplicate entries using ON DUPLICATE KEY UPDATE.
    5. Log every database operation.
    6. Provide query helpers for the reporting layer.

Senior Engineer Note:
    We separate table definition (DDL) from data operations (DML).
    SQLAlchemy's ORM handles schema creation portably.
    For duplicate prevention, we use a UNIQUE KEY on (city, recorded_at) —
    the database itself enforces integrity, not just application code.
"""

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import (
    create_engine, text, Column, Integer, Float, String,
    DateTime, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Session
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from utils import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# ORM BASE AND TABLE DEFINITION
# ──────────────────────────────────────────────

class Base(DeclarativeBase):
    """SQLAlchemy declarative base — all ORM models inherit from this."""
    pass


class WeatherRecord(Base):
    """
    ORM model representing one row in the weather_data table.

    Design decisions:
        - 'id' is a surrogate auto-increment primary key.
        - UNIQUE constraint on (city, recorded_at) prevents duplicate
          API readings from being stored twice.
        - Float types for measurements allow NULL (sensor could fail).
        - inserted_at is auto-set to the current DB time on insert.
    """
    __tablename__ = "weather_data"

    id                  = Column(Integer,  primary_key=True, autoincrement=True)
    city                = Column(String(100), nullable=False)
    country             = Column(String(10),  nullable=True)
    temperature_c       = Column(Float,  nullable=True)
    feels_like_c        = Column(Float,  nullable=True)
    temp_min_c          = Column(Float,  nullable=True)
    temp_max_c          = Column(Float,  nullable=True)
    humidity_pct        = Column(Integer, nullable=True)
    pressure_hpa        = Column(Integer, nullable=True)
    wind_speed_mps      = Column(Float,  nullable=True)
    wind_direction_deg  = Column(Integer, nullable=True)
    weather_condition   = Column(String(100), nullable=True)
    weather_description = Column(String(255), nullable=True)
    visibility_m        = Column(Integer, nullable=True)
    cloudiness_pct      = Column(Integer, nullable=True)
    heat_index_c        = Column(Float,  nullable=True)
    comfort_level       = Column(String(50),  nullable=True)
    recorded_at         = Column(DateTime, nullable=False)
    extracted_at        = Column(DateTime, nullable=True)
    inserted_at         = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Prevent duplicate readings for the same city at the same time
    __table_args__ = (
        UniqueConstraint("city", "recorded_at", name="uq_city_recorded_at"),
    )

    def __repr__(self):
        return (
            f"<WeatherRecord city={self.city!r} "
            f"temp={self.temperature_c}°C "
            f"at={self.recorded_at}>"
        )


# ──────────────────────────────────────────────
# LOADER CLASS
# ──────────────────────────────────────────────

class WeatherLoader:
    """
    Manages database connectivity, schema setup, and data insertion.
    """

    def __init__(self):
        self.engine = None
        self._ensure_database()
        self._setup_engine()
        self._create_tables()

    # ── Database Initialisation ──────────────────

    def _ensure_database(self) -> None:
        """
        Create the MySQL database if it doesn't exist.
        We connect without specifying the database name first.
        """
        try:
            # Temporarily connect without a database name
            tmp_engine = create_engine(
                config.DB_URL_NO_DB,
                echo=False,
                pool_pre_ping=True,
            )
            with tmp_engine.connect() as conn:
                conn.execute(
                    text(f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
                         f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                )
                conn.commit()
            tmp_engine.dispose()
            logger.info(
                f"[LOAD] Database '{config.DB_NAME}' is ready"
            )
        except sa.exc.OperationalError as e:
            logger.error(
                f"[LOAD] Cannot connect to MySQL — "
                f"check DB_HOST, DB_USER, DB_PASSWORD in config.py\n{e}"
            )
            raise

    def _setup_engine(self) -> None:
        """Create the SQLAlchemy engine connected to our database."""
        self.engine = create_engine(
            config.DB_URL,
            echo=False,            # Set True to see raw SQL in terminal
            pool_size=5,           # Keep 5 connections in pool
            pool_pre_ping=True,    # Test connections before using them
            pool_recycle=3600,     # Recycle connections after 1 hour
        )
        logger.info("[LOAD] SQLAlchemy engine created")

    def _create_tables(self) -> None:
        """
        Create all tables if they don't exist.
        SQLAlchemy's create_all() is idempotent — safe to call every run.
        """
        Base.metadata.create_all(bind=self.engine)
        logger.info("[LOAD] Database tables verified/created")

    # ── Data Insertion ────────────────────────────

    def load(self, df: pd.DataFrame) -> dict:
        """
        Insert the clean DataFrame into the MySQL database.

        Uses INSERT IGNORE to skip rows that violate the UNIQUE constraint
        (same city + recorded_at) without raising an error. This makes the
        pipeline safe to re-run without creating duplicates.

        Args:
            df: Clean, validated DataFrame from WeatherValidator.

        Returns:
            Dict with insertion statistics.
        """
        if df.empty:
            logger.warning("[LOAD] Empty DataFrame — nothing to insert")
            return {"inserted": 0, "skipped": 0, "failed": 0}

        logger.info(f"[LOAD] Attempting to insert {len(df)} records")

        inserted = 0
        skipped  = 0
        failed   = 0

        # ── Column mapping: DataFrame column → ORM attribute ──
        column_map = {
            "city":                "city",
            "country":             "country",
            "temperature_c":       "temperature_c",
            "feels_like_c":        "feels_like_c",
            "temp_min_c":          "temp_min_c",
            "temp_max_c":          "temp_max_c",
            "humidity_pct":        "humidity_pct",
            "pressure_hpa":        "pressure_hpa",
            "wind_speed_mps":      "wind_speed_mps",
            "wind_direction_deg":  "wind_direction_deg",
            "weather_condition":   "weather_condition",
            "weather_description": "weather_description",
            "visibility_m":        "visibility_m",
            "cloudiness_pct":      "cloudiness_pct",
            "heat_index_c":        "heat_index_c",
            "comfort_level":       "comfort_level",
            "recorded_at":         "recorded_at",
            "extracted_at":        "extracted_at",
        }

        with Session(self.engine) as session:
            for _, row in df.iterrows():
                try:
                    record_kwargs = {}
                    for df_col, orm_attr in column_map.items():
                        if df_col in df.columns:
                            val = row[df_col]
                            # Convert pandas NA types to Python None
                            if pd.isna(val):
                                val = None
                            # Convert pandas Timestamp → Python datetime
                            elif isinstance(val, pd.Timestamp):
                                val = val.to_pydatetime()
                            record_kwargs[orm_attr] = val

                    record = WeatherRecord(**record_kwargs)
                    session.add(record)
                    session.flush()   # Flush to catch constraint violations early
                    inserted += 1

                except sa.exc.IntegrityError:
                    # UniqueConstraint violation → duplicate record, skip it
                    session.rollback()
                    skipped += 1
                    city = row.get("city", "UNKNOWN")
                    logger.debug(
                        f"[LOAD] Skipped duplicate: {city} @ {row.get('recorded_at')}"
                    )
                except Exception as e:
                    session.rollback()
                    failed += 1
                    logger.error(f"[LOAD] Failed to insert row: {e}")

            # Commit all successfully inserted rows at once
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"[LOAD] Commit failed: {e}")
                raise

        stats = {"inserted": inserted, "skipped": skipped, "failed": failed}
        logger.info(
            f"[LOAD] Complete — "
            f"Inserted: {inserted}, Skipped (duplicates): {skipped}, "
            f"Failed: {failed}"
        )
        return stats

    # ── Query Helpers for Reporting ───────────────

    def fetch_all(self) -> pd.DataFrame:
        """Fetch all records from weather_data as a DataFrame."""
        query = "SELECT * FROM weather_data ORDER BY recorded_at DESC"
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        logger.info(f"[LOAD] Fetched {len(df)} records from database")
        return df

    def fetch_latest(self) -> pd.DataFrame:
        """Fetch only the most recent record for each city."""
        query = """
            SELECT wd.*
            FROM weather_data wd
            INNER JOIN (
                SELECT city, MAX(recorded_at) AS max_ts
                FROM weather_data
                GROUP BY city
            ) latest ON wd.city = latest.city AND wd.recorded_at = latest.max_ts
            ORDER BY wd.city
        """
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        logger.info(f"[LOAD] Fetched latest record for {len(df)} cities")
        return df

    def fetch_city_stats(self) -> pd.DataFrame:
        """
        Aggregate statistics per city — used by the reporting layer.
        Returns min, max, avg temperature and humidity per city.
        """
        query = """
            SELECT
                city,
                COUNT(*)                        AS total_readings,
                ROUND(AVG(temperature_c), 2)    AS avg_temp_c,
                ROUND(MIN(temperature_c), 2)    AS min_temp_c,
                ROUND(MAX(temperature_c), 2)    AS max_temp_c,
                ROUND(AVG(humidity_pct), 1)     AS avg_humidity_pct,
                ROUND(AVG(wind_speed_mps), 2)   AS avg_wind_speed_mps,
                MIN(recorded_at)                AS first_reading,
                MAX(recorded_at)                AS last_reading
            FROM weather_data
            GROUP BY city
            ORDER BY avg_temp_c DESC
        """
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        logger.info(f"[LOAD] City stats fetched for {len(df)} cities")
        return df

    def dispose(self):
        """Release all database connections back to the pool."""
        if self.engine:
            self.engine.dispose()
            logger.debug("[LOAD] Engine disposed — connections released")


# ──────────────────────────────────────────────
# STANDALONE TEST (requires MySQL running)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import pandas as pd

    loader = WeatherLoader()

    test_df = pd.DataFrame([
        {
            "city": "Kolkata",
            "country": "IN",
            "temperature_c": 30,
            "humidity_pct": 80,
            "pressure_hpa": 1005,
            "weather_condition": "Clouds",
            "recorded_at": pd.Timestamp.now()
        }
    ])

    result = loader.load(test_df)
    print(result)

    df = loader.fetch_all()
    print(df)

    loader.dispose()
