# CLAUDE.md — Network Operations & Predictive Intelligence

<!-- C4 deliverable. These are the PROJECT'S rules, owned by the team, not by
     Claude. Edited by the learner before commit, per the C4 lab process.
     They are re-packaged for the whole team in the C13 plugin. -->

## What this system is
A Milan mobile-network activity intelligence platform built on the Telecom
Italia open dataset: ingestion (Phase 2/DE labs) → Spark canonicalization
(`spark/telecom_pipeline.py`) → Airflow orchestration
(`airflow/network_pipeline_dag.py`) → warehouse/analytics (DE7) → FastAPI
(`api/`, endpoints API1–API6) → ML risk & anomaly scoring (`ml/`, ML1–ML6) →
React NOC dashboard (`frontend/`, RE1–RE5). Phase 7 adds Claude as an
engineered layer: `agents/`, `mcp/`, `.claude/`.

## Non-negotiable rules (the six from Lab C4)

1. **Canonical schema and grain.** Raw grain: one row per
   (grid, 10-min interval, country code). Analytics grain, after
   country-code aggregation: **one row per grid per hourly timestamp**.
   `hourly_grid_summary` must never contain duplicates on
   (grid_id, timestamp) — this is what `/network-health` (C7) and the
   post-edit hook (C10) test.
2. **Analytics grain restated:** one grid per hourly timestamp after
   country-code aggregation. Any transformation that could reintroduce the
   country-code dimension downstream is a defect.
3. **Activity values are proportional activity measures** from the provider —
   NOT call counts, NOT message counts, NOT megabytes. Never convert or label
   them as counts or MB anywhere: code, API fields, UI copy, or prose.
4. **High activity is never "confirmed congestion".** We have no capacity or
   utilization data. Say "elevated activity" / "needs attention". Asking
   "is grid X congested?" must produce a correction, not an answer.
5. **Geographic joins use `properties.cellId`** from
   `data/reference/milano-grid.geojson` — never the 0-based GeoJSON feature
   index. (This was the RE4 map trap; it applies to API6 `/location` too.)
6. **The AS_OF convention defines "now".** The dataset is historical; the
   current reporting window is the configured AS_OF timestamp, not wall-clock
   time. Baselines must exclude the current interval (enforced in C5).

## Data scope for all Claude integrations (Phase 7)
Curated evidence only: API responses, ML outputs, pipeline status. Never raw
rows. `data/raw/` is immutable — deletion is DENIED by policy (see
`.claude/settings.json`, Lab C6).

## Response contracts
- Single-grid explanation: SEVERITY / EVIDENCE / INTERPRETATION / NEXT CHECKS (C1)
- Incident investigation: CURRENT EVIDENCE / HISTORICAL EVIDENCE / UNCERTAINTY (C3)
- If evidence is insufficient, say so; never fill gaps or invent numbers.
- Every figure names its source (tool/endpoint).

## Where things live
See `docs/repository_map.md` (C4 deliverable) and `docs/architecture.md`.
Tests in `tests/` are invoked by the C10 hooks and the C15 CI review.
