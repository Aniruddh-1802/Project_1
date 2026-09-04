---
description: Run the API/grain/leakage test suite and summarize failures
allowed-tools: Bash(pytest*)
---
<!-- C7 command. Orientation: ENGINEERING. Runs the project's real root-level
     tests/ (not a network-intelligence-local copy): the grain check
     (SP3/DE8), the ML2 leakage regression, and the C5 top-movers
     additivity test against the real FastAPI app. test_top_movers.py skips
     itself if the warehouse DB isn't reachable in this environment - a skip
     there is not a pass and should be called out, not silently ignored. -->
!`python -m pytest tests/ -q`

Inputs: none. Output shape: pass/fail/skip counts, then for each failure: test
name, endpoint (API1–API6 / top-movers) or check (grain / leakage), one-line
cause, and whether the failure is a contract (non-additive) break — those are
release blockers per the C5/C15 rule.
