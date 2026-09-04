# DE7 — Architecture-to-DAG Mapping

How the DE1 architecture layers map onto the `de7_end_to_end` DAG's six tasks.

| DE1 layer | DE7 task | Reused from | New in DE7 |
|---|---|---|---|
| Ingestion | `ingest`, `validate` | `de2_ingestion.detect_files`, `validate_schema`, `validate_minimum_quality`, `route_file` (imported, not reimplemented) | Nothing — this is the same logic `raw_ingestion_dag.py` runs standalone |
| Processing | `spark_process` | `spark/telecom_pipeline.py` (the same `BashOperator` command `spark_proc.py` uses) | Nothing |
| Warehouse | `load_warehouse` | `Data Engineering/de6_warehouse.py` (the same `BashOperator` command `warehouse.py` uses) | Nothing |
| Pipeline status | `quality_check` | Reads `validate`'s XCom result and the on-disk outputs of `spark_process`/`load_warehouse` | The status record itself: `Data Engineering/de7_collect_metrics.py` (Windows-side metrics collection) and the JSON-writing logic in `quality_check` are new — this is DE7's own deliverable, not a reused component |
| Notification | `notify` | Reads the record `quality_check` just wrote | The re-raise-on-unhealthy logic that turns "housekeeping tasks ran fine" into "the DAG run itself reports failure" |

## Why the DAG contains no business logic

`spark_process` and `load_warehouse` are `BashOperator` calls to the exact same scripts (`telecom_pipeline.py`, `de6_warehouse.py`) that DE3 and DE6 already validated independently. If either script changes, the DAG does not need to change. `ingest`/`validate` import `de2_ingestion` directly rather than re-implementing schema or quality checks inline — the DAG only sequences calls, decides what runs next, and records the outcome.

## Single source of truth for pipeline health

`quality_check` is the only place that writes `logs/pipeline_status_latest.json`. Nothing else in the pipeline computes "healthy" independently — this is deliberate, so that a future consumer (API6's `GET /pipeline/status`) has exactly one place to read from and cannot disagree with the pipeline about its own state.
