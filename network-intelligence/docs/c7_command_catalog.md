# C7 — Project Command Set (documented inputs/outputs + orientation)

| Command | Orientation | Inputs | Output shape | Wraps |
|---|---|---|---|---|
| /network-health | Engineering | none | PASS/FAIL + duplicated (grid_id, timestamp) pairs | tests/test_grain.py — CLAUDE.md grain rules; same check as the C10 hook |
| /test-api | Engineering | none | pass/fail counts + per-failure endpoint & contract-break flag | tests/test_api.py + tests/test_top_movers.py (C5) |
| /check-pipeline | NOC | none | HEALTHY/DEGRADED/FAILED + rejected rows, staleness | API6 /pipeline/status (DE7 status record, DE8 injections) |
| /explain-grid <id> | NOC | grid_id | four-section SEVERITY/EVIDENCE/INTERPRETATION/NEXT CHECKS | API2, API4, ML4/ML6, API6 + C1 contract, C8 skill |
| /review-anomaly <id> | NOC | grid_id | 3-signal table + AGREE/DISAGREE + likely cause | NP3 alerts (API3), ML3 classifier (API5), ML4/ML6 anomaly |

Acceptance evidence: all five run; /network-health fails on a deliberately
inserted duplicate (verified by copying one hourly row for grid 4821 into a
scratch copy of hourly_grid_summary and pointing the test fixture at it).
