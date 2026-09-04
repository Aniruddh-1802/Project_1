# C6 — Project Permission Policy (learner-owned, committed)

Effective config: `.claude/settings.json`. Every classification names the
failure it prevents (the lab requirement). Final classification made by the
learner, not Claude.

| Operation | Class | Failure prevented |
|---|---|---|
| Read anything; run pytest; ruff/black; git status/diff | **allow** | none — safe reads, tests and formatting keep Claude Code productive |
| pip/uv/npm dependency changes | **ask** | silent PySpark/Airflow version drift (Lab 0 warned wheels lag Python releases) |
| Edit airflow/ DAGs or pipeline configuration | **ask** | breaking the ingest→Spark→warehouse→quality→scoring→notify chain built in DE2+ (also gated by the C10 pre-edit hook) |
| Database migrations / psql | **ask** | destructive schema change on DE7 analytics tables |
| Edit api/main.py, requirements.txt, .env.example | **ask** | non-additive API contract changes (the C5/C15 additivity rule) |
| Delete anything under data/ ; edit/write data/raw/ | **deny** | **raw must be immutable** — the DE-phase contract; losing raw destroys reprocessability |
| Read .env or any secret | **deny** | credential exfiltration into context/logs |
| DROP TABLE / TRUNCATE / rm -rf | **deny** | unrecoverable warehouse or repo loss |

## Demonstrations performed (acceptance criteria)
- **Denied, live:** asked Claude Code to `rm data/raw/sms-call-internet-mi-2013-11-07.csv`
  → operation blocked by `deny: Edit/Write/rm on data/raw/**`. ✔
- **Ask, live:** asked Claude Code to add a dependency → `pip install` prompted
  for approval before running. ✔
- Managed settings discussion: in a team environment these same rules ship via
  the C13 plugin plus org-managed settings so individual developers cannot
  loosen the deny list.
