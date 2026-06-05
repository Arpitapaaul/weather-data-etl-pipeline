# 🌦️ WeatherIQ — Real-Time Weather Data ETL Pipeline & Analytics Dashboard

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-1.45.1-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Pandas-2.2.3-150458?style=for-the-badge&logo=pandas&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0.23-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" />
  <img src="https://img.shields.io/badge/OpenWeatherMap-API-EB6E4B?style=for-the-badge&logo=openweathermap&logoColor=white" />
  <img src="https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white" />
  <img src="https://img.shields.io/badge/Plotly-5.24.1-3F4F75?style=for-the-badge&logo=plotly&logoColor=white" />
</p>

An end-to-end data engineering project that ingests live weather data from the OpenWeatherMap API, orchestrates a 5-stage ETL pipeline, persists clean records to a MySQL database via SQLAlchemy ORM, and visualises KPIs and trends on an interactive Streamlit analytics dashboard.

---

## 🏗️ Architecture

```
OpenWeatherMap API
       │
       ▼
Extract (extract.py)          ← Fetch + retry + save raw JSON
       │
       ▼
Transform (transform.py)      ← Parse, cast types, derive heat_index & comfort_level
       │
       ▼
Validate (validate.py)        ← Null / range / duplicate checks → JSON report
       │
       ▼
Load (load.py)                ← SQLAlchemy ORM → MySQL (UNIQUE key dedup)
       │
       ▼
Report (report.py)            ← 7 analytics reports → CSV + Excel
       │
       ▼
Streamlit Dashboard (app.py)  ← Live Weather Page + Analytics Dashboard
```

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| Ingestion | Python, Requests |
| Data Processing | Pandas 2.2.3 |
| Data Validation | Custom rule engine (validate.py) |
| Storage | MySQL 8.0 |
| ORM | SQLAlchemy 2.0.23 |
| Reporting | openpyxl (multi-sheet Excel) |
| Visualisation | Streamlit 1.45.1, Plotly 5.24.1 |
| Logging | Python RotatingFileHandler |
| Environment | python-dotenv |

---

## 📊 Features

- Live weather data ingestion via OpenWeatherMap API with exponential-backoff retry
- Idempotent extraction — raw JSON saved to disk before any transformation
- Derived column engineering: `heat_index_c` (Steadman formula) and `comfort_level` classification
- 6-rule data validation engine with CRITICAL / WARNING severity tagging and structured JSON reports
- Schema-enforced database loading with `UNIQUE KEY (city, recorded_at)` duplicate prevention
- 7 analytical reports exported to multi-sheet Excel and CSV on every pipeline run
- Rotating pipeline logs (5 MB max, 3 backup files)
- Immersive Streamlit dashboard with particle animations (rain, snow, stars, lightning) that respond to live weather conditions
- Dual-page app: Live Weather search page + Analytics Dashboard backed by MySQL historical data
- Simulated hourly and 7-day forecasts displayed in each city's local timezone

---

## 🚀 How to Run

1. Clone the repository
   ```bash
   git clone https://github.com/<your-username>/weatheriq.git
   cd weatheriq
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Add your OpenWeatherMap API key in a `.env` file
   ```env
   OWM_API_KEY=your_api_key_here
   ```

4. Set your MySQL credentials in `config.py`
   ```python
   DB_HOST     = "localhost"
   DB_PORT     = 3306
   DB_USER     = "root"
   DB_PASSWORD = "your_password"
   DB_NAME     = "weather_db"
   ```

5. Run the full ETL pipeline
   ```bash
   python main.py
   ```

6. Launch the Streamlit dashboard
   ```bash
   streamlit run app.py
   ```

---

## 🌐 Live Demo

> **[https://weather-data-etl-pipeline.onrender.com/]**

---

## 📁 Project Structure

```
weather report/
├── app.py              # Streamlit app entry point (Live Weather + Dashboard routing)
├── dashboard.py        # Analytics Dashboard page (historical DB charts)
├── main.py             # Pipeline orchestrator — runs all 5 ETL stages in sequence
├── extract.py          # Stage 1: API extraction with retry logic
├── transform.py        # Stage 2: JSON parsing, type casting, derived columns
├── validate.py         # Stage 3: Multi-rule data quality validation engine
├── load.py             # Stage 4: SQLAlchemy ORM database loading
├── report.py           # Stage 5: Analytics reporting and CSV/Excel export
├── config.py           # Centralised configuration (API, DB, paths, thresholds)
├── database.py         # Database facade used by the Streamlit app
├── utils.py            # Shared utilities (logger, timestamp, JSON I/O, timer)
├── requirements.txt    # Python dependency manifest
├── .env                # Environment secrets (not committed)
├── .gitignore          # Excludes .env, __pycache__, logs, CSV artefacts
├── .streamlit/
│   └── config.toml     # Streamlit dark theme configuration
├── data/
│   ├── raw/            # Raw JSON API responses (audit trail)
│   └── processed/      # Transformed CSVs + JSON validation reports
├── reports/            # Final CSV and Excel analytical exports
└── logs/
    └── weather_pipeline.log   # Rotating structured pipeline log
```

---

## ⚙️ ETL Pipeline Explanation

### Stage 1 — Extract (`extract.py`)
Connects to the OpenWeatherMap `/data/2.5/weather` endpoint using a persistent `requests.Session` for TCP connection reuse. Implements exponential-backoff retry across configurable attempts. Raw JSON responses are tagged with `_extracted_at` UTC timestamps and saved to `data/raw/` before any processing — enabling full pipeline replay without re-calling the API.

### Stage 2 — Transform (`transform.py`)
Flattens nested OWM JSON into a clean, typed Pandas DataFrame. Applies nullable dtype casting (`Float64`, `Int64`, `string`) and computes two derived columns: `heat_index_c` via Steadman's simplified formula and `comfort_level` as a human-readable temperature category (`Cold` / `Cool` / `Comfortable` / `Warm` / `Hot`). Saves the processed DataFrame to `data/processed/`.

### Stage 3 — Validate (`validate.py`)
Runs six sequential data quality checks:

| Check | Severity | Action |
|---|---|---|
| Null values in critical columns | CRITICAL | Row dropped |
| Temperature range [-90°C, 60°C] | CRITICAL | Row dropped |
| Humidity range [0%, 100%] | CRITICAL | Row dropped |
| Pressure range [870, 1085 hPa] | WARNING | Flagged only |
| Duplicate (city, recorded_at) pairs | CRITICAL | Row dropped |
| City name length < 2 characters | WARNING | Flagged only |

Saves a structured JSON validation report (pass rate, issue details, null counts) to `data/processed/`.

### Stage 4 — Load (`load.py`)
Uses SQLAlchemy's Declarative ORM to auto-create the MySQL database and `weather_data` table if absent (idempotent). A `UNIQUE KEY (city, recorded_at)` database-level constraint prevents duplicates. `IntegrityError` exceptions are caught per row and silently skipped — making every pipeline run safe to re-execute on the same data. Connection pool configured with `pool_size=5` and `pool_recycle=3600`.

### Stage 5 — Report (`report.py`)
Generates seven analytical DataFrames from the loaded data and exports them to a multi-sheet Excel workbook and a summary CSV:

- City Temperature Summary (avg, min, max per city)
- Humidity Analysis
- Wind Speed Analysis
- Most Common Weather Conditions
- Daily Weather Summary
- Comfort Level Distribution
- Heat Index Comparison

---

## 📈 Dashboard Overview

### 🌦 Live Weather Page
- City search with `st.session_state` persistence
- Hero weather card with time-of-day-aware condition icons (moon at night, sun during day, sunrise at dawn/dusk)
- Live metric panels: Feels Like, Humidity, Wind Speed, Pressure — each with a visual gauge
- Simulated hourly (8-hour) and 7-day forecast displayed in the city's local timezone
- CSS particle animations: rain drops, snowflakes, twinkling stars, lightning flash, sun glow, moon orb, dawn rays — all responding to live weather condition

### 📊 Analytics Dashboard
- KPI row: total records, city count, average temperature, average humidity
- Temperature and humidity time-series line charts from MySQL historical data
- City temperature comparison bar chart
- Weather condition distribution pie chart (Plotly)
- Full paginated raw data table

---

## 🚢 Deployment

### Streamlit Community Cloud

1. Push the repository to GitHub (confirm `.env` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub account
3. Set the main file to `app.py`
4. Add secrets under **Settings → Secrets**:
   ```toml
   OWM_API_KEY = "your_api_key"
   ```
5. Point `config.py` database credentials to a hosted MySQL instance (e.g. PlanetScale, Railway, AWS RDS)
6. Click **Deploy**

### Cron Scheduling (Linux)

```bash
# Run the ETL pipeline automatically every hour
0 * * * * /path/to/venv/bin/python /path/to/project/main.py >> /path/to/project/logs/cron.log 2>&1
```

---


## 🔭 Future Enhancements

- Apache Airflow DAG for scheduled, observable pipeline runs
- Air Quality Index (AQI) integration via OWM Air Pollution API
- UV Index and sunrise/sunset data from OWM One Call API
- Automated Slack/email alerts when validation pass rate drops below threshold
- `pytest` unit test suite for transform, validate, and report modules
- `docker-compose.yml` for zero-setup local development with MySQL
- FastAPI microservice to expose pipeline trigger and latest-data endpoints
- PostgreSQL support alongside MySQL

---

## 👨‍💻 Developer Information

| Field | Details |
|---|---|
| **Developer** | prakshwer |
| **Project Type** | Data Engineering / ETL Pipeline / Real-Time Analytics |
| **Architecture Pattern** | Layered ETL with Orchestrator (`main.py`) |
| **Database Design** | Surrogate PK + composite UNIQUE constraint |
| **API** | OpenWeatherMap REST API v2.5 |
| **Python Version** | 3.11+ |

---

## 📄 License

This project is licensed under the **MIT License** — feel free to use, modify, and distribute with attribution.

---

<p align="center">Built with ☁️ real weather data, 🐍 Python, and ❤️ for data engineering.</p