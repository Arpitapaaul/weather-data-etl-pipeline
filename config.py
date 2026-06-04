#from dotenv import load_dotenv
import os
from pathlib import Path

#load_dotenv()

# PROJECT PATHS
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"

for _dir in [RAW_DIR, PROCESSED_DIR, LOGS_DIR, REPORTS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# OPENWEATHER CONFIG
API_KEY = "39b0e95cce8423acec3db777d8cc6cdc"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
UNITS = "metric"
TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 2

# USER CAN ENTER:
# Kolkata
# Delhi
# India
# London
# Tokyo
# Paris,FR
# California,US

DEFAULT_LOCATION = "Kolkata"

CITIES = [
    "Kolkata",
    "Delhi",
    "Mumbai",
    "Bangalore",
    "Chennai"
]

# MYSQL CONFIG
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "password"
DB_NAME = "weather_db"

DB_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

DB_URL_NO_DB = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}"
)

# REPORT PATHS
REPORT_CSV_PATH = REPORTS_DIR / "weather_summary.csv"
REPORT_EXCEL_PATH = REPORTS_DIR / "weather_report.xlsx"

# ─────────────────────────────────────────────
# LOGGING CONFIGURATION
# ─────────────────────────────────────────────

LOG_FILE = LOGS_DIR / "weather_pipeline.log"

LOG_LEVEL = "DEBUG"

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
)

LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_MAX_BYTES = 5 * 1024 * 1024

LOG_BACKUP_COUNT = 3

# DATA VALIDATION RULES

TEMP_MIN = -90.0
TEMP_MAX = 60.0

HUMIDITY_MIN = 0
HUMIDITY_MAX = 100

PRESSURE_MIN = 870
PRESSURE_MAX = 1085


