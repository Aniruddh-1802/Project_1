# C11 — Checkpoint & Rollback Experiment (before/after + decision record)

**Experiment:** double the anomaly flag rate by lowering the ML4 threshold in
ml/anomaly.py (score > 3.0 → score > 2.1). Checkpoint created BEFORE the edit
(Claude Code checkpoint + git tag `pre-c11-threshold-experiment`).

## Quantitative before/after (operational output, not just tests)
| Metric | Before | After | Read |
|---|---|---|---|
| Grids flagged in AS_OF window (ML6 batch) | 41 | 87 | ~2.1× — target hit |
| Top-20 attention list composition | stable core of 17 | 9 of 20 replaced by low-growth grids | list churned toward noise |
| Agreement with NP3 rule alerts | 78% | 54% | **worsened** — new flags mostly uncorroborated |
| Tests | all pass | tests/test_ml.py::test_alert_rate_bounds FAILS | rate bound guard tripped |

## Decision: ROLL BACK
The change increased volume without corroboration: agreement with the
independent NP3 rules dropped 24 points and the RE5 predictive risk view /
ML6 top-twenty would have paged operators on noise. Claude recommended
rollback; the learner decided (per lab ownership).

## Rollback verification (acceptance criterion)
Restored from the checkpoint; re-ran ML6 batch score: flagged grids back to
41, top-20 identical to pre-change snapshot, all tests pass. ✔

**What the experiment showed:** threshold changes must be evaluated on
operational output (alert volume, top-20 composition, NP3 agreement), and the
checkpoint made trying it essentially free.
