"""
C15 — Headless / CI Engineering Review
======================================
Claude reviews a change diff IN ADDITION to tests, never instead of them
(the workflow in .github/workflows/claude-review.yml runs pytest first and
attaches the results). Claude has NO approval, merge or deployment authority
— it writes a report file; humans decide (acceptance criterion).

The six risk categories come straight from the lab and map to the project's
known failure modes:
  data-grain        CLAUDE.md rules 1–2 / tests/test_grain.py / C10 hook
  leakage           ML2 rule / tests/test_ml.py::test_no_leakage
  geographic join   properties.cellId rule (RE4 trap; API6 /location)
  API contract      additivity rule proven in C5
  terminology       CLAUDE.md rules 3–4 (no congestion, no counts/MB)
  missing tests     the C4 missing-tests list as a living standard
"""

import pathlib
import subprocess
import sys

import anthropic

MODEL = "claude-sonnet-4-5"  # per docs/c1_model_selection_rationale.md (CI row)
client = anthropic.Anthropic()

REVIEW_PROMPT = """Review this change against the project rules in CLAUDE.md
(attached). The test suite has already run and its results are attached.
Identify risks in these categories specifically:
- data-grain: could this reintroduce duplicates on (grid_id, timestamp)?
- leakage: could this let a feature see data after feature_timestamp?
- geographic join: does this touch the cellId join anywhere?
- API contract: is any change to a response shape non-additive?
- terminology: does any new string assert congestion or convert activity
  measures into counts or MB?
- missing tests
Produce a review report covering ALL SIX categories (write "no finding" where
clean). Do NOT approve, merge or deploy anything — those decisions stay with
a human. End with: findings the test suite did not catch, or why there were none."""


def main() -> int:
    diff = subprocess.run(["git", "diff", "origin/main...HEAD"],
                          capture_output=True, text=True, check=True).stdout
    claude_md = pathlib.Path("CLAUDE.md").read_text()
    test_results = pathlib.Path("test-results.txt").read_text() \
        if pathlib.Path("test-results.txt").exists() else "(test results missing — flag this)"

    response = client.messages.create(
        model=MODEL, max_tokens=2000,
        messages=[{"role": "user", "content":
            f"{REVIEW_PROMPT}\n\n--- CLAUDE.md ---\n{claude_md}\n\n"
            f"--- TEST RESULTS (already run) ---\n{test_results}\n\n"
            f"--- CHANGE DIFF ---\n{diff}"}],
    )
    report = response.content[0].text
    pathlib.Path("claude-review-report.md").write_text(report)
    print(report)
    # Advisory only: ALWAYS exit 0. The report is posted as a PR comment; a
    # human reads it and approves/merges. No gate, no deploy (lab boundary).
    return 0


if __name__ == "__main__":
    sys.exit(main())
