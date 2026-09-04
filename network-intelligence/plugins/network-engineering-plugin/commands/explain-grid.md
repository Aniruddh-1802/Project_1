---
description: Gather activity, features, anomaly score and location for a grid, then produce the four-section response
argument-hint: <grid_id>
allowed-tools: Bash(curl*)
---
<!-- C7 command. Orientation: NOC. Composes API2 + API4 + ML4/ML6 + API6 and the
     C1 response contract. The network-anomaly-analysis skill (C8) supplies the
     interpretation rules. -->
Grid to explain: $ARGUMENTS

Gather evidence (cite the source of every figure):
!`curl -s $NETWORK_API_BASE/network/grid/$ARGUMENTS`
!`curl -s $NETWORK_API_BASE/network/grid/$ARGUMENTS/features`
!`curl -s $NETWORK_API_BASE/network/grid/$ARGUMENTS/anomaly`
!`curl -s $NETWORK_API_BASE/network/grid/$ARGUMENTS/location`
!`curl -s $NETWORK_API_BASE/pipeline/status`

Output shape: exactly SEVERITY / EVIDENCE / INTERPRETATION / NEXT CHECKS.
Terminology rules from CLAUDE.md apply: activity measures not counts/MB; never
claim congestion; grid is a geographic cell, not a tower. If any call above
failed, state the gap instead of estimating.
