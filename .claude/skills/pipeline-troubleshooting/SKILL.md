---
name: pipeline-troubleshooting
description: Use when the data pipeline is degraded, a run failed, rejected rows appear, the analytics layer is stale, or someone asks whether the data can be trusted.
---
# Pipeline Troubleshooting (C8 skill)

## Diagnostic order (follow the DAG: ingest → Spark → warehouse → quality → scoring → notify)
1. `GET /pipeline/status` (API6) — read the DE7 status record first.
2. Rejected rows? Inspect `data/rejected/` and its reasons files, and
   `logs/` ingestion audit (ingestion/schema_validator.py decisions).
3. Stale analytics? Check the Airflow run history for the
   `de7_end_to_end` DAG (`Data Engineering/de7_end_to_end.py`, run via WSL
   Airflow) — which task failed: ingest, spark_process
   (`spark/telecom_pipeline.py`), or load_warehouse
   (`Data Engineering/de6_warehouse.py`)?
4. Grain broken? Run tests/test_grain.py (the /network-health check, C7).
5. Scores stale? Machine_learning/batch_score.py (ML6) run timestamp vs
   the AS_OF window.

## Rules
- `data/raw/` is immutable — remediation NEVER edits or deletes raw (C6 deny).
- Report impact in NOC terms: which answers are currently untrustworthy and
  why (this feeds the UNCERTAINTY sections of C1/C3/C14).
- Distinguish handled degradation (nulls handled, rows quarantined — the
  DE8-designed paths) from unhandled failure.
