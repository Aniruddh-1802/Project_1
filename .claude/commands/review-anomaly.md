---
description: Compare the NP3 rule signal against the ML2 feature-derived growth signal for a grid and explain any disagreement
argument-hint: <grid_id>
allowed-tools: Bash(curl*)
---
<!-- C7 command. Orientation: NOC (with an engineering tail). Compares two
     independently-computed signals available in this project:
       1. NP3 rule signal - whether $ARGUMENTS appears in /network/alerts or
          /network/hotspots (the real endpoints have no grid_id filter, so
          this command lists results and the caller checks membership).
       2. ML2 feature signal - activity_growth/peak_ratio/variability from
          /network/grid/{id}/features.

     There is no `/network/grid/{id}/anomaly` endpoint, and
     /network/predict-risk is currently a stub (models.py: risk_score is a
     fixed 0.72 regardless of grid) - it cannot yet be used for a genuine
     per-grid comparison. Both limitations must be stated as gaps, not
     papered over, when this command reports a result. -->
Grid to review: $ARGUMENTS

!`curl -s "$NETWORK_API_BASE/network/alerts?limit=50"`
!`curl -s "$NETWORK_API_BASE/network/hotspots?limit=50"`
!`curl -s $NETWORK_API_BASE/network/grid/$ARGUMENTS/features`

Inputs: grid_id. Output shape: a two-row signal table (NP3 rule / ML2
feature), AGREE or DISAGREE, and — if they disagree — the most likely cause
(threshold mismatch or a feature-window difference), stated as inference,
not fact. Explicitly note that /network/predict-risk is a stub and was
therefore excluded from this comparison. Surface disagreement; never average
it away (same rule as the C9 combined report).
