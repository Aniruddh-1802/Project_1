# Network Operations ML Phase (ML1-ML6)

Complete implementation of the Machine Learning layer for the Network Operations & Predictive Intelligence system.

## Overview

This folder contains all code for phases ML1 through ML6:
- **ML1**: Problem definition (non-executable, see `ML1_PROBLEM_STATEMENT.md`)
- **ML2**: Feature engineering (`features.py`)
- **ML3**: Train simple classifier (`train.py`)
- **ML4**: Anomaly baseline detection (`anomaly.py`)
- **ML5**: Model inference / operationalization (`predict.py`)
- **ML6**: Batch scoring for production (`batch_score.py`)

## File Structure

```
ml_phase/
├── README_ML_PHASE.md                    # This file
├── requirements.txt                      # Python dependencies
├── ML1_PROBLEM_STATEMENT.md              # Problem framing (non-executable)
├── features.py                           # ML2: Feature engineering
├── train.py                              # ML3: Train classifier
├── anomaly.py                            # ML4: Anomaly detection
├── predict.py                            # ML5: Model inference
└── batch_score.py                        # ML6: Batch scoring
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Ensure Input Data Exists

The ML phase requires outputs from earlier phases (Spark/PySpark processing).
You need to have:
- `data/analytics/hourly_grid_summary/` (Parquet or CSV)
  - From Phase 2 (PySpark) output
  - Columns: timestamp, grid_id, sms_in, sms_out, call_in, call_out, internet_activity
  - Minimum: 10 days of hourly data (14 days recommended)

- `data/reference/milano-grid.geojson` (for future visualization)

## Execution Guide

### ML2: Engineer Features

```bash
python features.py
```

**What it does:**
- Loads hourly_grid_summary from Parquet/CSV
- Computes 6 engineered features for each grid/timestamp:
  - `avg_activity`: Mean activity in trailing 24h window
  - `activity_growth`: Recent window vs baseline window
  - `active_hours`: Count of hours with activity > 0
  - `peak_ratio`: Peak / mean activity ratio
  - `variability`: Standard deviation of activity
  - `internet_share`: Internet activity as proportion of total
- Enforces strict t/t+1 boundary (features from t, no data from t+1)
- Saves to: `data/ml/network_feature_table/features.parquet`

**Configuration in `features.py`:**
- `RECENT_WINDOW_HOURS = 24` (lookback for features)
- `BASELINE_WINDOW_HOURS = 168` (7 days for baseline)

### ML3: Train Simple Classifier

```bash
python train.py
```

**What it does:**
- Loads features from ML2
- Creates HIGH_ACTIVITY labels from hourly_grid_summary
- Performs chronological train/test split (70/30)
  - Train: Earlier days
  - Test: Later days
  - NO random shuffling (maintains time-series integrity)
- Trains Logistic Regression or Decision Tree
- Reports:
  - Accuracy, Precision, Recall
  - Base rate (% of positive class)
  - Feature coefficients / importances
- Saves model to: `data/ml/model.pkl`

**Configuration in `train.py`:**
- `ACTIVITY_PERCENTILE = 75` (threshold: top 25% activity = HIGH)
- Model type: Logistic Regression (default) or Decision Tree

**Important Notes:**
- Accuracy should NOT exceed ~95% - if it does, check for data leakage
- Base rate matters as much as accuracy (expect ~25% positive)
- Report shows confusion matrix and feature importance

### ML4: Add Anomaly Baseline

```bash
python anomaly.py
```

**What it does:**
- Loads hourly_grid_summary
- For each grid and hour-of-day bucket:
  - Computes median baseline activity
  - Compares current activity against baseline
  - Flags HIGH (above baseline) or LOW (below 50% of baseline)
- Optionally compares with:
  - NP3 rule-based alerts
  - ML3 classifier predictions
- Saves to: `data/ml/network_anomaly_scores.parquet`

**Why ML4 works (but NP3 didn't):**
- NP3 had only 1 day → per-hour-of-day buckets have 1 observation → baseline = current value
- ML4 has 14+ days → each hour-of-day bucket has 14 observations → meaningful baseline

### ML5: Model Inference

```bash
python predict.py
```

**What it does:**
- Loads trained model from ML3
- Validates feature inputs
- Runs single-sample and batch inference
- Returns:
  - `risk_score`: 0.0-1.0 probability
  - `risk_level`: NORMAL / ATTENTION / HIGH
  - `model_version`: For tracking
- Can be called by FastAPI endpoint (see api/routers/prediction.py)

**Usage in code:**
```python
from predict import NetworkRiskPredictor, PredictionRequest

predictor = NetworkRiskPredictor(model_path='data/ml/model.pkl')

request = PredictionRequest(
    grid_id=4821,
    feature_timestamp='2013-11-05T14:00:00',
    avg_activity=150.0,
    activity_growth=0.2,
    active_hours=18,
    peak_ratio=2.5,
    variability=45.0,
    internet_share=0.65
)

response = predictor.predict_single(request)
print(f"Risk: {response.risk_level} (score: {response.risk_score})")
```

### ML6: Batch Scoring

```bash
python batch_score.py
```

**What it does:**
- Loads engineered features from ML2
- Loads trained model from ML3
- Loads anomaly scores from ML4
- Runs inference on ALL grid/timestamp combinations
- Generates top-20 grids requiring operational attention
- Saves risk scores to: `data/ml/network_risk_scores/`

**Suitable for Airflow integration:**
```python
# In Airflow DAG:
from ml.batch_score import run_batch_scoring

task = PythonOperator(
    task_id='ml_batch_score',
    python_callable=run_batch_scoring,
    op_kwargs={
        'features_path': 'data/ml/network_feature_table/',
        'model_path': 'data/ml/model.pkl',
        'anomaly_path': 'data/ml/network_anomaly_scores.parquet',
        'output_path': 'data/ml/network_risk_scores/'
    }
)
```

## Data Flow

```
Spark/PySpark Outputs (Phase 2)
    ↓
hourly_grid_summary Parquet
    ↓
ML2: Engineer Features
    ↓
network_feature_table Parquet
    ↓ (+ hourly_grid_summary)
ML3: Train Classifier
    ↓
model.pkl + evaluation metrics
    ↓
ML5: Operationalize (ready for API)
    ↓
ML4: Anomaly Baseline (parallel path)
    ↓
network_anomaly_scores Parquet
    ↓
ML6: Batch Score All Grids
    ↓
network_risk_scores Parquet + top-20 report
```

## Critical Time Boundaries (Enforce Always!)

### The t / t+1 Rule

Features for predicting interval **t+1** MUST use ONLY data from the trailing window ending at **t**.

```
t-7         t-1     t     t+1
|-----------|-------|-----|------ (prediction target)
<-- feature window -->
```

- `avg_activity`: Computed from [t-24h, t]
- `activity_growth`: Baseline from [t-168h, t-24h), recent from [t-24h, t]
- Label for training: Does grid have HIGH_ACTIVITY at t+1? (computed from t+1 data)

### Leakage Prevention

If `avg_activity` includes data from t+1:
- Model accuracy will be artificially inflated (~99%)
- This is a CIRCULAR label (features predict themselves)
- The leakage test in `features.py` will catch this

## Validation Checks

Each module includes validation:

1. **features.py**: Leakage test
   ```python
   fe.validate_no_leakage(features_df)
   # Should FAIL if features read from t+1
   ```

2. **train.py**: Chronological split validation
   ```
   Train period: 2013-10-01 to 2013-10-28
   Test period:  2013-10-29 to 2013-11-05
   (No overlap, proper time ordering)
   ```

3. **anomaly.py**: Direction consistency
   - HIGH: current > baseline
   - LOW: current < 50% of baseline
   - NORMAL: otherwise

4. **batch_score.py**: Score integrity
   ```python
   scorer.validate_scores()
   # Checks: No NaN, 0.0-1.0 range, no duplicates
   ```

## Important Notes on ML Problem

### What This IS:
- **Prediction of UNUSUAL ACTIVITY**: Based on recent grid activity patterns
- **OPERATIONAL ATTENTION SIGNAL**: "This grid needs investigation"
- **TIME-AWARE LEARNING**: Chronological split respects time-series structure
- **INTERPRETABLE**: Simple models with feature importance

### What This IS NOT:
- **Network Congestion Detection**: We have NO capacity/throughput/latency data
- **Customer Impact Prediction**: This is not a churn or SLA problem
- **Real-time Prediction**: This is batch/hourly, not real-time stream
- **Black-box Deep Learning**: We use explainable linear models

### Terminology Discipline:
- ✅ "High-activity risk", "Unusual activity", "Operational attention"
- ❌ "Congestion", "Network fault", "Traffic jam", "Bottleneck"

These words are checked:
- In docstrings
- In log messages
- In API responses (see `api/`)
- In dashboard labels (see React code)

## Example: Complete ML Pipeline Run

```bash
# 1. Feature engineering
python features.py
# Output: data/ml/network_feature_table/features.parquet

# 2. Train model
python train.py
# Outputs:
#   - data/ml/model.pkl
#   - Console: Accuracy, Precision, Recall, Feature importance

# 3. Anomaly detection (parallel)
python anomaly.py
# Output: data/ml/network_anomaly_scores.parquet

# 4. Model inference check
python predict.py
# Output: Example prediction

# 5. Batch scoring (for production)
python batch_score.py
# Outputs:
#   - data/ml/network_risk_scores/risk_scores.parquet
#   - Console: Top-20 grids by attention score
```

## Debugging

### Feature engineering fails
- Check: Is `data/analytics/hourly_grid_summary/` present?
- Check: Does it have required columns: timestamp, grid_id, sms_in, sms_out, call_in, call_out, internet_activity?
- Check: Is timestamp in datetime format?

### Model training shows ~99% accuracy
- **RED FLAG**: Data leakage
- Check: Are features including data from t+1?
- Check: Is label computed from the same window as features?
- Reread ML1_PROBLEM_STATEMENT.md section "The t / t+1 Rule"

### Batch scoring fails on missing model
- Check: Has ML3 (train.py) been run?
- Check: Is `data/ml/model.pkl` present?
- Check: Is pickle module available?

### Anomaly scores don't match rules
- This is **expected and informative**
- NP3 uses within-day baseline (limited visibility)
- ML4 uses hour-of-day baseline (14 days of history)
- Disagreement highlights where additional history helps

## Next Steps: Integration with API & Dashboard

After completing ML1-ML6:

1. **API Integration (ML5)**: 
   - `api/routers/prediction.py` calls `predict.NetworkRiskPredictor`
   - `POST /network/predict-risk` endpoint

2. **API Data Sources (API6)**:
   - `/network/hotspots` surfaces ML risk scores (additive to rules)
   - Database stores `network_risk_scores` table

3. **Dashboard Integration (RE5)**:
   - React Predictive Risk page displays model output
   - Separate model output from Claude explanation

4. **Airflow Integration (ML6)**:
   - `airflow/network_pipeline_dag.py` includes batch scoring task
   - Runs after feature generation, before quality check

5. **Claude Tools (Phase 7)**:
   - Claude can call API endpoints to retrieve risk/anomaly scores
   - Uses scores as evidence for investigations

## References

- **Trainer Guide**: Phase 6 — Machine Learning (main project guide)
- **Problem Definition**: `ML1_PROBLEM_STATEMENT.md` (this folder)
- **Data Contract**: Core Dataset Contract (main guide, Architecture section)
- **API Contracts**: `api/routers/prediction.py` (API layer)
- **Warehouse Schema**: `de/warehouse_model.sql` (Data Engineering)

---

**Last Updated**: 2024
**ML Phase Version**: 1.0
**Requires**: Spark Phase (SP1-SP7) and Data Engineering Phase (DE1-DE8) outputs
