---
name: network-anomaly-analysis
description: Use when someone asks why a grid is flagged, what an anomaly score means, or whether an activity pattern is unusual. Encodes the project's evidence requirements, four-section response format and terminology rules.
---
# Network Anomaly Analysis (C8 skill)

<!-- Domain rules owned by the learner/team — same rules as CLAUDE.md and the
     C1 contract, packaged for automatic activation. -->

## Required evidence — refuse a severity if any is missing
1. current activity for the interval (API2 / analytics.hourly_grid_summary)
2. baseline activity — the ML2 baseline, which excludes the current interval
3. anomaly score AND direction (ML4, batch-scored in ML6)
4. rule alerts currently firing (NP3, via API3 /network/alerts)
5. pipeline status (API6 /pipeline/status) — evidence is only as good as the run that produced it

If given a bare grid ID, ask for (or fetch) the evidence above. **State
insufficiency rather than fill gaps.** Never invent a number.

**Current build gap:** item 3 (a stored per-grid anomaly score) is not yet
exposed by an API endpoint in this project — `risk_score`/`risk_level` on
`/network/hotspots` and `/network/alerts` exist in the schema but are not
populated, and `/network/predict-risk` is a stub. Until ML5/ML6 wire a real
score through, correctly refusing to assign a severity that depends on it is
the expected outcome, not a bug in this skill.

## Response format — always, exactly
SEVERITY        NORMAL / ATTENTION / HIGH
EVIDENCE        only supplied figures, each with its source
INTERPRETATION  what this MIGHT mean, clearly marked as inference
NEXT CHECKS     what a human engineer should inspect next

## Terminology rules (CLAUDE.md rules 3–5)
- Activity values are proportional activity measures — not call counts, not
  message counts, not MB.
- Never claim congestion; there is no capacity or utilization data.
- A grid is a geographic cell of the Milan grid (milano-grid.geojson,
  joined on properties.cellId) — it is not a tower.

## Severity guidance
- Pipeline degraded (rejected rows / stale analytics) caps severity at
  ATTENTION and must be named in EVIDENCE and NEXT CHECKS.
- Anomaly score alone never yields HIGH; corroboration from the NP3 rule
  alerts or a sustained multi-interval pattern is required.
