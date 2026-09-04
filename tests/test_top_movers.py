"""
C5 top-movers additivity test, against the REAL FastAPI app
(FastAPI/main.py), not a standalone router. Existing endpoints
(API1-API5) are exercised unchanged elsewhere - this only proves the
new /network/top-movers endpoint is additive and correctly ordered.

Skipped (not failed) if the MySQL warehouse from
SQL_load_verify/load_to_sql.py is not reachable in this environment.
"""

import sys
from pathlib import Path

import pytest

FASTAPI_DIR = Path(__file__).resolve().parent.parent / "FastAPI"
if str(FASTAPI_DIR) not in sys.path:
    sys.path.insert(0, str(FASTAPI_DIR))

try:
    from fastapi.testclient import TestClient
    from main import app  # noqa: E402
    client = TestClient(app)
except Exception as exc:  # pragma: no cover - environment dependent
    # This environment's starlette build needs an extra test-client
    # dependency that was not already installed; skip rather than install
    # an unverified package on the user's behalf.
    client = None
    _import_error = exc


def _first_reachable_response():
    if client is None:
        pytest.skip(f"fastapi TestClient unavailable in this environment: {_import_error}")
    try:
        return client.get("/network/summary")
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"warehouse DB not reachable: {exc}")


def test_top_movers_is_additive_and_ordered():
    probe = _first_reachable_response()
    if probe.status_code != 200:
        pytest.skip(f"warehouse not populated: /network/summary -> {probe.status_code}")

    r = client.get("/network/top-movers?limit=10")
    assert r.status_code == 200

    body = r.json()
    assert set(body) == {"as_of", "top_movers"}

    growths = [m["growth"] for m in body["top_movers"]]
    assert growths == sorted(growths, reverse=True)

    for mover in body["top_movers"]:
        assert {"grid_id", "current_activity", "baseline_activity", "growth", "label"} <= set(mover)
        assert "congest" not in mover["label"].lower()

    # Existing API1 contract is untouched by this addition.
    summary = client.get("/network/summary")
    assert summary.status_code == 200
    assert set(summary.json()) == {
        "total_activity", "active_grids", "peak_hour", "top_grid", "as_of"
    }
