# C5 — Approved Plan: "Top Movers" NOC Feature (Plan Mode artifact)

**Requirement:** show the top grids whose activity increased most sharply
against their baseline in the current reporting window.

**Process record (acceptance criteria):** plan written and reviewed BEFORE any
edit; learner revised item 2 (originally proposed a new baseline computation —
rejected as a third implementation; must reuse ML2's baseline); approved.

## Where computed and why
API layer (SQL over the DE7 analytics tables). Not Spark: no new aggregation
grain is needed — hourly_grid_summary already holds current activity, and the
ML2 feature table already holds the baseline. Not React: ranking is business
logic and belongs behind the API contract, not in the client (RE-phase rule).

## Reused logic (no duplication)
- Baseline: the existing ML2 rolling baseline in ml/features.py /
  analytics.grid_features — **the baseline excludes the current interval**,
  and the AS_OF convention defines the current reporting window (CLAUDE.md
  rule 6). No new baseline math anywhere.
- Growth: the existing activity_growth definition from ML2.

## API contract — ADDITIVE
New endpoint `GET /network/top-movers?limit=10&as_of=...` in a new router
(api/routers/top_movers.py). No existing response shape changes; existing
clients (RE2–RE5 pages, C2 assistant, C12 MCP) are untouched.

## React placement
New card on the Network Overview page (RE2), linking each grid to the Grid
Explorer (RE3). Component: frontend/src/TopMovers.jsx.

## Tests changed
- New: tests/test_api.py::test_top_movers_shape_and_ordering
- New: tests/test_api.py::test_top_movers_baseline_excludes_current_interval
- Existing API snapshot tests unchanged → proves additivity.

## Verification result
All prior tests pass; end-to-end verified: endpoint → RE2 card renders top 10
by growth for the AS_OF window.
