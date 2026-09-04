"""
C12 — Network Intelligence MCP Server
=====================================
Exposes the platform to Claude via MCP. File name per the guide's canonical
Repository Structure: mcp/network_mcp_server.py.

HARD RULE (Trainer Focus): the MCP layer contains NO business logic. Every
tool is a THIN wrapper over an endpoint that already exists (API1–API6).
It must not compute, aggregate, threshold or interpret anything. If a
calculation seems needed here, the endpoint is missing — add it to api/
instead (exactly how the C5 top-movers endpoint came to exist).

Acceptance criteria this design satisfies:
  - every MCP tool result matches the corresponding direct API call exactly
    (we return the endpoint's JSON verbatim);
  - no aggregation/threshold/interpretation logic in this layer.
"""

import os
import re

import requests
from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("NETWORK_API_BASE", "http://localhost:8000")
TIMEOUT = 10

mcp = FastMCP("network-intelligence")

# --- validation & basic security constraints (Activity 6) -------------------
GRID_ID_MAX = 10000          # the Milan grid is 100×100 cells (milano-grid.geojson)
AS_OF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")  # AS_OF convention


def _validate_grid(grid_id: int) -> None:
    if not (1 <= grid_id <= GRID_ID_MAX):
        raise ValueError(f"grid_id must be 1..{GRID_ID_MAX} (Milan grid cellId range)")


def _validate_as_of(as_of: str | None) -> None:
    if as_of is not None and not AS_OF_RE.match(as_of):
        raise ValueError("as_of must be an ISO hourly timestamp (AS_OF convention)")


def _get(path: str, params: dict | None = None) -> dict:
    """Pass-through only. Verbatim endpoint JSON; errors surfaced, never masked
    (the C2 rule: report the gap, don't substitute an estimate)."""
    r = requests.get(f"{API_BASE}{path}", params=params or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# --- tools: exact mapping from the lab prompt --------------------------------

@mcp.tool()
def network_summary(as_of: str | None = None) -> dict:
    """Network-wide activity summary. Thin wrapper: GET /network/summary (API1)."""
    _validate_as_of(as_of)
    return _get("/network/summary", {"as_of": as_of})


@mcp.tool()
def grid_activity(grid_id: int, as_of: str | None = None) -> dict:
    """Hourly activity for one grid. Thin wrapper: GET /network/grid/{grid_id} (API2)."""
    _validate_grid(grid_id); _validate_as_of(as_of)
    return _get(f"/network/grid/{grid_id}", {"as_of": as_of})


@mcp.tool()
def grid_features(grid_id: int) -> dict:
    """ML2 engineered features. Thin wrapper: GET /network/grid/{grid_id}/features (API4)."""
    _validate_grid(grid_id)
    return _get(f"/network/grid/{grid_id}/features")


@mcp.tool()
def grid_location(grid_id: int) -> dict:
    """Geographic location in Milan (joined on properties.cellId — CLAUDE.md rule 5).
    Thin wrapper: GET /network/grid/{grid_id}/location (API6)."""
    _validate_grid(grid_id)
    return _get(f"/network/grid/{grid_id}/location")


@mcp.tool()
def hotspots(limit: int = 20, severity: str | None = None, as_of: str | None = None) -> dict:
    """Top attention grids (includes ML4/ML6 anomaly scores; the ranking lives in
    the API, not here). Thin wrapper: GET /network/hotspots (API3)."""
    if not (1 <= limit <= 100):
        raise ValueError("limit must be 1..100")
    _validate_as_of(as_of)
    return _get("/network/hotspots", {"limit": limit, "severity": severity, "as_of": as_of})


@mcp.tool()
def alerts(limit: int = 10, severity: str | None = None, as_of: str | None = None) -> dict:
    """NP3 rule alerts. Thin wrapper: GET /network/alerts (API3).
    Signature matches the real endpoint (FastAPI/routers.py) exactly —
    it has no grid_id filter server-side, so this tool must not invent one."""
    if not (1 <= limit <= 100):
        raise ValueError("limit must be 1..100")
    _validate_as_of(as_of)
    return _get("/network/alerts", {"limit": limit, "severity": severity, "as_of": as_of})


@mcp.tool()
def pipeline_status() -> dict:
    """Pipeline health — 'can I trust this?'. Thin wrapper: GET /pipeline/status
    (API6, serving the DE7 status record from logs/)."""
    return _get("/pipeline/status")


@mcp.tool()
def top_movers(limit: int = 10, as_of: str | None = None) -> dict:
    """Grids with the sharpest activity increase vs their ML2 baseline
    (additive C5 feature). Thin wrapper: GET /network/top-movers."""
    if not (1 <= limit <= 50):
        raise ValueError("limit must be 1..50")
    _validate_as_of(as_of)
    return _get("/network/top-movers", {"limit": limit, "as_of": as_of})


if __name__ == "__main__":
    # Register in Claude Code:  claude mcp add network-intelligence -- python mcp/network_mcp_server.py
    # Lab conversation to verify (tool calls visible in the log):
    #   1. "Which grids have the highest anomaly scores?"      -> hotspots
    #   2. "Check whether their data pipeline completed successfully." -> pipeline_status
    mcp.run(transport="stdio")
