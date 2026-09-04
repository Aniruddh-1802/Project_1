---
description: Compare the rule alert, classifier output and anomaly score for a grid and explain any disagreement
argument-hint: <grid_id>
allowed-tools: Bash(curl*)
---
<!-- C7 command. Orientation: NOC (with an engineering tail). Compares three
     independent signals: NP3 rule alerts (via API3 /network/alerts), the ML3
     classifier (via API5 /network/predict-risk) and the ML4/ML6 anomaly score. -->
Grid to review: $ARGUMENTS

!`curl -s "$NETWORK_API_BASE/network/alerts?grid_id=$ARGUMENTS"`
!`curl -s -X POST $NETWORK_API_BASE/network/predict-risk -d "{\"grid_id\": $ARGUMENTS}" -H 'Content-Type: application/json'`
!`curl -s $NETWORK_API_BASE/network/grid/$ARGUMENTS/anomaly`

Inputs: grid_id. Output shape: a three-row signal table (NP3 rule / ML3
classifier / ML4 anomaly), AGREE or DISAGREE, and — if they disagree — the most
likely cause (threshold mismatch, stale ML6 batch score, or a feature-window
difference), stated as inference, not fact. Surface the disagreement; never
average it away (same rule as the C9 combined report).
