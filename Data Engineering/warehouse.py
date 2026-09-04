"""
DE6 - Airflow DAG: build and load the network warehouse.

Same split as DE3: the check tasks run in WSL against /mnt/c paths,
while the Spark + MySQL load runs through the Windows interpreter,
because Java, pyspark and the MySQL client libraries all live on the
Windows side.
"""

import logging
import os

from datetime import datetime

from airflow.sdk import dag, task
from airflow.providers.standard.operators.bash import BashOperator


# ============================================================
# ABSOLUTE PATHS
# ============================================================

# --- WSL view (used by the Python @task functions) ---

PROJECT_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1"

ANALYTICS_PATH = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/analytics/hourly_grid_summary"

# --- Windows side (used by the BashOperator) ---

WINDOWS_PYTHON = "/mnt/c/Users/aniruddh.singh/AppData/Local/Programs/Python/Python311/python.exe"

WINDOWS_WAREHOUSE_SCRIPT = "C:/Users/aniruddh.singh/Documents/Project_1/Data Engineering/de6_warehouse.py"


@dag(
    dag_id="de6_network_warehouse",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["DE6", "warehouse", "mysql", "spark"]
)
def de6_network_warehouse():

    @task
    def check_analytics_output():

        logging.info(
            f"Checking analytics output: {ANALYTICS_PATH}"
        )

        if not os.path.exists(ANALYTICS_PATH):

            raise FileNotFoundError(
                f"Analytics output does not exist: "
                f"{ANALYTICS_PATH}"
            )

        parquet_files = []

        for root, directories, files in os.walk(
            ANALYTICS_PATH
        ):

            for file in files:

                if file.endswith(".parquet"):

                    parquet_files.append(
                        os.path.join(root, file)
                    )

        if not parquet_files:

            raise FileNotFoundError(
                "No Parquet files found in analytics output."
            )

        logging.info(
            f"Found {len(parquet_files)} Parquet files."
        )

    run_warehouse = BashOperator(
        task_id="run_de6_warehouse",

        bash_command=(
            'set -e\n'
            'echo "======================================"\n'
            'echo "Starting DE6 Warehouse Processing"\n'
            'echo "======================================"\n'
            f'"{WINDOWS_PYTHON}" "{WINDOWS_WAREHOUSE_SCRIPT}"\n'
            'echo "======================================"\n'
            'echo "DE6 Warehouse Processing Completed"\n'
            'echo "======================================"\n'
        )
    )

    @task
    def warehouse_complete():

        logging.info(
            "DE6 warehouse pipeline completed successfully."
        )

    check = check_analytics_output()

    check >> run_warehouse >> warehouse_complete()


de6_network_warehouse()
