# Data Engineering — how these files run on this machine

All paths in these files are hardcoded absolute paths for
`C:\Users\aniruddh.singh\Documents\Project_1`.

## Why there are two sets of paths

| Runs where | Why | Path form |
|---|---|---|
| Windows (`python.exe` 3.11) | Java 17 + pyspark 4.2, pyarrow, pymysql all live here | `C:\Users\aniruddh.singh\Documents\Project_1\...` |
| WSL Ubuntu-26.04 (`airflow-env`) | Airflow 3.3.1 lives here; it has no Java and no pyspark | `/mnt/c/Users/aniruddh.singh/Documents/Project_1/...` |

Both address the same folders on disk. The Airflow DAGs run in WSL and
shell out to the Windows interpreter for anything involving Spark, MySQL,
or Parquet.

| File | Interpreter | Notes |
|---|---|---|
| `de2_ingestion.py` | either | Picks its path set from `os.name`, so any WSL DAG can import it directly |
| `spark/telecom_pipeline.py` (+ helpers in `spark/`) | Windows | The real DE3 Spark job — already run once by hand; produced the data sitting in `data\processed` and `data\analytics` today |
| `de6_warehouse.py` | Windows | Loads MySQL through SQLAlchemy + PyMySQL (no JDBC jar needed) |
| `de7_collect_metrics.py` | Windows | Reads Parquet (pyarrow) + MySQL (pymysql) for the DE7 pipeline status record |
| `raw_ingestion_dag.py` (DE2 DAG) | WSL Airflow | Imports the DE2 functions rather than reimplementing them |
| `spark_proc.py` (DE3 DAG) | WSL Airflow | `BashOperator` → Windows `python.exe` → `spark/telecom_pipeline.py` |
| `warehouse.py` (DE6 DAG) | WSL Airflow | `BashOperator` → Windows `python.exe` → `de6_warehouse.py` |
| `de7_end_to_end.py` (DE7 DAG) | WSL Airflow | ingest → validate → spark_process → load_warehouse → quality_check → notify, reusing all of the above; writes `logs/pipeline_status_latest.json` |

`Data Engineering/_superseded/de3_spark.py` was a redundant reimplementation
of the Spark job from a different source than the rest of the project — see
`_superseded/README.md` for why it isn't used. `_original/` holds the
as-received, unmodified copies of every DE file for reference/diffing.

## Data zones

```
data\landing    incoming daily sms-call-internet-mi-YYYY-MM-DD.csv
data\raw        accepted files (DE2 moves them here; immutable — reruns are quarantined, not merged in)
data\rejected   quarantined files + stated reason (including DUPLICATE on rerun)
data\reference  milano-grid.geojson (static, never ingested)
data\processed\activity            DE3 cleaned rows, partitioned by date
data\analytics\hourly_grid_summary DE3 aggregated + geo-enriched, read by DE6
data\analytics\dashboard_summary   DE3 curated CSV for the dashboard
logs\ingestion_log.csv             DE2 audit trail (filename, status, row_count, reason, processed_at)
logs\pipeline_status_latest.json   DE7 machine-readable run status (see docs/DE7_*)
```

## Run order (standalone, on Windows)

```powershell
python "C:\Users\aniruddh.singh\Documents\Project_1\Data Engineering\de2_ingestion.py"

python "C:\Users\aniruddh.singh\Documents\Project_1\spark\telecom_pipeline.py" `
    --input "C:\Users\aniruddh.singh\Documents\Project_1\data\raw" `
    --output "C:\Users\aniruddh.singh\Documents\Project_1\data" `
    --reference "C:\Users\aniruddh.singh\Documents\Project_1\data\reference"

python "C:\Users\aniruddh.singh\Documents\Project_1\Data Engineering\de6_warehouse.py"
```

DE2 **moves** files out of `data\landing` into `data\raw`. Rerunning DE2 on
a filename already accepted into `raw\` does **not** overwrite it — the
rerun copy is quarantined to `data\rejected\` and logged with status
`DUPLICATE` (see `de2_ingestion.is_duplicate`).

DE6 writes to the MySQL database `telecom_warehouse_de6`, which it creates
if missing. `telecom_project_1` (loaded separately by
`SQL_load_verify\load_to_sql.py`) is left untouched. Sample validation
queries are in `de6_validation_queries.sql`.

## Run order (through Airflow, in WSL)

```bash
export AIRFLOW_HOME=/home/aniruddhsingh/airflow
source /mnt/c/Users/aniruddh.singh/Documents/Project_1/airflow-env/bin/activate

airflow db migrate
ln -s "/mnt/c/Users/aniruddh.singh/Documents/Project_1/Data Engineering" "$AIRFLOW_HOME/dags"

airflow standalone
```

Either trigger the three single-purpose DAGs in order
(`de2_landing_to_raw` → `de3_spark_processing` → `de6_network_warehouse`),
or trigger `de7_end_to_end`, which runs the whole chain in one DAG and
writes `logs/pipeline_status_latest.json` at the end — see
`docs/DE7_architecture_to_dag_mapping.md` and `docs/DE7_troubleshooting_map.md`.

`.airflowignore` keeps Airflow from parsing `de2_ingestion.py`'s heavier
siblings (`de6_warehouse.py`, `de7_collect_metrics.py`, and anything in
`_original/`, `_superseded/`, `docs/`, `tests/`) — those import pyspark,
pyarrow, or pymysql, none of which exist in the WSL venv.

## Tests

```powershell
python -m pytest "Data Engineering\tests\test_de2_ingestion.py" -v
```

Covers the valid path, every DE2/DE8-named invalid path (schema mismatch,
malformed timestamp, missing grid id, negative/non-numeric activity value,
empty file), the duplicate-rerun fix, and reference-file isolation.

## Design docs

`docs/DE1_architecture.md`, `docs/DE4_batch_vs_streaming.md`,
`docs/DE5_storage_strategy.md` — the DE1/DE4/DE5 written deliverables.
`docs/DE7_architecture_to_dag_mapping.md`, `docs/DE7_troubleshooting_map.md`
— DE7's remaining expected outputs.
