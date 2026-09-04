---
description: Run the API test suite and summarize failures
allowed-tools: Bash(pytest*)
---
<!-- C7 command. Orientation: ENGINEERING. Covers API1–API6 plus the C5
     top-movers additivity tests (tests/test_api.py, tests/test_top_movers.py). -->
!`python -m pytest tests/test_api.py tests/test_top_movers.py -q`

Inputs: none. Output shape: pass/fail counts, then for each failure: test name,
endpoint (API1–API6 / top-movers), one-line cause, and whether the failure is a
contract (non-additive) break — those are release blockers per the C5/C15 rule.
