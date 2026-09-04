# DE5 — Storage Strategy & Data Zones

## Zone table

| Zone | Path | Format | Write mode | Partitioning | Retention |
|---|---|---|---|---|---|
| Landing | `data/landing/` | CSV | Files dropped in, then moved out by DE2 | Not partitioned — one file per day, filename carries the date | Transient. A file lives here only until DE2 routes it (minutes to hours). Nothing should stay in landing across a pipeline run. |
| Raw | `data/raw/` | CSV | **Append-only, immutable.** DE2 moves files in; nothing ever moves out or gets rewritten. A rerun of an already-accepted filename is quarantined to `rejected/`, not merged into `raw/`. | Not partitioned — one file per day, filename carries the date | Keep indefinitely (or per a compliance-driven cutoff). This is the only record of exactly what was ingested; anything downstream can be rebuilt from it. |
| Rejected | `data/rejected/` | CSV | Append-only. Collisions get a timestamp suffix so no rejected evidence is ever silently overwritten. | Not partitioned | Retain at least as long as the incident-review window (recommend 90 days), then archive or delete. |
| Reference | `data/reference/` | GeoJSON | **Overwrite, out-of-band.** Updated only when the Milan grid definition itself changes (rare) — never as part of a daily run. | **Explicitly not date-partitioned** — it is one static file, not a daily series. | Keep the current version; if the grid definition ever changes, keep the prior version alongside it for reproducibility of historical warehouse loads. |
| Processed | `data/processed/activity/` | Parquet | **Overwrite per run, partitioned by `date`.** Each DE3 run rewrites only the partitions for the dates it processed. | `date=YYYY-MM-DD/` — earns its keep because downstream readers (warehouse load, ad hoc analysis) routinely filter by date range. | Retain the full accumulated history; this is the working analytical dataset, not an audit record (raw already serves that role). |
| Analytics | `data/analytics/` | Parquet (`hourly_grid_summary`, `dashboard_summary`) | **Overwrite per run.** Aggregates are cheap to recompute from `processed/`, so overwrite is safe and keeps the layer simple. | Not partitioned by date in the current job — the volume (≈1.7M rows total) does not yet justify it; revisit if history grows past a few years. | Retain current + enough history to support warehouse reloads; safe to regenerate from `processed/` if lost. |
| Warehouse | MySQL `telecom_warehouse_de6` (`dim_grid`, `dim_time`, `fact_network_activity`) | Relational tables | `dim_grid`/`dim_time`: replace on each load (they are derived, not appended). `fact_network_activity`: replace on each load in the current job; production would append new time keys incrementally instead of a full reload. | Indexed on `grid_id`, `time_key`, `timestamp` | Retained as the queryable analytics surface; rebuildable from `data/analytics/` at any time. |
| Logs | `logs/` (`ingestion_log.csv`, task logs, pipeline status records) | CSV / JSON | Append-only | Not partitioned | Retain at least one full pipeline lifecycle (covers reruns and incident review); this is the audit trail for DE2 and DE7/DE8, not disposable output. |

## Why raw is immutable

If `raw/` could be silently overwritten, three things become impossible:
1. **Reproducing a past analytics run** — if the input a run actually saw is gone, there is no way to confirm what produced a given `processed/` or `analytics/` output.
2. **Distinguishing a genuine correction from silent data loss** — an overwritten file looks identical to a file that was always correct; nobody can tell after the fact.
3. **Auditing DE8's failure-injection scenarios** — the reliability lab depends on being able to point at exactly what was ingested versus what was rejected; a mutable raw zone destroys that evidence.

This is why DE2's rerun handling (see `de2_ingestion.py::is_duplicate`) quarantines a repeat filename to `rejected/` instead of moving it into `raw/`.

## Why the reference zone is not date-partitioned

`milano-grid.geojson` describes the fixed geometry of 10,000 Milan grid cells — it does not have a "day" dimension. Partitioning it by date would imply a daily reference file that doesn't exist and would need updating even when nothing about the grid changed. It is versioned by replacement, not by date.

## Append vs overwrite, by layer

- **Append:** `raw/`, `rejected/`, `logs/` — these are audit trails. Losing a row means losing evidence of what happened.
- **Overwrite:** `processed/`, `analytics/`, `dim_grid`, `dim_time` — these are derived views. They can always be recomputed from `raw/` + `reference/`, so overwriting on each run is safe and keeps the pipeline idempotent.
- **Reload (currently overwrite, should become incremental append in production):** `fact_network_activity` — a full reload works at this data volume but does not scale; a production version would append only the new `time_key` range per run.
