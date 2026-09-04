# Network Operations ML Problem Statement

## Problem Definition

**Primary Objective:** Predict whether a grid cell will exhibit high activity in the next hourly interval.

**Prediction Unit:** One Milan grid cell (grid_id) for one future hourly interval (t+1)

**Data Availability:** Historical aggregated network activity data from hourly intervals ending at time t

---

## Problem Framing

### What We Are Predicting
- **Target:** Binary classification of whether a grid will experience HIGH_ACTIVITY in interval t+1
- **Label Definition:** A grid is labeled HIGH_ACTIVITY if its total_activity in interval t+1 exceeds a threshold (to be set empirically from the data distribution)
- **Time Boundary:** Features are STRICTLY computed from the trailing window ending at t (inclusive). NO data from t+1 is visible to the features.

### The Data We Have
- Grid-level hourly activity measures: sms_in, sms_out, call_in, call_out, internet_activity
- Aggregated from country-code-level records to grid/hour grain
- 10,000 geographic grid cells across Milan
- Historical activity over 14+ days (minimum 10 days)

### What We DO NOT Have
- Network capacity data
- Radio utilization
- Throughput / latency / packet loss
- Customer count
- Tower or BTS information

---

## Non-Goals (Critical)

1. **We do NOT claim confirmed congestion.** High activity is an operational attention signal, not a network fault.
2. **We do NOT use capacity metrics.** Without capacity or throughput data, we cannot define true congestion.
3. **We do NOT predict customer behavior.** This is not a churn or retention problem.
4. **We do NOT build complex neural networks.** Start with interpretable baseline models (Logistic Regression, Decision Tree).

---

## Operational Action

A positive prediction (high-activity risk) leads to:
- **Investigate this grid in the next hour**
- **Drill into recent activity patterns**
- **Check neighboring grids for spatial correlation**
- **Verify pipeline data quality for this grid**

NOT: "The network is congested" or "Customer service will be impacted"

---

## Feature Engineering Discipline

### The t / t+1 Rule
Every feature for prediction at t+1 is computed ONLY from the trailing window ending at t.

```
t-7          t-1     t     t+1 (future)
|-------------|-------|-----|------ (feature window) -----(label)----
<---- recent window ---->   ^       ^
                           Features Label
```

**Feature timestamp = t** (last timestamp the features are allowed to see)

---

## Leakage Prevention

**Circular Label Check:**
- If label = (total_activity_at_t+1 > threshold) AND features include avg_activity_in_t+1, the model is restating itself.
- Solution: features end at t; label describes t+1.

**Test Case:**
- Features for interval t+1 must NOT include any observation from interval t+1 itself.
- This is enforced with an assertion in the feature engineering code.

---

## Target Definition

**Label Strategy (Synthetic Proxy):**
- Compute percentiles of total_activity across all grid/hours in the training period
- Define HIGH_ACTIVITY as total_activity >= 75th percentile
- This is a training proxy. Document it clearly.
- Threshold is set empirically; do not hardcode it.

**Alternative:** Reuse the NP3 rule-based HIGH_ACTIVITY flag as the label.

**Class Balance:**
- Expected: ~25% positive (HIGH), ~75% negative (NORMAL)
- Report base rate alongside accuracy

---

## Validation Strategy

**Chronological Train/Test Split (MANDATORY):**
- Earlier days → train
- Later days → test
- NO random mixing of neighboring time observations
- Record the exact date ranges for reproducibility

**Evaluation Metrics:**
- Accuracy (with base rate reported separately)
- Precision (false-positive cost)
- Recall (missed-activity cost)
- Feature importance / coefficients (interpretability)

**Comparison:**
- Compare model predictions to NP3 rule-based alerts
- Identify where they disagree and why
- Model should add value beyond the baseline rule

---

## What Would It Take to Claim Congestion?

This problem statement does NOT support a congestion claim. To do so, we would need:

1. **Capacity Data:** Theoretical maximum activity for each grid/technology
2. **Utilization Metric:** Actual activity as a percentage of capacity
3. **Service Degradation Evidence:** Throughput, latency, packet loss
4. **Customer Impact Data:** Service quality, complaint volume

**Conclusion:** Call this "high-activity risk" or "unusual activity," never congestion.

---

## References

- **Data Schema:** Core Dataset Contract (main guide)
- **AS_OF Convention:** See main guide architecture section
- **Leakage Discipline:** ML2, ML3 labs in trainer guide
- **Baseline Rules:** NP3 – within-day and hourly baselines
