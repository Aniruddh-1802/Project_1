# C4 — Repository Map (deliverable)

Produced with Claude Code in read-only exploration; verified by the learner
against the actual build (spot-checked: spark grain, cellId join, /pipeline/status source).

| Directory | Responsibility | Built in |
|---|---|---|
| data/landing, raw, rejected | incoming CSVs; immutable accepted; quarantined + reasons | DE/ingestion labs |
| data/reference/milano-grid.geojson | static grid geometry; joined on properties.cellId | SP enrichment, RE4 |
| data/processed, analytics | Parquet by date; curated warehouse outputs | Spark labs, DE7 |
| logs/ | ingestion audit, run history, machine-readable pipeline status that **API6 serves** | DE7/DE8 |
| ingestion/ | file_detector.py, schema_validator.py, ingestion_logger.py | DE labs |
| spark/ | schemas, cleaning, country-code→grid/hour aggregation, GeoJSON enrichment, telecom_pipeline.py | SP labs |
| airflow/network_pipeline_dag.py | ingest → Spark → warehouse → quality check → scoring → notify | DE2+ |
| api/ | API1 /network/summary · API2 /network/grid/{id} · API3 /network/hotspots, /network/alerts · API4 /features · API5 /network/predict-risk · API6 /location, /pipeline/status | Phase 4 |
| ml/ | features.py (ML2), train.py (ML3), anomaly.py (ML4), predict.py (ML5), batch_score.py (ML6) | Phase 6 |
| frontend/ | React NOC dashboard: overview (RE2), grid explorer (RE3), Milan map (RE4), risk view (RE5) | Phase 5 |
| agents/, mcp/, .claude/ | Phase 7: C1–C3 integrations, C14 noc_investigator.py, C12 network_mcp_server.py, commands/skills/subagents/hooks | Phase 7 |

## Data flow (landing CSV → dashboard)
landing → ingestion validation (rejects to data/rejected) → data/raw (immutable)
→ spark/telecom_pipeline.py (clean, aggregate to hourly grid grain, enrich with
GeoJSON on properties.cellId) → data/processed → analytics/warehouse (DE7)
→ ml/batch_score.py (ML6) writes scores → FastAPI serves API1–API6
→ React dashboard reads the API. Airflow orchestrates and writes the pipeline
status record that /pipeline/status (API6) exposes.
