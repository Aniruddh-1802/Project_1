"""
DE3 - Airflow DAG: launch the Spark processing job.

Runs the EXISTING spark/telecom_pipeline.py (a real, previously-run job
built from ingetision_module.py, spark_cleaning.py, spark_aggregation.py,
spark_geo_enrichment.py and output_layer.py) rather than reimplementing
its logic in the DAG. See Data Engineering/_superseded/README.md for why.

Airflow runs inside WSL Ubuntu-26.04, which has neither Java nor pyspark.
Spark therefore runs on the Windows side: the BashOperator calls the
Windows interpreter through WSL interop and hands it the Windows CLI
invocation of telecom_pipeline.py.

Check tasks stay in WSL and use /mnt/c paths for the same folders.
"""

import os

from datetime import datetime

from airflow.sdk import dag, task
from airflow.providers.standard.operators.bash import BashOperator


# ============================================================
# ABSOLUTE PATHS
# ============================================================

# --- WSL view (used by the Python @task functions) ---

PROJECT_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1"

RAW_PATH = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/raw"

# telecom_pipeline.py writes these three outputs under --output
PROCESSED_ACTIVITY_PATH = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/processed/activity"

HOURLY_SUMMARY_PATH = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/analytics/hourly_grid_summary"

DASHBOARD_SUMMARY_PATH = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/analytics/dashboard_summary"

REFERENCE_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/reference"

REFERENCE_GEOJSON = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/reference/milano-grid.geojson"

# --- Windows side (used by the BashOperator) ---

WINDOWS_PYTHON = "/mnt/c/Users/aniruddh.singh/AppData/Local/Programs/Python/Python311/python.exe"

WINDOWS_SPARK_SCRIPT = "C:/Users/aniruddh.singh/Documents/Project_1/spark/telecom_pipeline.py"

WINDOWS_INPUT = "C:/Users/aniruddh.singh/Documents/Project_1/data/raw"
WINDOWS_OUTPUT = "C:/Users/aniruddh.singh/Documents/Project_1/data"
WINDOWS_REFERENCE = "C:/Users/aniruddh.singh/Documents/Project_1/data/reference"


# ============================================================
# DAG
# ============================================================

@dag(
    dag_id="de3_spark_processing",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["DE3", "spark", "processing"],
)
def de3_spark_processing():

    # ========================================================
    # 1. CHECK RAW INPUT
    # ========================================================

    @task
    def check_raw_input():

        if not os.path.exists(RAW_PATH):
            raise FileNotFoundError(
                f"Raw directory does not exist: {RAW_PATH}"
            )

        csv_files = [
            file
            for file in os.listdir(RAW_PATH)
            if file.lower().endswith(".csv")
        ]

        if not csv_files:
            raise FileNotFoundError(
                f"No CSV files found in raw zone: {RAW_PATH}"
            )

        if not os.path.exists(REFERENCE_GEOJSON):
            raise FileNotFoundError(
                f"Static reference file is missing: {REFERENCE_GEOJSON}"
            )

        print(
            f"Found {len(csv_files)} raw CSV file(s)."
        )

        for file in csv_files:
            print(f"  - {file}")

    # ========================================================
    # 2. RUN SPARK PROCESSING
    #
    # Windows interpreter, existing SP-phase script. --input reads
    # data/raw (DE2's validated output); --reference is a directory,
    # not the file itself - telecom_pipeline.py appends the filename.
    # ========================================================

    spark_job = BashOperator(
        task_id="run_spark_processing",

        bash_command=(
            f'"{WINDOWS_PYTHON}" "{WINDOWS_SPARK_SCRIPT}" '
            f'--input "{WINDOWS_INPUT}" '
            f'--output "{WINDOWS_OUTPUT}" '
            f'--reference "{WINDOWS_REFERENCE}"'
        ),
    )

    # ========================================================
    # 3. VERIFY OUTPUTS
    # ========================================================

    @task
    def verify_outputs():

        if not os.path.exists(PROCESSED_ACTIVITY_PATH):
            raise FileNotFoundError(
                f"Processed activity output was not created: {PROCESSED_ACTIVITY_PATH}"
            )

        if not os.path.exists(HOURLY_SUMMARY_PATH):
            raise FileNotFoundError(
                f"Hourly grid summary was not created: {HOURLY_SUMMARY_PATH}"
            )

        if not os.path.exists(DASHBOARD_SUMMARY_PATH):
            raise FileNotFoundError(
                f"Dashboard summary was not created: {DASHBOARD_SUMMARY_PATH}"
            )

        print("Processed activity output exists.")
        print("Hourly grid summary exists.")
        print("Dashboard summary exists.")
        print("DE3 Spark processing completed successfully.")

    # ========================================================
    # DEPENDENCIES
    # ========================================================

    check = check_raw_input()

    check >> spark_job

    spark_job >> verify_outputs()


# ============================================================
# DAG INSTANCE
# ============================================================

de3_spark_processing()
