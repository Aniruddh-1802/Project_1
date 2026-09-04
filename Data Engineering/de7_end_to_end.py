"""
DE7 - End-to-End Airflow Orchestration.

Chains ingest -> validate -> spark_process -> load_warehouse ->
quality_check -> notify, reusing the existing DE2/DE3/DE6 functions
and jobs (no cleaning/aggregation/warehouse logic is reimplemented
here).

quality_check writes a machine-readable pipeline status record -
run_id, run timestamp, per-task status, rows in, rows rejected,
nulls handled, rows published, and AS_OF (max analytics timestamp) -
to logs/pipeline_status/. This is the evidence source API6 will
later expose, and the record DE8 asks failures to be reflected in.

Runs in WSL Airflow. spark_process, load_warehouse and the metrics
collection in quality_check shell out to the Windows interpreter,
because Java, pyspark, pyarrow and the MySQL client all live there.
"""

import json
import os
import subprocess
import sys

from datetime import datetime, timezone

from airflow.sdk import dag, task
from airflow.providers.standard.operators.bash import BashOperator
from airflow.task.trigger_rule import TriggerRule


# ============================================================
# ABSOLUTE PATHS (WSL view unless noted)
# ============================================================

PROJECT_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1"

DE_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/Data Engineering"

if DE_DIR not in sys.path:
    sys.path.insert(0, DE_DIR)

from de2_ingestion import (
    detect_files,
    validate_schema,
    validate_minimum_quality,
    route_file,
)

RAW_PATH = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/raw"

STATUS_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/logs/pipeline_status"

STATUS_LATEST = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/logs/pipeline_status_latest.json"

# --- Windows side (BashOperator / subprocess targets) ---

WINDOWS_PYTHON = "/mnt/c/Users/aniruddh.singh/AppData/Local/Programs/Python/Python311/python.exe"

WINDOWS_TELECOM_PIPELINE = "C:/Users/aniruddh.singh/Documents/Project_1/spark/telecom_pipeline.py"

WINDOWS_INPUT = "C:/Users/aniruddh.singh/Documents/Project_1/data/raw"
WINDOWS_OUTPUT = "C:/Users/aniruddh.singh/Documents/Project_1/data"
WINDOWS_REFERENCE = "C:/Users/aniruddh.singh/Documents/Project_1/data/reference"

WINDOWS_WAREHOUSE_SCRIPT = "C:/Users/aniruddh.singh/Documents/Project_1/Data Engineering/de6_warehouse.py"

WINDOWS_METRICS_SCRIPT = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/Data Engineering/de7_collect_metrics.py"


@dag(
    dag_id="de7_end_to_end",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["DE7", "end-to-end", "orchestration"],
)
def de7_end_to_end():

    # ========================================================
    # 1. INGEST  (reuses de2_ingestion.detect_files)
    # ========================================================

    @task
    def ingest():

        files = detect_files()

        if not files:
            print("No files detected in landing zone.")

        return files

    # ========================================================
    # 2. VALIDATE  (reuses de2_ingestion.validate_schema /
    #    validate_minimum_quality / route_file - routing is part
    #    of validation, not a separate reimplementation)
    # ========================================================

    @task
    def validate(files):

        results = []

        for file_path in files:

            filename = os.path.basename(file_path)

            schema_valid, schema_reason = validate_schema(file_path)

            if not schema_valid:
                route_file(file_path, "REJECTED", schema_reason, 0)
                results.append({
                    "filename": filename,
                    "status": "REJECTED",
                    "row_count": 0,
                    "reason": schema_reason,
                })
                continue

            quality_valid, row_count, quality_reason = validate_minimum_quality(file_path)

            status = "VALID" if quality_valid else "REJECTED"

            route_file(file_path, status, quality_reason, row_count)

            results.append({
                "filename": filename,
                "status": status,  # route_file may upgrade this to DUPLICATE
                "row_count": row_count,
                "reason": quality_reason,
            })

        return results

    # ========================================================
    # 3. SPARK_PROCESS  (same job DE3 uses: spark/telecom_pipeline.py)
    # ========================================================

    spark_process = BashOperator(
        task_id="spark_process",
        bash_command=(
            f'"{WINDOWS_PYTHON}" "{WINDOWS_TELECOM_PIPELINE}" '
            f'--input "{WINDOWS_INPUT}" '
            f'--output "{WINDOWS_OUTPUT}" '
            f'--reference "{WINDOWS_REFERENCE}"'
        ),
    )

    # ========================================================
    # 4. LOAD_WAREHOUSE  (same job DE6 uses: de6_warehouse.py)
    # ========================================================

    load_warehouse = BashOperator(
        task_id="load_warehouse",
        bash_command=(
            f'"{WINDOWS_PYTHON}" "{WINDOWS_WAREHOUSE_SCRIPT}"'
        ),
    )

    # ========================================================
    # 5. QUALITY_CHECK
    #
    # Runs regardless of upstream success/failure (ALL_DONE) so a
    # failure is recorded, not silently dropped - this is what
    # DE8's fault-injection scenarios rely on being reflected here.
    # ========================================================

    @task(trigger_rule=TriggerRule.ALL_DONE)
    def quality_check(validate_results):

        from airflow.sdk import get_current_context

        context = get_current_context()

        run_id = context["run_id"]
        run_ts = context["ts"]

        dag_run = context["dag_run"]

        task_instances = {
            ti.task_id: ti.state
            for ti in dag_run.get_task_instances()
        }

        per_task_status = {
            task_id: task_instances.get(task_id, "unknown")
            for task_id in [
                "ingest",
                "validate",
                "spark_process",
                "load_warehouse",
            ]
        }

        rows_in = sum(r["row_count"] for r in validate_results)

        rows_rejected = sum(
            r["row_count"]
            for r in validate_results
            if r["status"] != "VALID"
        )

        valid_filenames = [
            r["filename"] for r in validate_results if r["status"] == "VALID"
        ]

        reasons = []

        metrics = {
            "nulls_handled": None,
            "as_of": None,
            "warehouse_row_counts": {},
        }

        if per_task_status["spark_process"] == "success" and per_task_status["load_warehouse"] == "success":

            raw_files_arg = ",".join(valid_filenames)

            try:
                output = subprocess.check_output(
                    [
                        WINDOWS_PYTHON,
                        WINDOWS_METRICS_SCRIPT,
                        "--raw-files", raw_files_arg,
                    ],
                    text=True,
                    timeout=600,
                )

                metrics = json.loads(output.strip().splitlines()[-1])

            except Exception as exc:
                reasons.append(f"metrics collection failed: {exc}")

        else:
            reasons.append(
                "spark_process or load_warehouse did not succeed; "
                "analytics/warehouse metrics not collected"
            )

        rows_published = (
            metrics.get("warehouse_row_counts", {})
            .get("fact_network_activity")
        )

        for task_id, state in per_task_status.items():
            if state not in ("success", "skipped"):
                reasons.append(f"{task_id} did not succeed (state={state})")

        if not valid_filenames and per_task_status["ingest"] == "success":
            reasons.append("no VALID files were ingested this run")

        healthy = (
            len(reasons) == 0
            and rows_published is not None
            and rows_published > 0
        )

        status_record = {
            "run_id": run_id,
            "run_ts": run_ts,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "per_task_status": per_task_status,
            "rows_in": rows_in,
            "rows_rejected": rows_rejected,
            "nulls_handled": metrics.get("nulls_handled"),
            "rows_published": rows_published,
            "as_of": metrics.get("as_of"),
            "healthy": healthy,
            "reasons": reasons,
        }

        os.makedirs(STATUS_DIR, exist_ok=True)

        with open(
            os.path.join(STATUS_DIR, f"{run_id}.json"),
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(status_record, f, indent=2)

        with open(STATUS_LATEST, "w", encoding="utf-8") as f:
            json.dump(status_record, f, indent=2)

        print(json.dumps(status_record, indent=2))

        return status_record

    # ========================================================
    # 6. NOTIFY
    #
    # Always runs; re-raises to fail the DAG run when the status
    # record says unhealthy, so the run still produces ONE
    # unambiguous success/failure even though quality_check itself
    # uses ALL_DONE.
    # ========================================================

    @task(trigger_rule=TriggerRule.ALL_DONE)
    def notify(status_record):

        if status_record["healthy"]:

            print(
                f"PIPELINE OK | run_id={status_record['run_id']} | "
                f"rows_published={status_record['rows_published']} | "
                f"as_of={status_record['as_of']}"
            )

        else:

            print(
                f"PIPELINE UNHEALTHY | run_id={status_record['run_id']} | "
                f"reasons={status_record['reasons']}"
            )

            raise RuntimeError(
                f"Pipeline run {status_record['run_id']} unhealthy: "
                f"{status_record['reasons']}"
            )

    # ========================================================
    # DEPENDENCIES
    # ========================================================

    ingested = ingest()
    validated = validate(ingested)

    validated >> spark_process >> load_warehouse

    checked = quality_check(validated)

    load_warehouse >> checked

    notify(checked)


de7_end_to_end()
