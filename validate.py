"""
src/validate.py
---------------
DATA VALIDATION LAYER — Step 3 of the ETL Pipeline.

Responsibilities:
    1. Check for null/missing values in critical columns.
    2. Validate temperature, humidity, and pressure are within realistic ranges.
    3. Detect duplicate records.
    4. Log every validation failure with details.
    5. Produce a structured validation summary report.
    6. Return only clean records to the loader.

Senior Engineer Note:
    Data quality is a contract. You must validate BEFORE loading into your
    database. Garbage-in-garbage-out is a real problem in production.
    Validation should be strict enough to catch real problems but lenient
    enough not to reject valid edge-case data.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from utils import get_logger, get_timestamp, save_json

logger = get_logger(__name__)


class WeatherValidator:
    """
    Validates a transformed weather DataFrame and returns clean records.

    The validator runs a series of checks. Records failing CRITICAL checks
    are quarantined (excluded from loading). Records with non-critical issues
    are flagged in the summary but still passed through.
    """

    def validate(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        """
        Run all validation checks on the DataFrame.

        Args:
            df: Transformed weather DataFrame from WeatherTransformer.

        Returns:
            Tuple of:
                - clean_df   : DataFrame with invalid rows removed.
                - summary    : Dict containing full validation report.
        """
        if df.empty:
            logger.warning("[VALIDATE] Received empty DataFrame — skipping validation")
            return df, {"status": "SKIPPED", "reason": "Empty DataFrame"}

        logger.info(f"[VALIDATE] Starting validation on {len(df)} records")

        validation_issues = []
        original_count = len(df)

        # Track which rows should be dropped (critical failures)
        rows_to_drop = set()

        # ── CHECK 1: Null values in critical columns ──
        critical_columns = [
            "city", "temperature_c", "humidity_pct",
            "pressure_hpa", "weather_condition", "recorded_at",
        ]
        null_issues = self._check_nulls(df, critical_columns, rows_to_drop)
        validation_issues.extend(null_issues)

        # ── CHECK 2: Temperature range ──
        temp_issues = self._check_range(
            df, "temperature_c",
            config.TEMP_MIN, config.TEMP_MAX,
            rows_to_drop, critical=True,
        )
        validation_issues.extend(temp_issues)

        # ── CHECK 3: Humidity range ──
        hum_issues = self._check_range(
            df, "humidity_pct",
            config.HUMIDITY_MIN, config.HUMIDITY_MAX,
            rows_to_drop, critical=True,
        )
        validation_issues.extend(hum_issues)

        # ── CHECK 4: Pressure range ──
        pres_issues = self._check_range(
            df, "pressure_hpa",
            config.PRESSURE_MIN, config.PRESSURE_MAX,
            rows_to_drop, critical=False,   # Flag but don't drop
        )
        validation_issues.extend(pres_issues)

        # ── CHECK 5: Duplicate records (same city + recorded_at) ──
        dup_issues, dup_indices = self._check_duplicates(df)
        validation_issues.extend(dup_issues)
        rows_to_drop.update(dup_indices)

        # ── CHECK 6: City name sanity ──
        city_issues = self._check_city_names(df)
        validation_issues.extend(city_issues)

        # ── Drop invalid rows ──
        clean_df = df.drop(index=list(rows_to_drop)).reset_index(drop=True)
        dropped_count = original_count - len(clean_df)

        # ── Build summary report ──
        summary = self._build_summary(
            original_count=original_count,
            clean_count=len(clean_df),
            dropped_count=dropped_count,
            issues=validation_issues,
            clean_df=clean_df,
        )

        # ── Save validation report ──
        timestamp = get_timestamp()
        report_path = config.PROCESSED_DIR / f"validation_report_{timestamp}.json"
        save_json(summary, report_path)
        logger.info(f"[VALIDATE] Validation report saved → {report_path}")

        # ── Log overall result ──
        status = "PASSED" if dropped_count == 0 else "PARTIAL"
        logger.info(
            f"[VALIDATE] {status} — "
            f"Original: {original_count}, "
            f"Clean: {len(clean_df)}, "
            f"Dropped: {dropped_count}, "
            f"Issues found: {len(validation_issues)}"
        )
        if dropped_count > 0:
            logger.warning(
                f"[VALIDATE] {dropped_count} records dropped due to critical failures"
            )

        return clean_df, summary

    # ──────────────────────────────────────────────
    # PRIVATE CHECK METHODS
    # ──────────────────────────────────────────────

    def _check_nulls(
        self,
        df: pd.DataFrame,
        columns: list[str],
        rows_to_drop: set,
    ) -> list[dict]:
        """Flag rows with null values in critical columns."""
        issues = []
        for col in columns:
            if col not in df.columns:
                continue
            null_mask = df[col].isna()
            null_indices = df[null_mask].index.tolist()
            if null_indices:
                rows_to_drop.update(null_indices)
                issue = {
                    "check":    "NULL_VALUE",
                    "column":   col,
                    "severity": "CRITICAL",
                    "affected_rows": len(null_indices),
                    "row_indices": null_indices,
                    "message":  f"NULL found in required column '{col}'",
                }
                issues.append(issue)
                logger.warning(
                    f"[VALIDATE] NULL in '{col}': "
                    f"{len(null_indices)} row(s) at indices {null_indices}"
                )
        return issues

    def _check_range(
        self,
        df: pd.DataFrame,
        column: str,
        min_val: float,
        max_val: float,
        rows_to_drop: set,
        critical: bool = True,
    ) -> list[dict]:
        """Flag rows where a numeric column falls outside a valid range."""
        issues = []
        if column not in df.columns:
            return issues

        col_data = pd.to_numeric(df[column], errors="coerce")
        out_of_range = df[(col_data < min_val) | (col_data > max_val)]

        if not out_of_range.empty:
            severity = "CRITICAL" if critical else "WARNING"
            if critical:
                rows_to_drop.update(out_of_range.index.tolist())

            issue = {
                "check":    "RANGE_VIOLATION",
                "column":   column,
                "severity": severity,
                "valid_range": [min_val, max_val],
                "affected_rows": len(out_of_range),
                "row_indices": out_of_range.index.tolist(),
                "offending_values": col_data[out_of_range.index].tolist(),
                "message": (
                    f"'{column}' out of range [{min_val}, {max_val}]"
                ),
            }
            issues.append(issue)
            logger.warning(
                f"[VALIDATE] Range violation in '{column}' "
                f"({severity}): {len(out_of_range)} row(s)"
            )
        return issues

    def _check_duplicates(
        self, df: pd.DataFrame
    ) -> tuple[list[dict], list[int]]:
        """Detect duplicate rows based on city + recorded_at."""
        issues = []
        dup_indices = []

        subset = [c for c in ["city", "recorded_at"] if c in df.columns]
        if not subset:
            return issues, dup_indices

        dup_mask = df.duplicated(subset=subset, keep="first")
        dups = df[dup_mask]

        if not dups.empty:
            dup_indices = dups.index.tolist()
            issue = {
                "check":    "DUPLICATE_RECORD",
                "severity": "CRITICAL",
                "subset":   subset,
                "affected_rows": len(dups),
                "row_indices": dup_indices,
                "message":  (
                    f"Duplicate records found on {subset}. "
                    f"Keeping first occurrence."
                ),
            }
            issues.append(issue)
            logger.warning(
                f"[VALIDATE] {len(dups)} duplicate row(s) detected and removed"
            )
        return issues, dup_indices

    def _check_city_names(self, df: pd.DataFrame) -> list[dict]:
        """Non-critical: warn if a city name is suspiciously short."""
        issues = []
        if "city" not in df.columns:
            return issues

        short_names = df[df["city"].str.len() < 2]
        if not short_names.empty:
            issue = {
                "check":    "SUSPICIOUS_CITY_NAME",
                "severity": "WARNING",
                "affected_rows": len(short_names),
                "values": short_names["city"].tolist(),
                "message": "City names with < 2 characters found",
            }
            issues.append(issue)
            logger.warning(f"[VALIDATE] Suspicious city names: {short_names['city'].tolist()}")
        return issues

    def _build_summary(
        self,
        original_count: int,
        clean_count: int,
        dropped_count: int,
        issues: list[dict],
        clean_df: pd.DataFrame,
    ) -> dict:
        """Assemble the full validation summary dict."""
        critical_issues = [i for i in issues if i.get("severity") == "CRITICAL"]
        warning_issues  = [i for i in issues if i.get("severity") == "WARNING"]

        # Per-column null summary (good to have in any data quality report)
        null_summary = {}
        for col in clean_df.columns:
            null_count = int(clean_df[col].isna().sum())
            if null_count > 0:
                null_summary[col] = null_count

        return {
            "validation_timestamp": datetime.utcnow().isoformat(),
            "original_record_count":  original_count,
            "clean_record_count":     clean_count,
            "dropped_record_count":   dropped_count,
            "pass_rate_pct": round(clean_count / original_count * 100, 1) if original_count else 0,
            "total_issues":   len(issues),
            "critical_issues": len(critical_issues),
            "warning_issues":  len(warning_issues),
            "null_counts_in_clean_data": null_summary,
            "issues_detail": issues,
        }


# ──────────────────────────────────────────────
# STANDALONE TEST
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import json

    # Create a test DataFrame with one bad row
    test_data = {
        "city":              ["Kolkata", "Delhi", "BadCity"],
        "temperature_c":     [34.2,      38.1,    999.9],    # 999.9 is invalid
        "humidity_pct":      [78,        55,       60],
        "pressure_hpa":      [1005,      1010,     1008],
        "weather_condition": ["Clouds",  "Clear",  "Haze"],
        "recorded_at":       ["2024-09-15 14:30:00"] * 3,
    }
    test_df = pd.DataFrame(test_data)

    validator = WeatherValidator()
    clean_df, summary = validator.validate(test_df)

    print("\nClean DataFrame:")
    print(clean_df)
    print("\nValidation Summary:")
    print(json.dumps(summary, indent=2, default=str))
