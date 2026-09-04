# DE1 — Network Intelligence Architecture

## 1. Data flow

```
sms-call-internet-mi-YYYY-MM-DD.csv          milano-grid.geojson
  (daily activity, arrives one file/day)      (static, 10,000 grid cells)
            |                                            |
            v                                            |
     data/landing/                                       |
            |                                            |
      [DE2] detect -> validate_schema ->                  |
            validate_minimum_quality -> route              |
            |                              |               |
            v                              v               |
     data/raw/ (VALID,               data/rejected/        |
     immutable)                      (INVALID/DUPLICATE,   |
            |                        reason logged)         |
            v                                                |
     logs/ingestion_log.csv <---------------------------------
     (filename, status, row_count, reason, processed_at)
            |
            v
     [DE3] spark/telecom_pipeline.py  <-------- reads data/reference/
            |                                    milano-grid.geojson
            | clean -> aggregate -> enrich -> write
            v
     data/processed/activity/date=YYYY-MM-DD/   (cleaned rows, Parquet)
     data/analytics/hourly_grid_summary/         (aggregated, Parquet)
     data/analytics/dashboard_summary/           (curated CSV)
            |
            v
     [DE6] de6_warehouse.py: dim_grid, dim_time, fact_network_activity
            |
            v
     MySQL: telecom_warehouse_de6
            |
            v
     [API layer] FastAPI reads the warehouse + the DE7 status record
            |
            v
     [React] noc-dashboard consumes the API
            |
            v
     [ML] models train on the warehouse / analytics layer
            |
            v
     [Claude] operations assistant calls the API for evidence,
              never narrates pipeline health from memory
```

## 2. Layer responsibilities (one sentence each, no overlap)

| Layer | Tool | Responsibility |
|---|---|---|
| Landing | filesystem (`data/landing/`) | Hold daily CSVs exactly as they arrive, before any validation. |
| Ingestion | `de2_ingestion.py` + `raw_ingestion_dag.py` | Validate schema/quality and route each file to `raw/` or `rejected/`, once, with an audit record. |
| Raw | filesystem (`data/raw/`) | Preserve accepted daily files unchanged, forever — the only source of truth for what was actually ingested. |
| Rejected | filesystem (`data/rejected/`) | Quarantine invalid or duplicate files with a stated reason, for inspection. |
| Reference | filesystem (`data/reference/`) | Hold the static Milan grid geometry; never touched by the daily ingestion flow. |
| Processing | `spark/telecom_pipeline.py` | Clean, aggregate, and geo-enrich raw activity data into processed and analytics Parquet. It contains all business logic. |
| Processed | filesystem (`data/processed/`) | Store cleaned, per-record activity, partitioned by date. |
| Analytics | filesystem (`data/analytics/`) | Store aggregated, query-ready summaries used by the warehouse load and the dashboard. |
| Warehouse | `de6_warehouse.py` + MySQL | Model analytics data as a star schema (`dim_grid`, `dim_time`, `fact_network_activity`) for repeatable SQL queries. |
| Orchestration | Airflow (`raw_ingestion_dag.py`, `spark_proc.py`, `warehouse.py`, DE7's end-to-end DAG) | Sequence the above steps, enforce task dependencies, and propagate failure — it contains no business logic of its own. |
| Pipeline status | DE7's `quality_check` task | Record run_id, per-task status, row counts, and AS_OF as a machine-readable fact, once per run. |
| API (FastAPI) | `FastAPI/` | Expose the warehouse and the pipeline status record as read endpoints; it computes nothing new. |
| Dashboard (React) | `noc-dashboard/` | Render what the API returns; it holds no business logic. |
| ML | `Machine_learning/` | Train and score models against the warehouse/analytics layer; it does not touch raw or landing. |
| Claude assistant | Phase 7 | Answer operator questions by calling the API's evidence endpoints; it never re-derives pipeline health from memory. |

## 3. Quality gates

Gates that must pass before **raw acceptance** (DE2):
1. Filename matches `sms-call-internet-mi-YYYY-MM-DD.csv` (the `-mi-` is mandatory).
2. Header matches the eight expected columns exactly.
3. File has at least one data row.
4. Every `datetime` value parses.
5. Every `CellID` is present.
6. Every activity column (`smsin`, `smsout`, `callin`, `callout`, `internet`) is numeric and non-negative.
7. The filename is not already present in `raw/` from a prior run (duplicate/rerun check).

Gates that must pass before **analytics publication** (DE3):
1. `data/raw/` contains at least one CSV (empty input fails loudly, not silently).
2. `data/reference/milano-grid.geojson` exists and contains at least one feature.
3. The clean/aggregate stage produces no duplicate `(grid_id, timestamp)` rows (asserted in `spark_aggregation.py`).
4. Output is written only after the full clean → aggregate → enrich chain succeeds (no partial analytics on failure).

## 4. Analytics outputs

| Output | Defined by | Grain |
|---|---|---|
| `hourly_grid_summary` | `spark_aggregation.create_operational_kpis` | one row per `(grid_id, timestamp)` |
| `daily_grid_summary` (`daily_activity_by_grid`) | same | one row per `(date, grid_id)` |
| `hotspots` (`hotspot_ranking`) | same | top 10 grids by daily activity |
| Alert table (`outputs/network_alerts.csv`) | `spark/alert_generator.py` | one row per detected anomaly |
| Risk table | ML phase (not yet built) | one row per `(grid_id, date)` risk score |

## 5. Non-goals

- We do not have capacity, throughput, or utilization data — only activity counts (SMS/call/internet events).
- We do not model live/streaming ingestion in this training dataset; DE4 documents where Kafka would conceptually enter without changing the data.
- We do not duplicate the full grid Polygon geometry into every warehouse fact row — `fact_network_activity` holds keys and measures only; geometry lives in `dim_grid`.
- We do not treat `milano-grid.geojson` as a daily ingestion candidate.
- Pipeline health is recorded in exactly one place: the DE7 `quality_check` status record. The API layer reads it; it does not recompute it.

## 6. Where pipeline health is recorded

The DE7 `quality_check` task writes one machine-readable status record per DAG run (`run_id`, `run_ts`, per-task status, `rows_in`, `rows_rejected`, `nulls_handled`, `rows_published`, `as_of`, `healthy`, `reasons`) to `logs/pipeline_status/<run_id>.json` and to `logs/pipeline_status_latest.json`. `API6`'s `GET /pipeline/status` reads this file; it does not recompute pipeline health independently.
