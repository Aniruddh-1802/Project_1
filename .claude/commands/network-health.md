---
description: Run the grain duplicate check on hourly_grid_summary and report pass/fail
allowed-tools: Bash(pytest*), Bash(python*)
---
<!-- C7 command. Orientation: ENGINEERING. Guards CLAUDE.md rules 1–2 (canonical
     grain: one grid per hourly timestamp after country-code aggregation).
     Same check the C10 post-edit hook runs automatically. -->
Run the canonical grain check:

!`python -m pytest tests/test_grain.py -q`

Inputs: none (always checks analytics.hourly_grid_summary for the AS_OF window).
Output shape: PASS, or FAIL with the duplicated (grid_id, timestamp) pairs and
which upstream stage (spark/aggregations.py country-code rollup) most likely
reintroduced them. Acceptance: this MUST fail when a duplicate is deliberately
inserted (verified in the lab).
