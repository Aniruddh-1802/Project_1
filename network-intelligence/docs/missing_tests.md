# C4 — Proposed Missing Tests & Documentation (Claude-proposed, learner-reviewed)

1. **Grain uniqueness on hourly_grid_summary** — duplicate (grid_id, timestamp)
   check as a standing test, not just a notebook cell. → became
   tests/test_grain.py, used by /network-health (C7) and the C10 hook.
2. **ML2 feature leakage test** — assert no feature reads data after
   feature_timestamp. → tests/test_ml.py::test_no_leakage, wired into the C10
   post-edit hook and the C15 CI review categories.
3. **cellId join test** — a grid known to differ between feature index and
   properties.cellId must map to the correct polygon (API6 /location).
4. **API contract additivity tests** — response-shape snapshots for API1–API6
   so C5-style changes are provably additive (checked again in C15).
5. **Pipeline-status truthfulness test** — inject a DE8-style failure and
   assert /pipeline/status reflects it (rejected rows, staleness).
6. **Docs gaps** — docs/data_contract.md lacked the AS_OF convention;
   docs/runbook.md lacked the degraded-pipeline NOC procedure (now referenced
   by the pipeline-troubleshooting skill, C8).
