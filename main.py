"""
main.py
-------
PIPELINE ORCHESTRATOR — Entry point for the Weather ETL Pipeline.

Run this file to execute the complete pipeline:
    python main.py

Execution flow:
    1. EXTRACT  — Fetch weather data from OpenWeatherMap API
    2. TRANSFORM — Parse, clean, and enrich the raw data
    3. VALIDATE  — Check data quality and remove invalid records
    4. LOAD      — Insert clean data into MySQL database
    5. REPORT    — Generate analytics and export to CSV/Excel

Senior Engineer Note:
    The orchestrator should be thin — it just calls each stage in order
    and passes outputs between them. Error handling here is top-level;
    each stage handles its own internal errors.
    This pattern is called an "ETL Pipeline" or "DAG" (Directed Acyclic Graph)
    in tools like Apache Airflow.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to Python path so all imports work correctly
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from utils import get_logger, print_section, timing_decorator
from extract import WeatherExtractor
from transform import WeatherTransformer
from validate import WeatherValidator
from load import WeatherLoader
from report import WeatherReporter
logger = get_logger("main")


@timing_decorator
def run_pipeline() -> dict:
    """
    Execute all five stages of the ETL pipeline in sequence.

    Returns:
        Summary dict with statistics from each stage.
    """
    pipeline_start = time.perf_counter()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"{'='*60}")
    logger.info(f"WEATHER ETL PIPELINE STARTED — Run ID: {run_id}")
    logger.info(f"{'='*60}")

    summary = {
        "run_id":    run_id,
        "started_at": datetime.now().isoformat(),
        "stages":    {},
        "status":    "RUNNING",
    }

    extractor  = None
    loader     = None

    try:
        # ══════════════════════════════════════════════
        # STAGE 1: EXTRACT
        # ══════════════════════════════════════════════
        print_section("STAGE 1/5 — EXTRACT")
        logger.info("[MAIN] Starting extraction stage")

        extractor = WeatherExtractor()
        raw_records = extractor.fetch_all_cities()

        summary["stages"]["extract"] = {
            "cities_attempted": len(config.CITIES),
            "records_fetched":  len(raw_records),
            "status": "SUCCESS" if raw_records else "FAILED",
        }

        if not raw_records:
            logger.error(
                "[MAIN] Extraction returned no data. "
                "Check your API key and internet connection. Aborting."
            )
            summary["status"] = "FAILED"
            return summary

        logger.info(f"[MAIN] Extraction complete: {len(raw_records)} records fetched")

        # ══════════════════════════════════════════════
        # STAGE 2: TRANSFORM
        # ══════════════════════════════════════════════
        print_section("STAGE 2/5 — TRANSFORM")
        logger.info("[MAIN] Starting transformation stage")

        transformer = WeatherTransformer()
        transformed_df = transformer.transform(raw_records)

        summary["stages"]["transform"] = {
            "records_in":  len(raw_records),
            "records_out": len(transformed_df),
            "columns":     list(transformed_df.columns),
            "status": "SUCCESS" if not transformed_df.empty else "FAILED",
        }

        if transformed_df.empty:
            logger.error("[MAIN] Transformation produced empty DataFrame. Aborting.")
            summary["status"] = "FAILED"
            return summary

        logger.info(
            f"[MAIN] Transformation complete: "
            f"{len(transformed_df)} rows × {len(transformed_df.columns)} columns"
        )

        # ══════════════════════════════════════════════
        # STAGE 3: VALIDATE
        # ══════════════════════════════════════════════
        print_section("STAGE 3/5 — VALIDATE")
        logger.info("[MAIN] Starting validation stage")

        validator = WeatherValidator()
        clean_df, validation_summary = validator.validate(transformed_df)

        summary["stages"]["validate"] = {
            "records_in":     len(transformed_df),
            "records_clean":  len(clean_df),
            "records_dropped": validation_summary.get("dropped_record_count", 0),
            "pass_rate_pct":  validation_summary.get("pass_rate_pct", 0),
            "critical_issues": validation_summary.get("critical_issues", 0),
            "status": "SUCCESS" if not clean_df.empty else "FAILED",
        }

        if clean_df.empty:
            logger.error(
                "[MAIN] All records failed validation. "
                "Check validation report in data/processed/. Aborting."
            )
            summary["status"] = "FAILED"
            return summary

        logger.info(
            f"[MAIN] Validation complete: "
            f"{len(clean_df)}/{len(transformed_df)} records passed "
            f"({validation_summary.get('pass_rate_pct', 0):.1f}%)"
        )

        # ══════════════════════════════════════════════
        # STAGE 4: LOAD
        # ══════════════════════════════════════════════
        print_section("STAGE 4/5 — LOAD")
        logger.info("[MAIN] Starting database load stage")

        try:
            loader = WeatherLoader()
            load_stats = loader.load(clean_df)

            summary["stages"]["load"] = {
                **load_stats,
                "status": "SUCCESS",
            }
            logger.info(
                f"[MAIN] Load complete: "
                f"{load_stats['inserted']} inserted, "
                f"{load_stats['skipped']} skipped, "
                f"{load_stats['failed']} failed"
            )

        except Exception as db_err:
            logger.warning(
                f"[MAIN] Database load failed: {db_err}\n"
                "Continuing to reporting stage using in-memory data."
            )
            loader = None
            summary["stages"]["load"] = {
                "status": "FAILED",
                "error": str(db_err),
                "note": "Reporting will use in-memory data",
            }

        # ══════════════════════════════════════════════
        # STAGE 5: REPORT
        # ══════════════════════════════════════════════
        print_section("STAGE 5/5 — REPORT")
        logger.info("[MAIN] Starting reporting stage")

        # Use database data if available, otherwise use in-memory clean data
        if loader:
            report_df = loader.fetch_all()
            if report_df.empty:
                logger.info(
                    "[MAIN] Database returned no rows yet — using in-memory data"
                )
                report_df = clean_df
        else:
            report_df = clean_df

        reporter = WeatherReporter(report_df)
        reports  = reporter.generate_all_reports()

        reporter.print_terminal_summary(reports)

        csv_path   = reporter.export_to_csv(reports)
        excel_path = reporter.export_to_excel(reports)

        summary["stages"]["report"] = {
            "reports_generated": len(reports),
            "csv_path":   str(csv_path),
            "excel_path": str(excel_path) if excel_path else "Not generated",
            "status": "SUCCESS",
        }

        # ══════════════════════════════════════════════
        # PIPELINE COMPLETE
        # ══════════════════════════════════════════════
        elapsed = time.perf_counter() - pipeline_start
        summary["status"]     = "SUCCESS"
        summary["elapsed_s"]  = round(elapsed, 2)
        summary["finished_at"] = datetime.now().isoformat()

        print_section("PIPELINE COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"PIPELINE SUCCEEDED in {elapsed:.2f}s — Run ID: {run_id}")
        logger.info(f"  Reports saved to : {config.REPORTS_DIR}")
        logger.info(f"  Logs saved to    : {config.LOG_FILE}")
        logger.info(f"{'='*60}")

    except KeyboardInterrupt:
        logger.warning("[MAIN] Pipeline interrupted by user (Ctrl+C)")
        summary["status"] = "INTERRUPTED"

    except Exception as exc:
        logger.exception(f"[MAIN] Unhandled pipeline error: {exc}")
        summary["status"] = "ERROR"
        summary["error"]  = str(exc)

    finally:
        # Always clean up resources
        if extractor:
            extractor.close()
        if loader:
            loader.dispose()

    return summary


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════╗
║       REAL-TIME WEATHER DATA ETL PIPELINE           ║
║       Built with Python · Pandas · MySQL            ║
╚══════════════════════════════════════════════════════╝
    """)

    result = run_pipeline()

    # Exit with non-zero code on failure (important for CI/CD systems)
    if result.get("status") not in ("SUCCESS",):
        sys.exit(1)
