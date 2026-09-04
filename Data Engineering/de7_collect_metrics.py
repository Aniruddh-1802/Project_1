"""
DE7 helper - runs on Windows (needs pandas/pyarrow/pymysql, all of
which live there, not in the WSL airflow-env).

Called by the quality_check task of the DE7 end-to-end DAG. Reads
data already written by DE3 (spark/telecom_pipeline.py) and DE6
(de6_warehouse.py) and prints ONE JSON object to stdout - nothing
else - so the caller can parse it directly.

    python de7_collect_metrics.py --raw-files a.csv,b.csv
"""

import argparse
import json
import os

import pandas as pd
import pyarrow.parquet as pq
import pymysql


RAW_DIR = r"C:\Users\aniruddh.singh\Documents\Project_1\data\raw"

ANALYTICS_PATH = r"C:\Users\aniruddh.singh\Documents\Project_1\data\analytics\hourly_grid_summary"

MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_DATABASE = "telecom_warehouse_de6"
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"

ACTIVITY_COLUMNS = ["smsin", "smsout", "callin", "callout", "internet"]


def count_nulls_in_raw_files(filenames):

    total_nulls = 0

    for filename in filenames:

        path = os.path.join(RAW_DIR, filename)

        if not os.path.exists(path):
            continue

        df = pd.read_csv(path, usecols=lambda c: c in ACTIVITY_COLUMNS)

        total_nulls += int(df.isna().sum().sum())

    return total_nulls


def analytics_as_of():

    if not os.path.exists(ANALYTICS_PATH):
        return None

    table = pq.ParquetDataset(ANALYTICS_PATH).read(columns=["timestamp"])

    max_ts = table.column("timestamp").combine_chunks().to_pandas().max()

    if pd.isna(max_ts):
        return None

    return max_ts.isoformat()


def warehouse_row_counts():

    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
        )
    except Exception as exc:
        return {"error": str(exc)}

    try:
        cursor = connection.cursor()

        counts = {}

        for table_name in ["dim_grid", "dim_time", "fact_network_activity"]:

            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            counts[table_name] = cursor.fetchone()[0]

        return counts

    finally:
        connection.close()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--raw-files",
        default="",
        help="Comma-separated filenames (in data/raw) accepted this run"
    )

    args = parser.parse_args()

    filenames = [f for f in args.raw_files.split(",") if f]

    result = {
        "nulls_handled": count_nulls_in_raw_files(filenames),
        "as_of": analytics_as_of(),
        "warehouse_row_counts": warehouse_row_counts(),
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
