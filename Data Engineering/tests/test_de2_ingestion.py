"""
DE2 test suite - covers the valid path, and each invalid path named
in the trainer guide's DE2 and DE8 labs: schema mismatch, malformed
timestamp, missing CellID, negative activity value, non-numeric
activity value, and a duplicate/rerun of an already-accepted file.

Run with:
    python -m pytest "Data Engineering\\tests\\test_de2_ingestion.py" -v
"""

import csv
import importlib
import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

import de2_ingestion as de2


HEADER = "datetime,CellID,countrycode,smsin,smsout,callin,callout,internet\n"

VALID_ROW = "2013-11-01 00:00:00,1,39,1.0,2.0,3.0,4.0,5.0\n"


@pytest.fixture
def de2_env(tmp_path, monkeypatch):
    """Point every de2_ingestion path constant at an isolated tmp tree."""

    monkeypatch.setattr(de2, "LANDING_DIR", str(tmp_path / "landing"))
    monkeypatch.setattr(de2, "RAW_DIR", str(tmp_path / "raw"))
    monkeypatch.setattr(de2, "REJECTED_DIR", str(tmp_path / "rejected"))
    monkeypatch.setattr(de2, "REFERENCE_DIR", str(tmp_path / "reference"))
    monkeypatch.setattr(de2, "LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(
        de2, "INGESTION_LOG", str(tmp_path / "logs" / "ingestion_log.csv")
    )

    de2.create_directories()

    return de2


def _write_landing_file(env, filename, content):

    path = os.path.join(env.LANDING_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return path


def _ingest_all(env):
    """Run detect -> validate -> route for every file currently in landing."""

    results = []

    for file_path in env.detect_files():

        schema_ok, schema_reason = env.validate_schema(file_path)

        if not schema_ok:
            env.route_file(file_path, "REJECTED", schema_reason, 0)
            results.append(("REJECTED", schema_reason))
            continue

        quality_ok, rows, quality_reason = env.validate_minimum_quality(file_path)

        status = "VALID" if quality_ok else "REJECTED"

        env.route_file(file_path, status, quality_reason, rows)

        results.append((status, quality_reason))

    return results


def _log_rows(env):

    with open(env.INGESTION_LOG, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ============================================================
# VALID PATH
# ============================================================

def test_valid_file_lands_in_raw_with_audit_record(de2_env):

    _write_landing_file(
        de2_env,
        "sms-call-internet-mi-2013-11-01.csv",
        HEADER + VALID_ROW
    )

    results = _ingest_all(de2_env)

    assert results == [("VALID", "Minimum quality checks passed")]

    assert os.path.exists(
        os.path.join(de2_env.RAW_DIR, "sms-call-internet-mi-2013-11-01.csv")
    )

    log_rows = _log_rows(de2_env)
    assert len(log_rows) == 1
    assert log_rows[0]["status"] == "VALID"
    assert log_rows[0]["row_count"] == "1"


# ============================================================
# SCHEMA MISMATCH (missing / renamed column)
# ============================================================

def test_missing_column_is_rejected_with_named_reason(de2_env):

    bad_header = "datetime,CellID,countrycode,smsin,smsout,callin,callout\n"  # no 'internet'

    _write_landing_file(
        de2_env,
        "sms-call-internet-mi-2013-11-02.csv",
        bad_header + "2013-11-02 00:00:00,1,39,1.0,2.0,3.0,4.0\n"
    )

    results = _ingest_all(de2_env)

    assert results[0][0] == "REJECTED"
    assert "Schema mismatch" in results[0][1]

    assert os.path.exists(
        os.path.join(de2_env.REJECTED_DIR, "sms-call-internet-mi-2013-11-02.csv")
    )
    assert not os.path.exists(
        os.path.join(de2_env.RAW_DIR, "sms-call-internet-mi-2013-11-02.csv")
    )


# ============================================================
# MALFORMED TIMESTAMP
# ============================================================

def test_malformed_timestamp_is_rejected(de2_env):

    _write_landing_file(
        de2_env,
        "sms-call-internet-mi-2013-11-03.csv",
        HEADER + "NOT-A-DATE,1,39,1.0,2.0,3.0,4.0,5.0\n"
    )

    results = _ingest_all(de2_env)

    assert results[0][0] == "REJECTED"
    assert "Malformed timestamp" in results[0][1]


# ============================================================
# MISSING CellID
# ============================================================

def test_missing_grid_id_is_rejected(de2_env):

    _write_landing_file(
        de2_env,
        "sms-call-internet-mi-2013-11-04.csv",
        HEADER + "2013-11-04 00:00:00,,39,1.0,2.0,3.0,4.0,5.0\n"
    )

    results = _ingest_all(de2_env)

    assert results[0][0] == "REJECTED"
    assert "Missing CellID" in results[0][1]


# ============================================================
# NEGATIVE ACTIVITY VALUE
# ============================================================

def test_negative_activity_value_is_rejected(de2_env):

    _write_landing_file(
        de2_env,
        "sms-call-internet-mi-2013-11-05.csv",
        HEADER + "2013-11-05 00:00:00,1,39,-1.0,2.0,3.0,4.0,5.0\n"
    )

    results = _ingest_all(de2_env)

    assert results[0][0] == "REJECTED"
    assert "Negative activity values" in results[0][1]


# ============================================================
# NON-NUMERIC ACTIVITY VALUE
# ============================================================

def test_non_numeric_activity_value_is_rejected(de2_env):

    _write_landing_file(
        de2_env,
        "sms-call-internet-mi-2013-11-06.csv",
        HEADER + "2013-11-06 00:00:00,1,39,abc,2.0,3.0,4.0,5.0\n"
    )

    results = _ingest_all(de2_env)

    assert results[0][0] == "REJECTED"
    assert "Non-numeric values" in results[0][1]


# ============================================================
# EMPTY FILE
# ============================================================

def test_empty_file_is_rejected(de2_env):

    _write_landing_file(
        de2_env,
        "sms-call-internet-mi-2013-11-07.csv",
        HEADER
    )

    results = _ingest_all(de2_env)

    assert results[0][0] == "REJECTED"
    assert "zero data rows" in results[0][1]


# ============================================================
# DUPLICATE / RERUN (DE2 + DE8)
# ============================================================

def test_rerun_on_already_accepted_file_does_not_overwrite_raw(de2_env):

    filename = "sms-call-internet-mi-2013-11-08.csv"

    _write_landing_file(de2_env, filename, HEADER + VALID_ROW)
    _ingest_all(de2_env)

    raw_path = os.path.join(de2_env.RAW_DIR, filename)

    with open(raw_path, encoding="utf-8") as f:
        original_content = f.read()

    # A file with the same name arrives again, with different content.
    _write_landing_file(
        de2_env,
        filename,
        HEADER + "2099-01-01 00:00:00,999,39,9.0,9.0,9.0,9.0,9.0\n"
    )

    # route_file() reclassifies VALID -> DUPLICATE internally when the
    # filename already exists in raw/, so the outcome is checked via
    # the audit log below, not via _ingest_all's pre-route status.
    _ingest_all(de2_env)

    with open(raw_path, encoding="utf-8") as f:
        assert f.read() == original_content, "raw/ must stay immutable on rerun"

    rejected_files = os.listdir(de2_env.REJECTED_DIR)
    assert len(rejected_files) == 1

    log_rows = _log_rows(de2_env)
    assert [r["status"] for r in log_rows] == ["VALID", "DUPLICATE"]


def test_reference_geojson_is_not_touched_by_ingestion(de2_env):

    os.makedirs(de2_env.REFERENCE_DIR, exist_ok=True)

    geojson_path = os.path.join(de2_env.REFERENCE_DIR, "milano-grid.geojson")

    with open(geojson_path, "w", encoding="utf-8") as f:
        f.write('{"type": "FeatureCollection", "features": []}')

    _write_landing_file(
        de2_env,
        "sms-call-internet-mi-2013-11-09.csv",
        HEADER + VALID_ROW
    )

    _ingest_all(de2_env)

    # The GeoJSON is not a landing candidate and must be untouched.
    assert os.path.exists(geojson_path)
    with open(geojson_path, encoding="utf-8") as f:
        assert f.read() == '{"type": "FeatureCollection", "features": []}'
