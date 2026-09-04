"""
C5 — Top Movers endpoint (implemented AFTER plan approval — see
docs/plans/c5_top_movers_plan.md).

Additive API change: new router, no existing response shape touched.
Reuses the ML2 baseline (analytics.grid_features.baseline_total_activity),
which already EXCLUDES the current interval — no third baseline
implementation (the plan revision the learner insisted on).
"""

from fastapi import APIRouter, Query

# Shared services built in Phase 4 (api/services/): the same DB access layer
# API1–API6 use. Nothing here reads data/raw or data/processed directly.
from api.services.warehouse import query_analytics  # DE7 analytics layer
from api.services.as_of import resolve_as_of        # AS_OF convention (CLAUDE.md rule 6)

router = APIRouter(prefix="/network", tags=["network"])

SQL = """
-- Grain: one row per grid per hourly timestamp (CLAUDE.md rules 1–2).
-- Baseline from the ML2 feature table; excludes the current interval.
SELECT s.grid_id,
       s.total_activity              AS current_activity,   -- proportional activity measure, not counts/MB
       f.baseline_total_activity     AS baseline_activity,
       s.total_activity / NULLIF(f.baseline_total_activity, 0) AS growth
FROM   analytics.hourly_grid_summary s
JOIN   analytics.grid_features f
       ON f.grid_id = s.grid_id AND f.feature_timestamp = s.timestamp
WHERE  s.timestamp = :as_of
ORDER  BY growth DESC NULLS LAST
LIMIT  :limit
"""


@router.get("/top-movers")
def top_movers(limit: int = Query(10, ge=1, le=50), as_of: str | None = None):
    """Top grids by activity growth vs baseline in the current reporting window."""
    window = resolve_as_of(as_of)
    rows = query_analytics(SQL, {"as_of": window, "limit": limit})
    return {
        "as_of": window,
        "top_movers": [
            {
                "grid_id": r["grid_id"],
                "current_activity": r["current_activity"],
                "baseline_activity": r["baseline_activity"],
                "growth": r["growth"],
                # NOC-facing label: attention language only — never "congested"
                # (CLAUDE.md rule 4; same language rule as the ML6 top-twenty report).
                "label": "sharp increase vs baseline",
            }
            for r in rows
        ],
    }
