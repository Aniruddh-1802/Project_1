# C3 — Context Engineering Checklist (project standard)

Deliverable required by Lab C3; reused by C9 (what each subagent receives),
C14 (agent evidence gathering) and C16 (cost rules).

Before anything enters a Claude context in this project, check:

1. **Is it curated?** Phase 7 data-scope rule: API responses, ML outputs and
   pipeline status only. Never raw rows from `data/raw/` or `data/processed/`.
2. **Is history summarized?** Older evidence is aggregated (in Spark/SQL over
   the DE7 analytics layer) before insertion — counts, maxima, recurrence,
   never row dumps.
3. **Is pipeline status included?** Every situation answer needs API6
   `GET /pipeline/status`. "Can I trust this?" is part of the evidence, not
   an afterthought. (DE8 failure injections must surface in UNCERTAINTY.)
4. **Is every number traceable?** Each figure must map to a source: API1–API6,
   ML3/ML4/ML6, or the NP3 rule alerts.
5. **Is anything irrelevant?** Remove context not needed for the question and
   re-run; if the conclusion changes, document why (C3 Activity 5).
6. **Is terminology safe?** No field names or labels implying counts, MB or
   congestion (see CLAUDE.md terminology rules).
7. **Is the response format contracted?** Four sections (C1) or three sections
   (C3) — a format contract prevents evidence/inference blur.
8. **Is the model matched to the task?** See docs/c1_model_selection_rationale.md
   and the C16 rules.
