# C9 — Combined Multi-Agent Investigation Report — "Why is Grid 4821 flagged?"
<!-- Deliverable assembled in Cowork per the lab's "Where Cowork fits" note.
     Supervisor task ran the four .claude/agents/ specialists in parallel. -->

## Severity (single): ATTENTION

## Evidence, attributed by specialist
- **Data Pipeline Agent:** last run successful; 0 rejected rows; analytics 1h
  old → TRUSTWORTHY. Source: API6 /pipeline/status (DE7 record).
- **Network Analysis Agent:** activity 342.7 vs ML2 baseline 121.4 (growth
  1.82×); two neighbouring cells (API3 nearby hotspots) show a milder rise →
  localized-plus-spillover pattern. Sources: API1, API2, API3, API6/location.
- **ML Analysis Agent:** ML4 anomaly 3.9 above_baseline; ML3 classifier
  "elevated"; driving features peak_ratio 2.61, activity_growth 1.82 (API4).
  Signals agree with the NP3 rule alert.
- **API Agent:** all endpoints OK; ML6 anomaly response timestamp matches the
  AS_OF window — no staleness.

## Disagreement surfaced (not smoothed)
Network Analysis reads the neighbour spillover as *area-wide onset*; ML
Analysis notes the anomaly model flags only 4821, since neighbours remain
inside their own baselines. Left as an open disagreement — next check decides.

## Recommended next checks (human)
1. Re-run /explain-grid on the two neighbouring cells next interval.
2. Check whether the pattern repeats at the same hour (the C3 historical
   recurrence finding suggests an evening pattern).
3. If it recurs area-wide, treat as an event pattern, not a grid fault.

## When NOT to orchestrate (required discussion)
For a single-grid, healthy-pipeline question, the C2 single assistant with the
same tools reaches the same answer with one context and lower cost. Four
agents earn their complexity only when the perspectives can genuinely
disagree (as here) or when scope isolation matters (governance).
