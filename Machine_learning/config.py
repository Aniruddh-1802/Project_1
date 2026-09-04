"""
ML Phase Configuration

Central place for all paths, thresholds, and configuration parameters.
Update these paths to match your actual data locations.

IMPORTANT: All paths should be relative to the project root, not this file.
"""

import os
from pathlib import Path

# ============================================================================
# DATA PATHS - Input & Output Locations
# ============================================================================

# INPUT: Spark/PySpark Processing Output
HOURLY_SUMMARY_PATH = 'data/analytics/hourly_grid_summary/'
# This is the primary input: hourly grid activity summary from Phase 2
# Format: Parquet directory or CSV file
# Expected columns: timestamp, grid_id, sms_in, sms_out, call_in, call_out, internet_activity
# Minimum: 10 days, Recommended: 14+ days

REFERENCE_GEOJSON_PATH = 'data/reference/milano-grid.geojson'
# Static geographic reference (not used in ML, but kept for reference)

# ============================================================================
# ML OUTPUT PATHS - Where Each Module Saves Its Results
# ============================================================================

# ML2 Output: Engineered Features
FEATURES_OUTPUT_PATH = 'data/ml/network_feature_table/'

# ML3 Output: Trained Model
MODEL_OUTPUT_PATH = 'data/ml/model.pkl'
MODEL_METADATA_PATH = 'data/ml/model_metadata.json'

# ML4 Output: Anomaly Scores
ANOMALY_SCORES_PATH = 'data/ml/network_anomaly_scores.parquet'

# ML6 Output: Risk Scores (final product)
RISK_SCORES_OUTPUT_PATH = 'data/ml/network_risk_scores/'

# ============================================================================
# FEATURE ENGINEERING PARAMETERS (ML2)
# ============================================================================

RECENT_WINDOW_HOURS = 24
# Hours to look back for recent features
# Used for: avg_activity, peak_ratio, variability, internet_share
# Recommendation: 24 hours (1 day) for sensitivity to changes

BASELINE_WINDOW_HOURS = 168
# Hours to look back for baseline (historical pattern)
# Used for: activity_growth calculation
# 168 hours = 7 days (captures weekly patterns)
# Recommendation: 7 days minimum, 14 days or more preferred

ACTIVITY_FLOOR = 0.0
# Minimum activity threshold
# Grids below this are treated as "no activity"
# Used to prevent division by zero in feature calculations

# ============================================================================
# LABELING PARAMETERS (ML3)
# ============================================================================

ACTIVITY_PERCENTILE = 75
# Percentile above which activity is labeled HIGH_ACTIVITY
# 75 = top 25% are labeled HIGH (positive class)
# This creates class balance suitable for sklearn

TRAINING_TEST_SPLIT_RATIO = 0.7
# Proportion of data for training (rest for testing)
# 70/30 split is standard
# IMPORTANT: Split is chronological, not random

# ============================================================================
# MODEL PARAMETERS (ML3)
# ============================================================================

MODEL_TYPE = 'logistic'  # Options: 'logistic' or 'tree'
# Logistic Regression: Fast, interpretable, good baseline
# Decision Tree: Also interpretable, non-linear boundaries

# For Logistic Regression:
LOGISTIC_MAX_ITER = 1000
LOGISTIC_RANDOM_STATE = 42
LOGISTIC_CLASS_WEIGHT = 'balanced'  # Handle class imbalance

# For Decision Tree:
TREE_MAX_DEPTH = 5
TREE_MIN_SAMPLES_LEAF = 10
TREE_RANDOM_STATE = 42
TREE_CLASS_WEIGHT = 'balanced'

# ============================================================================
# ANOMALY DETECTION PARAMETERS (ML4)
# ============================================================================

ANOMALY_Z_SCORE_THRESHOLD = 2.0
# Standard deviations from baseline for anomaly flagging
# 2.0 = ~95% of normal variation (alerts on extremes)

ANOMALY_BUCKETING_KEY = 'hour_of_day'
# 'hour_of_day': Baseline for each hour across all days (requires 7+ days)
# 'within_day': Baseline for same day only (works with 1 day)
# Recommendation: 'hour_of_day' once history accumulates

# ============================================================================
# RISK SCORING THRESHOLDS (ML5 & ML6)
# ============================================================================

RISK_LEVEL_HIGH = 0.7
# risk_score >= 0.7 → risk_level = HIGH

RISK_LEVEL_ATTENTION = 0.4
# 0.4 <= risk_score < 0.7 → risk_level = ATTENTION

# risk_score < 0.4 → risk_level = NORMAL

# ============================================================================
# BATCH SCORING PARAMETERS (ML6)
# ============================================================================

TOP_ATTENTION_N = 20
# Number of grids to include in top-attention report
# Used by generate_top_attention_report() in batch_score.py

# Weighting for combined attention score:
ATTENTION_ML_WEIGHT = 0.6
# 60% from ML risk_score
ATTENTION_ANOMALY_WEIGHT = 0.4
# 40% from anomaly_score

# ============================================================================
# LOGGING & DEBUGGING
# ============================================================================

LOG_LEVEL = 'INFO'
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

LOG_FILE_PATH = 'logs/ml_phase.log'
# Where to save detailed logs

SAVE_INTERMEDIATE_RESULTS = True
# Save intermediate DataFrames (features, etc.) for debugging
# Set to False in production to save disk space

# ============================================================================
# FEATURE COLUMN NAMES (DO NOT MODIFY)
# ============================================================================

FEATURE_COLUMNS = [
    'avg_activity',
    'activity_growth',
    'active_hours',
    'peak_ratio',
    'variability',
    'internet_share'
]
# These MUST match exactly in ML2, ML3, ML5 and batch_score.py
# If changed, update in all modules

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def ensure_output_directories():
    """Create all output directories if they don't exist."""
    paths = [
        FEATURES_OUTPUT_PATH,
        os.path.dirname(MODEL_OUTPUT_PATH),
        os.path.dirname(ANOMALY_SCORES_PATH),
        RISK_SCORES_OUTPUT_PATH,
        os.path.dirname(LOG_FILE_PATH)
    ]
    
    for path in paths:
        if path:
            os.makedirs(path, exist_ok=True)


def get_config_summary():
    """Return a human-readable summary of all config parameters."""
    summary = f"""
ML Phase Configuration Summary
==============================

INPUTS:
  Hourly Summary: {HOURLY_SUMMARY_PATH}
  Reference GeoJSON: {REFERENCE_GEOJSON_PATH}

OUTPUTS:
  Features: {FEATURES_OUTPUT_PATH}
  Model: {MODEL_OUTPUT_PATH}
  Anomalies: {ANOMALY_SCORES_PATH}
  Risk Scores: {RISK_SCORES_OUTPUT_PATH}

FEATURE ENGINEERING:
  Recent Window: {RECENT_WINDOW_HOURS}h
  Baseline Window: {BASELINE_WINDOW_HOURS}h

LABELING:
  Activity Percentile: {ACTIVITY_PERCENTILE}%
  Test Split: {(1-TRAINING_TEST_SPLIT_RATIO)*100:.0f}%

MODEL:
  Type: {MODEL_TYPE}

ANOMALY:
  Bucketing: {ANOMALY_BUCKETING_KEY}
  Z-score Threshold: {ANOMALY_Z_SCORE_THRESHOLD}

RISK THRESHOLDS:
  HIGH: >= {RISK_LEVEL_HIGH}
  ATTENTION: >= {RISK_LEVEL_ATTENTION}
  NORMAL: < {RISK_LEVEL_ATTENTION}
"""
    return summary


if __name__ == '__main__':
    # Print config when run directly
    print(get_config_summary())
    ensure_output_directories()
    print("Configuration validated and directories created.")
