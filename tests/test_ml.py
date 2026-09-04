"""
ML2 feature-leakage regression test (guards the t / t+1 boundary described
in Machine_learning/features.py and enforced by the C10 post-edit hook).

Uses a small, fully synthetic hourly activity series - no files under
data/ are read here. It asserts that avg_activity computed at hour t is
unaffected by what happens at hour t+1, i.e. that engineer_features()
never looks past its own feature_timestamp.
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Machine_learning.features import NetworkActivityFeatures  # noqa: E402


def _synthetic_hourly_frame(spike_at_t_plus_1: float) -> pd.DataFrame:
    """48 hours of flat activity=100 for grid 1, then a controllable spike
    at the 25th hour (which sits one hour after our feature_timestamp of
    interest, hour index 23)."""
    hours = pd.date_range("2013-11-01 00:00", periods=48, freq="h")
    total_activity = [100.0] * 48
    total_activity[24] = spike_at_t_plus_1  # this is t+1 relative to hour[23]

    return pd.DataFrame(
        {
            "grid_id": 1,
            "timestamp": hours,
            "sms_in": [0.0] * 48,
            "sms_out": [0.0] * 48,
            "call_in": [0.0] * 48,
            "call_out": [0.0] * 48,
            "internet_activity": total_activity,
            "total_sms": [0.0] * 48,
            "total_calls": [0.0] * 48,
            "total_activity": total_activity,
        }
    )


def _features_at(df: pd.DataFrame, feature_timestamp: pd.Timestamp) -> dict:
    fe = NetworkActivityFeatures()
    fe.df = df.sort_values(["grid_id", "timestamp"]).reset_index(drop=True)
    features_df = fe.engineer_features()
    row = features_df[features_df["feature_timestamp"] == feature_timestamp]
    assert len(row) == 1, "expected exactly one feature row at this timestamp"
    return row.iloc[0].to_dict()


def test_no_leakage():
    baseline_df = _synthetic_hourly_frame(spike_at_t_plus_1=100.0)
    leaked_df = _synthetic_hourly_frame(spike_at_t_plus_1=100_000.0)

    t = baseline_df.loc[23, "timestamp"]  # feature_timestamp under test

    baseline_features = _features_at(baseline_df, t)
    leaked_features = _features_at(leaked_df, t)

    # A massive change at t+1 must not move any feature computed for t.
    assert baseline_features["avg_activity"] == leaked_features["avg_activity"], (
        "avg_activity at feature_timestamp t changed when only t+1 "
        "changed - a feature is reading data from the wrong side of the "
        "time boundary (Machine_learning/features.py engineer_features)."
    )
    assert baseline_features["peak_ratio"] == leaked_features["peak_ratio"]
    assert baseline_features["variability"] == leaked_features["variability"]
