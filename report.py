"""
src/report.py
-------------
REPORTING AND ANALYTICS LAYER — Step 5 of the ETL Pipeline.

Responsibilities:
    1. Query the database for analytical data.
    2. Generate multiple aggregated reports.
    3. Export reports to CSV and Excel (with multiple sheets).
    4. Print formatted summaries to the terminal.

Reports generated:
    - City temperature summary (avg, min, max)
    - Humidity analysis
    - Wind speed analysis
    - Most common weather conditions
    - Daily weather summary
    - Comfort level distribution
    - Heat index comparison

Senior Engineer Note:
    Reports should be reproducible. Given the same database state, always
    produce the same output. We use openpyxl for Excel export because it
    allows us to write multiple sheets and apply formatting — important for
    professional deliverables.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from utils import get_logger, get_timestamp

logger = get_logger(__name__)

# Try importing openpyxl — needed for Excel export
try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger.warning(
        "[REPORT] openpyxl not installed — Excel export will be skipped. "
        "Run: pip install openpyxl"
    )


class WeatherReporter:
    """
    Generates analytical reports from weather data.

    Args:
        df: The full weather DataFrame (fetched from the database
            or passed directly from the pipeline).
    """

    def __init__(self, df: pd.DataFrame):
        if df.empty:
            logger.warning("[REPORT] Empty DataFrame passed to reporter")
        self.df = df.copy()
        self._preprocess()

    def _preprocess(self):
        """Ensure numeric types are correct before aggregation."""
        numeric_cols = [
            "temperature_c", "feels_like_c", "temp_min_c", "temp_max_c",
            "humidity_pct", "pressure_hpa", "wind_speed_mps", "heat_index_c",
        ]
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        if "recorded_at" in self.df.columns:
            self.df["recorded_at"] = pd.to_datetime(self.df["recorded_at"], errors="coerce")
            self.df["date"] = self.df["recorded_at"].dt.date

    # ──────────────────────────────────────────────
    # INDIVIDUAL REPORT GENERATORS
    # ──────────────────────────────────────────────

    def city_temperature_summary(self) -> pd.DataFrame:
        """Average, min, max temperature per city — sorted by avg temp."""
        report = (
            self.df.groupby("city", as_index=False)
            .agg(
                readings        = ("temperature_c", "count"),
                avg_temp_c      = ("temperature_c", "mean"),
                min_temp_c      = ("temperature_c", "min"),
                max_temp_c      = ("temperature_c", "max"),
                avg_feels_like  = ("feels_like_c",  "mean"),
            )
            .round(2)
            .sort_values("avg_temp_c", ascending=False)
            .reset_index(drop=True)
        )
        logger.info("[REPORT] City temperature summary generated")
        return report

    def humidity_analysis(self) -> pd.DataFrame:
        """Average and max humidity per city."""
        report = (
            self.df.groupby("city", as_index=False)
            .agg(
                avg_humidity_pct = ("humidity_pct", "mean"),
                max_humidity_pct = ("humidity_pct", "max"),
                min_humidity_pct = ("humidity_pct", "min"),
            )
            .round(1)
            .sort_values("avg_humidity_pct", ascending=False)
            .reset_index(drop=True)
        )
        logger.info("[REPORT] Humidity analysis generated")
        return report

    def wind_speed_analysis(self) -> pd.DataFrame:
        """Average wind speed per city — useful for detecting windy periods."""
        report = (
            self.df.groupby("city", as_index=False)
            .agg(
                avg_wind_mps = ("wind_speed_mps", "mean"),
                max_wind_mps = ("wind_speed_mps", "max"),
            )
            .round(2)
            .sort_values("avg_wind_mps", ascending=False)
            .reset_index(drop=True)
        )
        logger.info("[REPORT] Wind speed analysis generated")
        return report

    def common_weather_conditions(self) -> pd.DataFrame:
        """Most frequent weather condition per city."""
        if "weather_condition" not in self.df.columns:
            return pd.DataFrame()

        report = (
            self.df.groupby(["city", "weather_condition"], as_index=False)
            .agg(occurrences = ("weather_condition", "count"))
            .sort_values(["city", "occurrences"], ascending=[True, False])
        )
        # Keep only the most common condition per city
        most_common = (
            report.groupby("city", as_index=False)
            .first()
            .rename(columns={"weather_condition": "most_common_condition"})
        )
        logger.info("[REPORT] Common weather conditions generated")
        return most_common

    def daily_weather_summary(self) -> pd.DataFrame:
        """
        Per-day summary across all cities.
        Useful for identifying hot days, rainy stretches, etc.
        """
        if "date" not in self.df.columns:
            return pd.DataFrame()

        report = (
            self.df.groupby("date", as_index=False)
            .agg(
                avg_temp_c      = ("temperature_c", "mean"),
                max_temp_c      = ("temperature_c", "max"),
                min_temp_c      = ("temperature_c", "min"),
                avg_humidity    = ("humidity_pct",  "mean"),
                cities_tracked  = ("city",          "nunique"),
                readings        = ("temperature_c", "count"),
            )
            .round(2)
            .sort_values("date", ascending=False)
            .reset_index(drop=True)
        )
        logger.info("[REPORT] Daily weather summary generated")
        return report

    def comfort_distribution(self) -> pd.DataFrame:
        """Count of readings per comfort level — quick quality-of-life view."""
        if "comfort_level" not in self.df.columns:
            return pd.DataFrame()

        report = (
            self.df.groupby(["city", "comfort_level"], as_index=False)
            .agg(count = ("comfort_level", "count"))
            .sort_values(["city", "count"], ascending=[True, False])
            .reset_index(drop=True)
        )
        logger.info("[REPORT] Comfort distribution generated")
        return report

    def heat_index_comparison(self) -> pd.DataFrame:
        """Compare actual temperature vs perceived (heat index) per city."""
        if "heat_index_c" not in self.df.columns:
            return pd.DataFrame()

        report = (
            self.df.groupby("city", as_index=False)
            .agg(
                avg_temp_c       = ("temperature_c", "mean"),
                avg_heat_index_c = ("heat_index_c",  "mean"),
            )
            .round(2)
        )
        report["heat_difference_c"] = (
            report["avg_heat_index_c"] - report["avg_temp_c"]
        ).round(2)
        report = report.sort_values("heat_difference_c", ascending=False)
        logger.info("[REPORT] Heat index comparison generated")
        return report

    # ──────────────────────────────────────────────
    # MAIN EXPORT METHODS
    # ──────────────────────────────────────────────

    def generate_all_reports(self) -> dict[str, pd.DataFrame]:
        """
        Run all report generators and return them as a named dict.

        Returns:
            Dict mapping report name → DataFrame.
        """
        if self.df.empty:
            logger.warning("[REPORT] No data to report on")
            return {}

        reports = {
            "City Temperature Summary":  self.city_temperature_summary(),
            "Humidity Analysis":         self.humidity_analysis(),
            "Wind Speed Analysis":       self.wind_speed_analysis(),
            "Common Weather Conditions": self.common_weather_conditions(),
            "Daily Summary":             self.daily_weather_summary(),
            "Comfort Distribution":      self.comfort_distribution(),
            "Heat Index Comparison":     self.heat_index_comparison(),
        }
        logger.info(f"[REPORT] {len(reports)} reports generated")
        return reports

    def export_to_csv(self, reports: dict[str, pd.DataFrame] | None = None) -> Path:
        """
        Export the main city temperature summary to CSV.

        Returns:
            Path to the saved CSV file.
        """
        reports = reports or self.generate_all_reports()
        main_report = reports.get("City Temperature Summary", pd.DataFrame())

        timestamp = get_timestamp()
        csv_path = config.REPORTS_DIR / f"weather_summary_{timestamp}.csv"
        main_report.to_csv(csv_path, index=False)
        logger.info(f"[REPORT] CSV exported → {csv_path}")
        return csv_path

    def export_to_excel(
        self, reports: dict[str, pd.DataFrame] | None = None
    ) -> Path | None:
        """
        Export all reports to a multi-sheet Excel workbook.

        Each report becomes one worksheet. Sheet names are truncated to
        31 characters (Excel limit).

        Returns:
            Path to the saved Excel file, or None if openpyxl is missing.
        """
        if not EXCEL_AVAILABLE:
            logger.warning("[REPORT] Skipping Excel export — openpyxl not installed")
            return None

        reports = reports or self.generate_all_reports()
        print(reports.keys())
        timestamp = get_timestamp()
        excel_path = config.REPORTS_DIR / f"weather_report_{timestamp}.xlsx"

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            # ── Metadata sheet ──
            meta = pd.DataFrame({
                "Field": ["Generated At", "Total Records", "Cities"],
                "Value": [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    len(self.df),
                    ", ".join(sorted(self.df["city"].dropna().unique())),
                ],
            })
            meta.to_excel(writer, sheet_name="Metadata", index=False)

            # ── Data sheets ──
            for report_name, report_df in reports.items():
                if report_df.empty:
                    continue
                sheet_name = report_name[:31]   # Excel sheet name limit
                report_df.to_excel(writer, sheet_name=sheet_name, index=False)

                # Auto-fit column widths
                ws = writer.sheets[sheet_name]
                for col_idx, col in enumerate(report_df.columns, start=1):
                    max_len = max(
                        len(str(col)),
                        report_df[col].astype(str).str.len().max()
                        if not report_df.empty else 0,
                    )
                    ws.column_dimensions[
                        openpyxl.utils.get_column_letter(col_idx)
                    ].width = min(max_len + 4, 40)

        logger.info(f"[REPORT] Excel workbook exported → {excel_path}")
        return excel_path

    def print_terminal_summary(self, reports: dict[str, pd.DataFrame] | None = None):
        """Print formatted reports to the terminal for quick review."""
        reports = reports or self.generate_all_reports()

        print("\n" + "=" * 65)
        print("  WEATHER ETL PIPELINE — ANALYTICS REPORT")
        print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 65)

        for name, df in reports.items():
            if df.empty:
                continue
            print(f"\n{'─' * 65}")
            print(f"  📊  {name.upper()}")
            print(f"{'─' * 65}")
            print(df.to_string(index=False))

        print("\n" + "=" * 65)
        logger.info("[REPORT] Terminal summary printed")


# ──────────────────────────────────────────────
# STANDALONE TEST
# ──────────────────────────────────────────────
if __name__ == "__main__":

  if __name__ == "__main__":

    from database import get_all_weather

    df = get_all_weather()

    reporter = WeatherReporter(df)

    reporter.print_terminal_summary()

    csv_path = reporter.export_to_csv()

    excel_path = reporter.export_to_excel()

    print(csv_path)
    print(excel_path)