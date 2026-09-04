# Phase 7 — Claude: AI-Assisted Network Operations — Completed Deliverables

Claude stops being the tool that helped build the platform and becomes an
engineered part of it. Data scope everywhere: **curated evidence only** (API
responses, ML outputs, pipeline status) — never raw rows.

| Lab | Deliverable(s) | Key cross-references |
|---|---|---|
| C1 Insight Generator | `agents/c1_insight_generator.py`, `docs/c1_model_selection_rationale.md` | evidence from API4 + ML4/ML6 + NP3; four-section contract |
| C2 Tool-Using Assistant | `agents/c2_noc_assistant.py`, `logs/c2_tool_calls.jsonl` | tools = API1–API6 + ML4/ML6; pipeline status (API6) in every situation answer |
| C3 Long-Context Investigation | `agents/c3_incident_investigation.py`, `docs/context_engineering_checklist.md`, `docs/c3_incident_report_grid4821.md` (Cowork) | history summarized from DE7; DE8 failure injections drive UNCERTAINTY |
| C4 Claude Code onboarding | `CLAUDE.md` (all six rules), `docs/repository_map.md`, `docs/missing_tests.md` | grain, activity≠counts/MB, no congestion, properties.cellId, AS_OF |
| C5 Plan Mode feature | `docs/plans/c5_top_movers_plan.md`, `api/routers/top_movers.py`, `frontend/src/TopMovers.jsx`, `tests/test_top_movers.py` | reuses ML2 baseline; additive API; RE2 placement, RE3 links |
| C6 Permissions | `.claude/settings.json` (allow/ask/deny), `docs/c6_permission_policy.md` | data/raw immutable (DE contract); .env denied |
| C7 Slash commands | `.claude/commands/` (5), `docs/c7_command_catalog.md` | /network-health = grain test; /review-anomaly compares NP3 vs ML3 vs ML4 |
| C8 Skills | `.claude/skills/` (3 skills), `docs/c8_skill_before_after.md` | encodes C1 contract + CLAUDE.md terminology; refuses severity on missing evidence |
| C9 Subagents | `.claude/agents/` (4 specialists), `docs/c9_combined_investigation_report.md` (Cowork) | Pipeline/Network/ML/API scopes; disagreement surfaced, not smoothed |
| C10 Hooks | `.claude/hooks/*.sh`, hooks block in `.claude/settings.json`, `logs/hook_outcomes.log` | post-edit grain + ML2 leakage tests; pre-edit confirm on airflow/ |
| C11 Checkpoints | `docs/c11_checkpoint_rollback_report.md` | threshold experiment judged on alert volume, top-20, NP3 agreement; rolled back |
| C12 MCP Server | `mcp/network_mcp_server.py` | THIN wrappers over API1–API6; zero business logic; validation + limits |
| C13 Plugin | `plugins/network-engineering-plugin/`, `docs/c13_versioning_ownership.md` | packages C4 rules + C7 + C8 + C9 + C10 + C12 config |
| C14 Agent SDK | `agents/noc_investigator.py` (headless) | gather→compare→assess→summarize; pipeline_status FIRST; graceful degradation; feeds the Capstone |
| C15 CI Review | `ci/claude_review.py`, `.github/workflows/claude-review.yml`, `docs/c15_review_comparison.md` | six risk categories; advisory only, humans merge |
| C16 Cost & Context | `scripts/c16_context_comparison.py`, `docs/c16_cost_context_guidelines.md` (Cowork) | Design A vs B at real DE7 row counts; model-selection rules |

Environment: `ANTHROPIC_API_KEY` and `NETWORK_API_BASE` per `.env.example`
(Lab 0). Python deps: `anthropic`, `mcp`, `claude-agent-sdk`, `requests`,
`fastapi`, `pytest`.
