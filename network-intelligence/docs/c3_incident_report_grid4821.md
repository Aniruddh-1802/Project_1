# C3 — Incident Investigation Report — Grid 4821 (Cowork hand-over template)

> Assemble the final version of this report in Cowork (per the lab's
> "Where Cowork fits" note). Populate from the recorded runs of
> `agents/c3_incident_investigation.py`.

## CURRENT EVIDENCE
- Interval 2013-11-07T18:00 (AS_OF convention — see CLAUDE.md)
- total_activity 342.7 vs baseline 121.4 (growth 1.82) — source: API2/API4
- anomaly_score 3.9 above_baseline — source: ML4/ML6
- NP3_SPIKE_RULE firing — source: API3 /network/alerts

## HISTORICAL EVIDENCE
- 2 of last 6 summarized intervals exceeded anomaly score 3 (max 4.1) — source: DE7 analytics summary
- Same NP3 rule fired at similar evening hours on 2013-10-31 and 2013-11-01
- Preliminary read: a *recurring evening pattern*, not a first occurrence

## UNCERTAINTY
- Healthy-pipeline run: uncertainty limited to absence of capacity data
  (hence no congestion claim is possible — terminology rule).
- Degraded-pipeline run (DE8-style injection: 5,231 rejected rows, analytics
  26h stale): current-interval figures may undercount activity; severity
  cannot exceed ATTENTION until the pipeline recovers. **This section changed
  materially between runs — acceptance criterion met.**

## Comparison record (dump-everything vs curated)
| | Dump-everything | Curated package |
|---|---|---|
| Context size | full multi-grid extract (quantified in C16) | ~1.5 KB |
| Historical recurrence identified | buried / inconsistent | explicit, counted |
| Pipeline status used | ignored among rows | drives UNCERTAINTY |
| Conclusion changed when irrelevant context removed? | yes — recorded per Activity 5 | n/a |
