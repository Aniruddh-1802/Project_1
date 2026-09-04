---
description: Gather activity, features, hotspot standing and location for a grid, then produce the four-section response
argument-hint: <grid_id>
allowed-tools: Bash(curl*)
---
<!-- C7 command. Orientation: NOC. Composes API2 + API4 + API3 + API6 and the
     C1 response contract. The network-anomaly-analysis skill (C8) supplies the
     interpretation rules.

     There is no standalone `/network/grid/{id}/anomaly` endpoint in this
     project - Machine_learning/anomaly.py exists but is not yet wired into
     the API. Until ML5/ML6 expose a stored anomaly score per grid, the
     closest available signals are the ML2 features (activity_growth,
     peak_ratio, variability) and whether the grid appears in /hotspots. -->
Grid to explain: $ARGUMENTS

Gather evidence (cite the source of every figure):
!`curl -s $NETWORK_API_BASE/network/grid/$ARGUMENTS`
!`curl -s $NETWORK_API_BASE/network/grid/$ARGUMENTS/features`
!`curl -s $NETWORK_API_BASE/network/grid/$ARGUMENTS/location`
!`curl -s "$NETWORK_API_BASE/network/hotspots?limit=50"`
!`curl -s $NETWORK_API_BASE/pipeline/status`

Output shape: exactly SEVERITY / EVIDENCE / INTERPRETATION / NEXT CHECKS.
When forming SEVERITY, check whether $ARGUMENTS appears in the /hotspots
list above and read activity_growth/peak_ratio/variability from /features -
there is no separate anomaly score endpoint to call yet. Terminology rules
from CLAUDE.md apply: activity measures not counts/MB; never claim
congestion; grid is a geographic cell, not a tower. If any call above
failed, state the gap instead of estimating.
