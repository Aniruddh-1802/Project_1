# ML Phase Complete File Index

## 📦 What's Included

Complete, ready-to-run implementation of ML phases 1-6 for the Network Operations & Predictive Intelligence project.

**Total Files:** 13 (8 Python modules + 5 documentation/config files)

---

## 🎯 Start Here

### For First-Time Users
1. Read: `QUICKSTART.md` (5 min)
2. Read: `ML1_PROBLEM_STATEMENT.md` (understand the problem)
3. Edit: `config.py` (update paths to your data)
4. Run: `python run_all.py` (execute the pipeline)

### For Learning
1. Read: `README_ML_PHASE.md` (complete documentation)
2. Read: Individual module docstrings
3. Follow the execution order: ML2 → ML3 → ML4 → ML5 → ML6

---

## 📄 File Guide

### 🚀 Executable Scripts

#### `run_all.py` (MAIN ENTRY POINT)
**Purpose:** Execute the entire ML pipeline in sequence
**When to use:** `python run_all.py`
**What it does:**
- Runs ML2 → ML3 → ML4 → ML5 → ML6
- Handles errors and provides progress summary
- Can run individual phases with `--phase ml3`
**Dependencies:** All other modules

**Options:**
```bash
python run_all.py                    # All phases
python run_all.py --phase ml3        # Only ML3
python run_all.py --skip-anomaly     # Skip ML4
python run_all.py --verbose          # Debug logging
```

---

#### `features.py` (ML2: Feature Engineering)
**Purpose:** Engineer 6 features from hourly activity data
**When to run:** First (unless features already exist)
**What it does:**
1. Loads `hourly_grid_summary` from Parquet/CSV
2. Computes:
   - `avg_activity`: Mean activity (24h trailing)
   - `activity_growth`: Recent vs baseline growth
   - `active_hours`: Count of hours with activity
   - `peak_ratio`: Peak / mean ratio
   - `variability`: Standard deviation
   - `internet_share`: Internet / total activity
3. Enforces t/t+1 boundary (no future data)
4. Tests for leakage
5. Saves to `network_feature_table/features.parquet`

**Run directly:**
```bash
python features.py
```

**Input files (PLACEHOLDER - update config.py):**
- `data/analytics/hourly_grid_summary/` (Parquet or CSV)

**Output files:**
- `data/ml/network_feature_table/features.parquet`

**Key parameters in config:**
- `RECENT_WINDOW_HOURS = 24`
- `BASELINE_WINDOW_HOURS = 168` (7 days)

---

#### `train.py` (ML3: Train Simple Classifier)
**Purpose:** Train Logistic Regression or Decision Tree
**When to run:** After ML2
**What it does:**
1. Loads engineered features from ML2
2. Creates HIGH_ACTIVITY labels (75th percentile threshold)
3. Performs chronological train/test split (70/30)
4. Trains model with class balancing
5. Evaluates: Accuracy, Precision, Recall
6. Reports feature importance/coefficients
7. Saves model to `model.pkl`

**Run directly:**
```bash
python train.py
```

**Input files:**
- `data/ml/network_feature_table/features.parquet` (from ML2)
- `data/analytics/hourly_grid_summary/` (for labels)

**Output files:**
- `data/ml/model.pkl` (trained model)

**Key parameters in config:**
- `ACTIVITY_PERCENTILE = 75` (label threshold)
- `MODEL_TYPE = 'logistic'` (or 'tree')
- `TRAINING_TEST_SPLIT_RATIO = 0.7`

**⚠️ Important:**
- If accuracy > 95%, check for data leakage!
- Base rate matters as much as accuracy
- Chronological split (NOT random) is mandatory

---

#### `anomaly.py` (ML4: Anomaly Detection)
**Purpose:** Detect unusual activity using hour-of-day baselines
**When to run:** After Spark processing (can be parallel to ML3)
**What it does:**
1. Loads hourly_grid_summary
2. Computes historical baseline per hour-of-day bucket
3. Flags HIGH (above baseline) or LOW (<50% baseline)
4. Optionally compares with rules and classifier
5. Saves anomaly scores and directions

**Run directly:**
```bash
python anomaly.py
```

**Input files:**
- `data/analytics/hourly_grid_summary/` (Parquet or CSV)
- Optional: Rule alerts and classifier predictions

**Output files:**
- `data/ml/network_anomaly_scores.parquet`

**Key parameters in config:**
- `ANOMALY_BUCKETING_KEY = 'hour_of_day'`
- `ANOMALY_Z_SCORE_THRESHOLD = 2.0`

**Why this works:**
- Needs 7+ days to build meaningful hour-of-day baselines
- NP3 (1-day) couldn't do this, had to use within-day baseline
- Now with accumulated history, can see patterns

---

#### `predict.py` (ML5: Model Inference)
**Purpose:** Load model and run inference for single/batch predictions
**When to run:** After ML3 (validation)
**What it does:**
1. Loads trained model from `model.pkl`
2. Validates feature inputs
3. Runs inference: single-sample and batch modes
4. Returns risk_score (0.0-1.0) and risk_level (NORMAL/ATTENTION/HIGH)
5. Provides `PredictionRequest` and `PredictionResponse` classes

**Run directly:**
```bash
python predict.py
```

**Input files:**
- `data/ml/model.pkl` (from ML3)

**Use in code:**
```python
from predict import NetworkRiskPredictor, PredictionRequest

predictor = NetworkRiskPredictor(model_path='data/ml/model.pkl')
request = PredictionRequest(grid_id=4821, ...)
response = predictor.predict_single(request)
print(f"Risk: {response.risk_level}")
```

**Called by:**
- FastAPI endpoint (api/routers/prediction.py)
- Batch scoring (batch_score.py)

**Risk level thresholds (in config):**
- `RISK_LEVEL_HIGH = 0.7`
- `RISK_LEVEL_ATTENTION = 0.4`

---

#### `batch_score.py` (ML6: Batch Scoring)
**Purpose:** Score all grids/timestamps and integrate into pipeline
**When to run:** After ML2, ML3, ML4 (production integration)
**What it does:**
1. Loads features from ML2
2. Loads trained model from ML3
3. Optionally loads anomaly scores from ML4
4. Runs inference on all rows
5. Combines ML risk + anomaly scores
6. Generates top-20 operational attention report
7. Validates score integrity
8. Saves `network_risk_scores/risk_scores.parquet`

**Run directly:**
```bash
python batch_score.py
```

**Input files:**
- `data/ml/network_feature_table/` (from ML2)
- `data/ml/model.pkl` (from ML3)
- `data/ml/network_anomaly_scores.parquet` (from ML4, optional)

**Output files:**
- `data/ml/network_risk_scores/risk_scores.parquet`

**Designed for Airflow integration:**
```python
from ml.batch_score import run_batch_scoring

task = PythonOperator(
    task_id='ml_batch_score',
    python_callable=run_batch_scoring,
    op_kwargs={...}
)
```

**Key parameters in config:**
- `TOP_ATTENTION_N = 20` (grids in report)
- `ATTENTION_ML_WEIGHT = 0.6`, `ATTENTION_ANOMALY_WEIGHT = 0.4`

---

### ⚙️ Configuration & Setup

#### `config.py` (CONFIGURATION CENTER)
**Purpose:** Central configuration for all ML modules
**When to use:** Edit once at the beginning
**What to configure:**
1. Input paths: `HOURLY_SUMMARY_PATH`
2. Output paths: `FEATURES_OUTPUT_PATH`, `MODEL_OUTPUT_PATH`, etc.
3. Feature parameters: Window sizes, thresholds
4. Model parameters: Type, hyperparameters
5. Risk thresholds: HIGH, ATTENTION, NORMAL cutoffs
6. Logging: Level, file path

**All modules import from here:**
```python
from config import HOURLY_SUMMARY_PATH, MODEL_OUTPUT_PATH, ...
```

**Run to validate:**
```bash
python config.py
```

**Key sections:**
- `DATA PATHS`: Input/output locations (EDIT THESE!)
- `FEATURE ENGINEERING PARAMETERS`: Window sizes
- `LABELING PARAMETERS`: Percentile threshold
- `MODEL PARAMETERS`: Model type, hyperparameters
- `ANOMALY DETECTION PARAMETERS`: Baseline method
- `RISK SCORING PARAMETERS`: Thresholds

**Helper functions:**
- `ensure_output_directories()`: Create all output folders
- `get_config_summary()`: Print configuration

---

#### `requirements.txt` (DEPENDENCIES)
**Purpose:** Python package dependencies
**When to use:** `pip install -r requirements.txt`
**What's included:**
- pandas, numpy: Data processing
- scikit-learn: ML models (Logistic Regression, Decision Tree)
- pyarrow: Parquet I/O
- sqlalchemy, psycopg2, pymysql: Database connectivity (optional)
- pytest: Testing (optional)

**Install:**
```bash
pip install -r requirements.txt
```

---

#### `__init__.py` (PYTHON PACKAGE)
**Purpose:** Makes ml_phase a Python package
**What it does:**
- Imports key classes for easy access
- Provides version info
- Handles import errors gracefully

**Use:**
```python
from ml_phase import NetworkActivityFeatures, NetworkRiskPredictor
```

---

### 📚 Documentation

#### `QUICKSTART.md` (⭐ START HERE)
**Purpose:** Quick reference for new users
**Contents:**
- 5-minute setup
- How to run the pipeline
- Common issues and fixes
- Validation checklist
**Read time:** 5 minutes
**Next step:** Read ML1_PROBLEM_STATEMENT.md

---

#### `ML1_PROBLEM_STATEMENT.md` (UNDERSTAND THE PROBLEM)
**Purpose:** Problem definition and constraints
**Contents:**
- What we're predicting (high-activity risk, NOT congestion)
- Data availability and limitations
- The t/t+1 time boundary (CRITICAL)
- Leakage prevention
- What would it take to claim congestion (we don't have it)
- Operational actions (investigate, not conclude)

**Key takeaway:**
- This is an attention signal, not a network fault diagnosis
- We do NOT have capacity/throughput data

**Read time:** 15 minutes
**Critical section:** "The t / t+1 Rule"

---

#### `README_ML_PHASE.md` (COMPLETE DOCUMENTATION)
**Purpose:** Full ML pipeline documentation
**Contents:**
- Overview of all phases
- Setup instructions
- Detailed execution guide for each phase
- Data flow diagram
- Critical time boundaries
- Validation checks
- Example pipeline run
- Debugging guide
- Next steps for integration

**Read time:** 30 minutes
**Best for:** Learning and reference

---

#### `INDEX.md` (THIS FILE)
**Purpose:** Guide to all files and their purposes
**Contents:**
- File descriptions
- Usage instructions
- Dependencies
- When to run each module
- Configuration options

---

### 🔧 Utility Files

#### `.gitignore` (GIT IGNORE PATTERNS)
**Purpose:** Keep large outputs out of Git repository
**What it ignores:**
- Python compiled files (`*.pyc`)
- Model artifacts (`*.pkl`)
- Feature/score Parquets
- Logs
- IDE and system files

---

## 🔄 Execution Flow

### Sequential Execution (Recommended)

```
START
  ↓
[ML2: features.py]
  Input: data/analytics/hourly_grid_summary/
  Output: features.parquet
  Time: 1-5 min
  ↓
[ML3: train.py]
  Input: features.parquet + hourly_grid_summary
  Output: model.pkl
  Time: 1-2 min
  ↓
[ML4: anomaly.py] ← Can run parallel to ML3
  Input: hourly_grid_summary
  Output: network_anomaly_scores.parquet
  Time: 1-2 min
  ↓
[ML5: predict.py]
  Input: model.pkl
  Output: Validation only
  Time: <1 min
  ↓
[ML6: batch_score.py]
  Input: features.parquet + model.pkl + anomaly scores
  Output: risk_scores.parquet
  Time: 2-5 min
  ↓
END
Total time: 7-20 minutes (depending on data size)
```

### Using run_all.py

```bash
python run_all.py
```

Executes the entire flow with error handling and progress reporting.

### Running Individual Phases

```bash
python run_all.py --phase ml3        # Only ML3
python run_all.py --skip-anomaly     # All except ML4
python features.py                   # Direct execution
```

---

## 🎯 Key Files by Purpose

### Just want to extract features?
→ Run `features.py` alone

### Just want to train a model?
→ Run `features.py` then `train.py`

### Complete pipeline?
→ Run `python run_all.py`

### Integrate with Airflow?
→ Call `run_batch_scoring()` from batch_score.py

### Use in FastAPI?
→ Import `NetworkRiskPredictor` from predict.py

### Understand the problem?
→ Read `ML1_PROBLEM_STATEMENT.md`

### Debug an issue?
→ Check `README_ML_PHASE.md` → Debugging section

---

## ✅ Implementation Checklist

- [ ] Read `QUICKSTART.md` (5 min)
- [ ] Read `ML1_PROBLEM_STATEMENT.md` (15 min)
- [ ] Update paths in `config.py`
- [ ] `pip install -r requirements.txt`
- [ ] `python run_all.py` (7-20 min)
- [ ] Verify outputs exist:
  - [ ] `data/ml/network_feature_table/features.parquet`
  - [ ] `data/ml/model.pkl`
  - [ ] `data/ml/network_anomaly_scores.parquet`
  - [ ] `data/ml/network_risk_scores/risk_scores.parquet`
- [ ] Read `README_ML_PHASE.md` for integration

---

## 📊 File Statistics

| File | Type | Lines | Purpose |
|------|------|-------|---------|
| run_all.py | Script | ~300 | Execute entire pipeline |
| features.py | Module | ~400 | Engineer features (ML2) |
| train.py | Module | ~350 | Train classifier (ML3) |
| anomaly.py | Module | ~350 | Detect anomalies (ML4) |
| predict.py | Module | ~300 | Model inference (ML5) |
| batch_score.py | Module | ~300 | Batch scoring (ML6) |
| config.py | Config | ~250 | Centralized configuration |
| **Total Python** | | **~2,250** | All executable code |
| README_ML_PHASE.md | Docs | ~600 | Complete documentation |
| ML1_PROBLEM_STATEMENT.md | Docs | ~200 | Problem definition |
| QUICKSTART.md | Docs | ~300 | Quick reference |
| **Total Docs** | | **~1,100** | All documentation |

---

## 🚀 Next After ML

Once ML phase is complete, proceed to:

1. **Phase 7 (Claude):** Use ML outputs in Claude tools and agents
   - Risk scores as evidence
   - Anomaly baseline for investigation
   - Model versioning and monitoring

2. **API Integration:** Expose risk scores through FastAPI
   - Prediction endpoint (POST /network/predict-risk)
   - Risk scores queryable via API

3. **React Dashboard:** Visualize predictions
   - Predictive Risk View
   - Model output separate from narrative

4. **Airflow:** Integrate batch scoring into daily pipeline
   - After feature generation
   - Before quality check

---

## 💬 Quick Reference

### Run everything:
```bash
python run_all.py
```

### Run one phase:
```bash
python run_all.py --phase ml3
```

### Run directly:
```bash
python features.py  # ML2
python train.py     # ML3
python anomaly.py   # ML4
python predict.py   # ML5
python batch_score.py  # ML6
```

### Check configuration:
```bash
python config.py
```

### Install dependencies:
```bash
pip install -r requirements.txt
```

---

**Version:** 1.0  
**Last Updated:** 2024  
**Status:** Ready for local execution  
**Next Phase:** Phase 7 (Claude) or Integration
