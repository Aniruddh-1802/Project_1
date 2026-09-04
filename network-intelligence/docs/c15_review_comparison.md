# C15 — Review vs Tests/Static Comparison (required validation record)

Change reviewed: the C5 top-movers PR (api/routers/top_movers.py,
frontend/src/TopMovers.jsx, tests/test_top_movers.py).

| Finding | Caught by tests/static? | Caught by Claude review? |
|---|---|---|
| growth division by zero baseline | yes (test) | yes |
| response shape additive | yes (snapshot tests) | yes |
| **UI footnote initially said "usage"** — terminology drift toward counts | **no** — no lint rule reads JSX copy | **yes** (terminology category) |
| missing test: limit>50 rejected | no | yes (missing-tests category) |
| leakage / grain / cellId | n/a (change doesn't touch them) | correctly reported "no finding" |

At least one finding the test suite did not catch: the terminology drift —
exactly the class of failure the CLAUDE.md rules exist for. Agent authority:
none — CI exits 0 regardless; humans merge.
