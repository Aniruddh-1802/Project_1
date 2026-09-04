# DE7 — Troubleshooting Map

Which module to debug for each failure type, and what the DE7 pipeline
status record (`logs/pipeline_status_latest.json`) shows when it happens.

| Failure | Task that fails | Module to debug | Status record signal |
|---|---|---|---|
| No files in `data/landing/` | `ingest` | `de2_ingestion.detect_files` | `per_task_status.ingest = "success"` but `rows_in = 0`; `reasons` includes "no VALID files were ingested this run" |
| Malformed CSV (bad schema, bad timestamp, negative value, non-numeric value) | `validate` (task itself still succeeds — the file is rejected, not the task) | `de2_ingestion.validate_schema` / `validate_minimum_quality` | `rows_rejected > 0`; check `data/rejected/` and `logs/ingestion_log.csv` for the named reason |
| Same filename re-arrives after being accepted | `validate` (task succeeds; file is quarantined) | `de2_ingestion.is_duplicate` / `route_file` | status `DUPLICATE` in `logs/ingestion_log.csv`; file lands in `data/rejected/` with a `.dup-<timestamp>` suffix if it collides with an existing rejected file |
| Empty `data/raw/` when Spark runs | `spark_process` | `spark/telecom_pipeline.py` → `ingetision_module.load_raw_network_data` | task fails; `load_warehouse` and downstream analytics are skipped; `per_task_status.spark_process != "success"` |
| Spark job crashes mid-run (bad data, OOM, Hadoop/winutils misconfigured) | `spark_process` | `spark/telecom_pipeline.py` and its helpers (`spark_cleaning.py`, `spark_aggregation.py`, `spark_geo_enrichment.py`, `output_layer.py`) | task fails; analytics layer is left as it was before the run (Spark's overwrite is all-or-nothing per output path); `reasons` names `spark_process` |
| Reference GeoJSON missing or empty | `spark_process` | `spark/spark_geo_enrichment.load_grid_lookup` | task fails with `FileNotFoundError`/`ValueError`; `load_warehouse` skipped |
| MySQL unreachable, or JDBC/SQLAlchemy misconfigured | `load_warehouse` | `Data Engineering/de6_warehouse.py` | task fails; `quality_check` still runs (ALL_DONE) and records `rows_published = None` |
| Warehouse load succeeds but a table ends up empty | `load_warehouse` | `de6_warehouse.py::NetworkWarehouse.validate` | task raises `ValueError` before completing; `reasons` names `load_warehouse` |
| Metrics collection itself fails (e.g. `de7_collect_metrics.py` can't reach MySQL or the analytics path) | `quality_check` (task still completes — it does not crash the DAG here) | `Data Engineering/de7_collect_metrics.py` | `reasons` includes `"metrics collection failed: ..."`; `nulls_handled`/`as_of`/`rows_published` are `null` |
| Everything upstream succeeded but the run is still marked unhealthy | `notify` | the `quality_check` task's `reasons` list itself | `notify` raises, marking the DAG run failed — this is the single unambiguous failure signal for the whole run |

## Reading order when a run fails

1. Check `logs/pipeline_status_latest.json` first — `per_task_status` says which task(s) failed, and `reasons` says why in one line.
2. If `ingest`/`validate` are named, check `logs/ingestion_log.csv` and `data/rejected/` for the specific file and reason.
3. If `spark_process` is named, check the Airflow task log for that run — it is the captured stdout/stderr of `telecom_pipeline.py`.
4. If `load_warehouse` is named, check MySQL connectivity and the `telecom_warehouse_de6` schema directly.
5. Never trust a "success" DAG-run color alone — `quality_check`/`notify` use `ALL_DONE` specifically so a failure earlier in the chain is still recorded in the status file even when later housekeeping tasks run. The DAG run's own final success/failure (via `notify` re-raising) is the one signal safe to treat as ground truth.
