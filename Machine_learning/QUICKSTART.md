# ML Phase Quick Start Guide

Complete ML pipeline for Network Operations & Predictive Intelligence - Ready to run locally!

## 📋 What You Have

All files needed for ML1-ML6:

```
ml_phase/
├── features.py              ← ML2: Feature Engineering
├── train.py                 ← ML3: Train Classifier  
├── anomaly.py               ← ML4: Anomaly Detection
├── predict.py               ← ML5: Model Inference
├── batch_score.py           ← ML6: Batch Scoring
├── config.py                ← Configuration (paths, parameters)
├── run_all.py               ← Execute entire pipeline
├── __init__.py              ← Python package init
├── requirements.txt         ← Dependencies
├── ML1_PROBLEM_STATEMENT.md ← Problem definition (non-executable)
├── README_ML_PHASE.md       ← Complete documentation
└── QUICKSTART.md            ← This file
```

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Update Paths in config.py

Edit `config.py` to match your data locations:

```python
# INPUT: Where is your Spark output?
HOURLY_SUMMARY_PATH = 'data/analytics/hourly_grid_summary/'

# OUTPUT: Where should ML save results?
FEATURES_OUTPUT_PATH = 'data/ml/network_feature_table/'
MODEL_OUTPUT_PATH = 'data/ml/model.pkl'
ANOMALY_SCORES_PATH = 'data/ml/network_anomaly_scores.parquet'
RISK_SCORES_OUTPUT_PATH = 'data/ml/network_risk_scores/'
```

### 3. Run the Pipeline

**All phases in order:**
```bash
python run_all.py
```

**Or run individual phases:**
```bash
python features.py      # ML2
python train.py         # ML3
python anomaly.py       # ML4
python predict.py       # ML5 (validation)
python batch_score.py   # ML6
```

## 📊 Data Flow

```
Your Spark Output (hourly_grid_summary)
         ↓
    [ML2: Features]
         ↓
    [ML3: Train]
         ↓
    [ML4: Anomaly] ← runs in parallel
         ↓
    [ML5: Validate]
         ↓
    [ML6: Batch Score] ← produces final risk scores
         ↓
    Ready for API & Dashboard
```

## 📍 Expected Input Files

**PLACEHOLDER PATHS** - Update `config.py` to your actual locations:

```
data/
└── analytics/
    └── hourly_grid_summary/     ← Spark output (Parquet directory)
        Columns: timestamp, grid_id, sms_in, sms_out, call_in, 
                 call_out, internet_activity
        Minimum: 10 days of hourly data
        Recommended: 14+ days
```

## 📤 Expected Output Files

After running the pipeline:

```
data/
└── ml/
    ├── network_feature_table/
    │   └── features.parquet     ← ML2 output (6 features per grid/hour)
    ├── model.pkl                ← ML3 output (trained classifier)
    ├── network_anomaly_scores.parquet  ← ML4 output
    └── network_risk_scores/     ← ML6 output (FINAL PRODUCT)
        └── risk_scores.parquet
            Columns: grid_id, timestamp, risk_score, risk_level, model_version
```

## ⚠️ Critical Files in Your Spark Output

**REQUIRED** - Must exist before running ML:

- ✅ `data/analytics/hourly_grid_summary/` (Parquet or CSV)
  - One row per grid per hour
  - Has columns: timestamp, grid_id, total_activity
  - Has 10+ days of data

**NOT REQUIRED** - Optional:
- Reference GeoJSON (used later by React, not in ML)

## 🔍 What Each Phase Does

### ML2: Feature Engineering
- Loads hourly activity data
- Computes 6 features for each grid/hour:
  - avg_activity, activity_growth, active_hours, peak_ratio, variability, internet_share
- **Output:** `network_feature_table/features.parquet`
- **Time:** 1-5 minutes depending on data size

### ML3: Train Classifier
- Creates HIGH_ACTIVITY labels
- Splits chronologically (70% train, 30% test)
- Trains Logistic Regression or Decision Tree
- Reports: Accuracy, Precision, Recall
- **Output:** `model.pkl`
- **Time:** 1-2 minutes

### ML4: Anomaly Detection
- Computes hour-of-day baselines
- Flags HIGH/LOW/NORMAL activity
- **Output:** `network_anomaly_scores.parquet`
- **Time:** 1-2 minutes
- **Note:** Runs independently from ML3

### ML5: Model Inference
- Loads trained model
- Tests single-sample prediction
- Used by API (see api/routers/prediction.py)
- **Output:** None (validation only)
- **Time:** <1 minute

### ML6: Batch Scoring
- Scores all grid/timestamp combinations
- Combines ML risk + anomaly scores
- Generates top-20 attention report
- **Output:** `network_risk_scores/risk_scores.parquet`
- **Time:** 2-5 minutes

## 💡 Common Issues

### Error: "No such file or directory: data/analytics/hourly_grid_summary/"
**Fix:** Update `config.py` with your actual data path

### Error: "Model not found at data/ml/model.pkl"
**Fix:** Run ML3 first: `python train.py`

### Accuracy is ~99%
**⚠️ RED FLAG:** Data leakage detected
- Features are including data from the future (t+1)
- Check the t/t+1 rule in ML1_PROBLEM_STATEMENT.md

### "ModuleNotFoundError: No module named 'sklearn'"
**Fix:** Install dependencies: `pip install -r requirements.txt`

## 🎯 Key Concepts

### The t / t+1 Rule (CRITICAL)
```
Features are computed from: [t-24h, t]
Label describes:            [t+1]

Features can NEVER see data from t+1, or accuracy will be fake!
```

### Chronological Split (MANDATORY)
```
CORRECT:    Train=[2013-10-01:2013-10-28], Test=[2013-10-29:2013-11-05]
WRONG:      Train=[random 70%], Test=[random 30%]
```
Time-series data must NOT be randomly shuffled!

### What is "HIGH_ACTIVITY"?
- Top 25% of all observed activity (75th percentile)
- This is a training proxy, NOT confirmed congestion
- Recommendation for operators: "Investigate this grid"

## 📚 Next Steps

After completing ML:

1. **API Integration** → See `api/routers/prediction.py`
   - FastAPI endpoint serves model predictions

2. **Airflow Integration** → See `airflow/network_pipeline_dag.py`
   - ML6 runs daily after Spark processing

3. **React Dashboard** → See React code
   - Displays risk scores on predictive view

4. **Claude Tools** → See Phase 7 (Claude)
   - Assistant uses risk/anomaly scores as evidence

## 🐛 Debugging

**Enable debug logging:**
```bash
python run_all.py --verbose
```

**Run only one phase:**
```bash
python run_all.py --phase ml3
```

**Skip a phase:**
```bash
python run_all.py --skip-anomaly
```

**Check configuration:**
```bash
python config.py
```

## 📖 Full Documentation

For complete details, see:
- `README_ML_PHASE.md` - Full ML pipeline documentation
- `ML1_PROBLEM_STATEMENT.md` - Problem definition & time boundaries
- Inline docstrings in each module

## ✅ Validation Checklist

Before considering ML complete:

- [ ] ML2 produces `network_feature_table/features.parquet`
- [ ] ML3 trains model and saves `model.pkl`
- [ ] ML3 reports accuracy, precision, recall with base rate
- [ ] ML3 accuracy is < 95% (not suspicious)
- [ ] ML4 produces `network_anomaly_scores.parquet`
- [ ] ML5 validates model loads and predicts
- [ ] ML6 produces `network_risk_scores/risk_scores.parquet`
- [ ] All files have expected columns and no NaN values

## 🎉 Success Looks Like

```
✓ ML2 Complete: 87,600 feature rows
✓ ML3 Complete: Model trained with 78.5% accuracy
✓ ML4 Complete: 87,600 anomaly scores computed
✓ ML5 Complete: Model inference working
✓ ML6 Complete: 87,600 grids scored

All phases completed successfully!
```

---

**Ready?** Run: `python run_all.py`

**Need help?** Check `README_ML_PHASE.md`
