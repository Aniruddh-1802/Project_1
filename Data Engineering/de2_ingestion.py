
import csv
import logging
import os
import re
import shutil
from datetime import datetime, timezone

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# ABSOLUTE PATHS
#
# This module runs in two different places:
#
#   * directly on Windows, via
#       python "C:\Users\aniruddh.singh\Documents\Project_1\Data Engineering\de2_ingestion.py"
#
#   * imported by raw_ingestion_dag.py, which Airflow executes
#     inside WSL Ubuntu-26.04 (the airflow-env virtualenv)
#
# Both sets below address exactly the same folders on disk:
# Windows reaches them as C:\... and WSL reaches them as /mnt/c/...
# ------------------------------------------------------------

if os.name == "nt":

    PROJECT_ROOT = r"C:\Users\aniruddh.singh\Documents\Project_1"

    LANDING_DIR = r"C:\Users\aniruddh.singh\Documents\Project_1\data\landing"
    RAW_DIR = r"C:\Users\aniruddh.singh\Documents\Project_1\data\raw"
    REJECTED_DIR = r"C:\Users\aniruddh.singh\Documents\Project_1\data\rejected"
    REFERENCE_DIR = r"C:\Users\aniruddh.singh\Documents\Project_1\data\reference"
    LOG_DIR = r"C:\Users\aniruddh.singh\Documents\Project_1\logs"

    INGESTION_LOG = r"C:\Users\aniruddh.singh\Documents\Project_1\logs\ingestion_log.csv"

    REFERENCE_GEOJSON = r"C:\Users\aniruddh.singh\Documents\Project_1\data\reference\milano-grid.geojson"

else:

    PROJECT_ROOT = "/mnt/c/Users/aniruddh.singh/Documents/Project_1"

    LANDING_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/landing"
    RAW_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/raw"
    REJECTED_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/rejected"
    REFERENCE_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/reference"
    LOG_DIR = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/logs"

    INGESTION_LOG = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/logs/ingestion_log.csv"

    REFERENCE_GEOJSON = "/mnt/c/Users/aniruddh.singh/Documents/Project_1/data/reference/milano-grid.geojson"


# Daily activity file pattern
FILE_PATTERN = re.compile(
    r"^sms-call-internet-mi-\d{4}-\d{2}-\d{2}\.csv$"
)


# Canonical source schema
EXPECTED_COLUMNS = [
    "datetime",
    "CellID",
    "countrycode",
    "smsin",
    "smsout",
    "callin",
    "callout",
    "internet"
]


ACTIVITY_COLUMNS = [
    "smsin",
    "smsout",
    "callin",
    "callout",
    "internet"
]


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ============================================================
# DIRECTORY SETUP
# ============================================================

def create_directories():

    os.makedirs(LANDING_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(REJECTED_DIR, exist_ok=True)
    os.makedirs(REFERENCE_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


# ============================================================
# 1. DETECT FILES
# ============================================================

def detect_files():

    logging.info(
        f"Scanning landing zone: {LANDING_DIR}"
    )

    detected_files = []

    if not os.path.exists(LANDING_DIR):
        raise FileNotFoundError(
            f"Landing directory does not exist: {LANDING_DIR}"
        )

    for filename in os.listdir(LANDING_DIR):

        file_path = os.path.join(
            LANDING_DIR,
            filename
        )

        # Ignore directories
        if not os.path.isfile(file_path):
            continue

        # Only detect daily activity CSVs
        if FILE_PATTERN.match(filename):
            detected_files.append(file_path)

    logging.info(
        f"Detected {len(detected_files)} daily activity file(s)"
    )

    for file_path in detected_files:
        logging.info(
            f"Detected: {os.path.basename(file_path)}"
        )

    return detected_files


# ============================================================
# 2. VALIDATE SCHEMA
# ============================================================

def validate_schema(file_path):

    filename = os.path.basename(file_path)

    try:

        # Read only the header first
        df = pd.read_csv(
            file_path,
            nrows=0
        )

        actual_columns = list(df.columns)

        if actual_columns != EXPECTED_COLUMNS:

            return False, (
                "Schema mismatch. "
                f"Expected columns: {EXPECTED_COLUMNS}; "
                f"Found: {actual_columns}"
            )

        return True, "Schema valid"

    except Exception as exc:

        return False, (
            f"Unable to read CSV schema: {exc}"
        )


# ============================================================
# 3. VALIDATE MINIMUM QUALITY
# ============================================================

def validate_minimum_quality(file_path):

    filename = os.path.basename(file_path)

    try:

        df = pd.read_csv(file_path)

        row_count = len(df)

        if row_count == 0:

            return False, row_count, (
                "File contains zero data rows"
            )

        # ----------------------------------------------------
        # Timestamp validation
        # ----------------------------------------------------

        parsed_timestamps = pd.to_datetime(
            df["datetime"],
            errors="coerce"
        )

        malformed_timestamps = (
            parsed_timestamps.isna().sum()
        )

        if malformed_timestamps > 0:

            return False, row_count, (
                f"Malformed timestamp values: "
                f"{malformed_timestamps}"
            )

        # ----------------------------------------------------
        # Grid ID validation
        # ----------------------------------------------------

        null_grid_ids = df["CellID"].isna().sum()

        if null_grid_ids > 0:

            return False, row_count, (
                f"Missing CellID values: "
                f"{null_grid_ids}"
            )

        # ----------------------------------------------------
        # Activity value validation
        # ----------------------------------------------------

        for column in ACTIVITY_COLUMNS:

            numeric_values = pd.to_numeric(
                df[column],
                errors="coerce"
            )

            invalid_numeric = (
                numeric_values.isna()
                & df[column].notna()
            ).sum()

            if invalid_numeric > 0:

                return False, row_count, (
                    f"Non-numeric values found "
                    f"in activity column '{column}': "
                    f"{invalid_numeric}"
                )

            negative_values = (
                numeric_values < 0
            ).sum()

            if negative_values > 0:

                return False, row_count, (
                    f"Negative activity values found "
                    f"in '{column}': "
                    f"{negative_values}"
                )

        return True, row_count, "Minimum quality checks passed"

    except Exception as exc:

        return False, 0, (
            f"Quality validation failed: {exc}"
        )


# ============================================================
# 4. WRITE INGESTION METADATA
# ============================================================

def write_metadata(
    filename,
    status,
    row_count,
    reason
):

    os.makedirs(
        LOG_DIR,
        exist_ok=True
    )

    metadata = {
        "filename": filename,
        "status": status,
        "row_count": row_count,
        "reason": reason,
        "processed_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    file_exists = os.path.exists(
        INGESTION_LOG
    )

    with open(
        INGESTION_LOG,
        "a",
        newline="",
        encoding="utf-8"
    ) as log_file:

        writer = csv.DictWriter(
            log_file,
            fieldnames=[
                "filename",
                "status",
                "row_count",
                "reason",
                "processed_at"
            ]
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(metadata)

    logging.info(
        f"Ingestion metadata written: "
        f"{filename} -> {status}"
    )


# ============================================================
# 4b. DUPLICATE DETECTION
# ============================================================
#
# raw/ is immutable: once a filename has been accepted there, a later
# file with the same name must never silently overwrite it. Rerunning
# ingestion on an already-processed file is therefore a defined,
# logged outcome (DUPLICATE -> rejected), not a silent overwrite.
# ============================================================

def is_duplicate(filename):

    return os.path.exists(
        os.path.join(RAW_DIR, filename)
    )


def _non_colliding_path(directory, filename):

    destination = os.path.join(directory, filename)

    if not os.path.exists(destination):
        return destination

    stem, ext = os.path.splitext(filename)

    suffix = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%S%fZ")

    return os.path.join(
        directory,
        f"{stem}.dup-{suffix}{ext}"
    )


# ============================================================
# 5. ROUTE FILE
# ============================================================

def route_file(
    file_path,
    status,
    reason,
    row_count
):

    filename = os.path.basename(
        file_path
    )

    if status == "VALID" and is_duplicate(filename):

        status = "DUPLICATE"

        reason = (
            f"Duplicate ingestion attempt: '{filename}' already "
            f"present in raw/ from a prior run. Original left "
            f"untouched; this copy quarantined to rejected/."
        )

        destination = _non_colliding_path(
            REJECTED_DIR,
            filename
        )

        shutil.move(
            file_path,
            destination
        )

        logging.warning(
            f"DUPLICATE -> rejected: {filename} | {reason}"
        )

    elif status == "VALID":

        destination = os.path.join(
            RAW_DIR,
            filename
        )

        shutil.move(
            file_path,
            destination
        )

        logging.info(
            f"VALID -> raw: {filename}"
        )

    else:

        destination = _non_colliding_path(
            REJECTED_DIR,
            filename
        )

        shutil.move(
            file_path,
            destination
        )

        logging.warning(
            f"INVALID -> rejected: "
            f"{filename} | {reason}"
        )

    write_metadata(
        filename=filename,
        status=status,
        row_count=row_count,
        reason=reason
    )


# ============================================================
# MAIN INGESTION FLOW
# ============================================================

def run_ingestion():

    create_directories()

    detected_files = detect_files()

    if not detected_files:

        logging.info(
            "No daily activity files found."
        )

        return

    for file_path in detected_files:

        filename = os.path.basename(
            file_path
        )

        logging.info(
            f"Processing: {filename}"
        )

        # ----------------------------------------------------
        # Schema validation
        # ----------------------------------------------------

        schema_valid, schema_reason = (
            validate_schema(file_path)
        )

        if not schema_valid:

            route_file(
                file_path=file_path,
                status="REJECTED",
                reason=schema_reason,
                row_count=0
            )

            continue

        # ----------------------------------------------------
        # Minimum quality validation
        # ----------------------------------------------------

        quality_valid, row_count, quality_reason = (
            validate_minimum_quality(file_path)
        )

        if not quality_valid:

            route_file(
                file_path=file_path,
                status="REJECTED",
                reason=quality_reason,
                row_count=row_count
            )

            continue

        # ----------------------------------------------------
        # Valid file
        # ----------------------------------------------------

        route_file(
            file_path=file_path,
            status="VALID",
            reason=quality_reason,
            row_count=row_count
        )


if __name__ == "__main__":

    run_ingestion()

