# C16 — Cost & Context Design Guideline (standing reference — Cowork deliverable)

## The measurement (scripts/c16_context_comparison.py, real row counts from DE7)
| | Design A: raw rows in prompt | Design B: curated top-20 via API3 + ML6 |
|---|---|---|
| Records sent | 10,000 hourly rows (one AS_OF interval, all grids) | 20 evidence records + pipeline status |
| Approx context | ~550k tokens — infeasible/expensive; multi-hour windows impossible | ~3.1k tokens (~180× smaller) |
| Latency | tens of seconds+ where it runs at all | ~2–4 s |
| Answer quality | ranking drifted between runs; pipeline status buried; invited invented aggregates | stable top-20; every figure sourced; UNCERTAINTY driven by API6 status |
| What A gets right that B doesn't | can notice a pattern the endpoints don't expose | — that's the signal an **endpoint is missing** (the C12 thin-wrapper rule): add it to the API, don't dump rows |

## Project rules: cheaper/faster vs deeper reasoning (Activity 6)
1. **Haiku** — single-grid, fully-curated, format-contract tasks: C1
   explanations, /explain-grid (C7), UI-adjacent summaries.
2. **Sonnet** — tool orchestration and review: C2 assistant, C14
   noc_investigator.py, C15 CI review.
3. **Sonnet + extended thinking (Opus by exception)** — genuine synthesis:
   C3 incident investigation, adjudicating C9 specialist disagreement.
4. Escalate models only when the task fails a quality check, never by default.

## Context rules (with the C3 checklist)
- Curated evidence only; raw rows never enter a prompt (Phase 7 data-scope rule).
- History is summarized in Spark/SQL (DE7) before insertion.
- Pipeline status (API6) accompanies every situation question.
- Long sessions: compact by replacing resolved threads with one-paragraph
  summaries; re-state the AS_OF window after every compaction.
- If a question needs data no endpoint serves → add the endpoint (C5 process),
  don't widen the context.
