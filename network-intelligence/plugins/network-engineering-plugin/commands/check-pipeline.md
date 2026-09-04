---
description: Call GET /pipeline/status and summarize health, naming rejected rows or staleness
allowed-tools: Bash(curl*)
---
<!-- C7 command. Orientation: NOC. Wraps API6 /pipeline/status, which serves the
     machine-readable status record written to logs/ by the DE7 pipeline (and
     exercised by the DE8 failure injections). -->
!`curl -s $NETWORK_API_BASE/pipeline/status`

Inputs: none. Output shape: HEALTHY / DEGRADED / FAILED, then: last successful
run, rejected row count (from data/rejected quarantine), handled nulls,
analytics staleness in hours, and one sentence on what this means for trusting
current answers (feeds the UNCERTAINTY section used in C1/C3/C14).
