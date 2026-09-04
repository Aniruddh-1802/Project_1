"""C5 tests (new, per approved plan). Existing API snapshot tests in
tests/test_api.py are untouched — that is the additivity proof."""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AS_OF = "2013-11-07T18:00:00"  # AS_OF convention — CLAUDE.md rule 6


def test_top_movers_shape_and_ordering():
    r = client.get(f"/network/top-movers?limit=10&as_of={AS_OF}")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"as_of", "top_movers"}
    growths = [m["growth"] for m in body["top_movers"]]
    assert growths == sorted(growths, reverse=True)
    for m in body["top_movers"]:
        assert {"grid_id", "current_activity", "baseline_activity", "growth", "label"} <= set(m)
        assert "congest" not in m["label"].lower()  # CLAUDE.md rule 4


def test_top_movers_baseline_excludes_current_interval():
    # Baseline comes from ML2's grid_features; assert it differs from the
    # current interval value for a grid with a known spike (Grid 4821 fixture).
    r = client.get(f"/network/top-movers?limit=50&as_of={AS_OF}").json()
    spike = next(m for m in r["top_movers"] if m["grid_id"] == 4821)
    assert spike["baseline_activity"] != spike["current_activity"]
