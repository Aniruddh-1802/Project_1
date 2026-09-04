# C1 — Model Selection Rationale (required acceptance artifact)

Lab C1 requires a written model choice with cost and latency considered.
These rules are reused later by C16 (Context, Cost & Usage Optimization).

| Task in this project | Model | Why |
|---|---|---|
| Single-grid four-section explanation (C1, /explain-grid in C7) | Haiku | Evidence is small (< 1 KB curated object from API4 + ML6). Reasoning depth is low: format + terminology discipline. Cheapest and lowest latency; a NOC operator waits on this interactively. |
| Tool-using NOC assistant (C2) and headless investigator (C14) | Sonnet | Multi-step tool orchestration against API1–API6; needs reliable tool selection and evidence attribution, but not deep synthesis. |
| Long-context incident investigation (C3), multi-agent synthesis (C9) | Sonnet with extended thinking (Opus only if disagreement between specialists must be adjudicated) | Comparing current vs summarized historical evidence from DE7 + pipeline status from API6 is genuine reasoning; extended thinking helps separate CURRENT / HISTORICAL / UNCERTAINTY. |
| CI review (C15) | Sonnet | Runs headless in CI; latency matters less than in NOC chat, but cost per commit adds up. Sonnet catches grain/leakage/contract risks reliably. |

## Cost / latency notes recorded during the lab
- Rich context package (~1.4 KB) vs short package (~0.3 KB): answer quality
  improved materially with the rich package (INTERPRETATION cited rule alerts
  from NP3 and pipeline health from API6); latency difference was negligible
  at this evidence size. Conclusion: curation, not truncation, is the lever —
  this is the thesis proven quantitatively in C16.
- Extended thinking was NOT enabled for C1: the four-section format does the
  reasoning scaffolding, and enabling thinking roughly doubled latency with
  no change in severity classification across the 5 test grids.

## The four Claude surfaces in this project (Student Activity 1)
| Surface | Role here |
|---|---|
| Claude (chat) | Ad-hoc exploration; drafting docs like this one |
| Claude API | The production integration: C1, C2, C3, C14, C15 |
| Claude Code | Engineering assistant on the repo: C4–C13 |
| Cowork | Hand-over deliverables: the C3 incident report, C9 combined report, C16 guideline |
