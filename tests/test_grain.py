"""
Canonical grain check (Core Dataset Contract rule 2 / SP3 / DE8 / C7
"/network-health" / C10 post-edit hook).

The single most valuable test in the project: a duplicate on
(grid_id, timestamp) in the grid/hour analytics layer means the
country-code aggregation was missed or partially applied, and every KPI,
feature, model score and API response downstream is then inflated.

This test reads data/analytics/hourly_grid_summary (Parquet) and asserts
zero duplicates on (grid_id, timestamp). It is skipped, not failed, if
that output has not been produced yet in this environment.
"""

from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOURLY_SUMMARY_PATH = PROJECT_ROOT / "data" / "analytics" / "hourly_grid_summary"


def _load_hourly_summary() -> pd.DataFrame:
    if not HOURLY_SUMMARY_PATH.exists():
        pytest.skip(
            f"{HOURLY_SUMMARY_PATH} does not exist yet - run the Spark "
            "pipeline (spark/telecom_pipeline.py) before this check applies."
        )
    return pd.read_parquet(HOURLY_SUMMARY_PATH)


def test_no_duplicates_on_grid_and_timestamp():
    df = _load_hourly_summary()

    required = {"grid_id", "timestamp"}
    missing = required - set(df.columns)
    assert not missing, f"hourly_grid_summary is missing columns: {missing}"

    duplicate_mask = df.duplicated(subset=["grid_id", "timestamp"], keep=False)
    duplicate_count = int(duplicate_mask.sum())

    assert duplicate_count == 0, (
        f"{duplicate_count} duplicate (grid_id, timestamp) rows found in "
        "hourly_grid_summary - the country-code aggregation was missed or "
        "partially applied upstream (spark/spark_aggregation.py)."
    )


def test_every_grid_id_within_milan_range():
    df = _load_hourly_summary()
    assert df["grid_id"].between(1, 10000).all(), (
        "hourly_grid_summary contains grid_id values outside 1-10000 - "
        "check for a Trentino-file contamination (sms-call-internet-*.csv "
        "instead of sms-call-internet-mi-*.csv)."
    )
