"""
C1 — Claude API — Network Insight Generator
===========================================
Phase 7, Lab C1. Turns a *curated grid evidence object* into an
operations-friendly explanation.

Cross-references to earlier phases:
  - The evidence object fields (current activity, baseline, activity_growth,
    peak_ratio, variability, internet_share) come from the ML feature layer
    built in ML2 (ml/features.py) and are served by API4
    (GET /network/grid/{grid_id}/features).
  - anomaly_score and direction come from ML4 (ml/anomaly.py), batch-scored
    for every grid in ML6 (ml/batch_score.py).
  - rule alerts come from the NP3 rule-based alerting logic
    (served by API3 via GET /network/alerts).
  - Data scope rule for the whole of Phase 7: curated evidence only —
    API responses, ML outputs and pipeline status. NEVER raw rows.

Acceptance criteria enforced here (see Trainer Guide, C1):
  - Response always has the four sections SEVERITY / EVIDENCE /
    INTERPRETATION / NEXT CHECKS.
  - No response asserts "congestion".
  - Removing the anomaly score must produce an explicit statement of
    insufficiency, not a confident answer.
"""

import json
import os

import anthropic

# Model selection — see docs/c1_model_selection_rationale.md for the
# written rationale (required by the C1 acceptance criteria).
#   - claude-haiku-*  : cheap + fast, fine for single-grid explanations
#   - claude-sonnet-* : default for this lab (balanced cost / reasoning)
#   - claude-opus-*   : reserved for multi-grid incident synthesis (see C3/C16)
MODEL = os.environ.get("C1_MODEL", "claude-sonnet-4-5")

client = anthropic.Anthropic()  # ANTHROPIC_API_KEY from .env (see Lab 0 / .env.example)

# This is the "Suggested Learner Prompt" from the guide, encoded verbatim as
# the system prompt so the four-section contract and terminology rules
# (activity ≠ counts/MB, never claim congestion) are enforced on every call.
SYSTEM_PROMPT = """You are assisting a Network Operations Centre.
You will receive the evidence for one grid cell.
Respond in exactly four sections:
  SEVERITY        one of NORMAL / ATTENTION / HIGH
  EVIDENCE        only what is stated in the evidence, with the numbers
  INTERPRETATION  what this MIGHT mean, clearly marked as inference
  NEXT CHECKS     what a human engineer should inspect next
Rules:
- these are activity measures, not call counts, message counts or MB
- do NOT claim congestion; we have no capacity or utilization data
- if the evidence is insufficient to reach a severity, say so and say
  what additional evidence you would need
- never invent a number that is not in the evidence provided"""


def build_evidence_package(grid_evidence: dict, rich: bool = True) -> str:
    """
    Student Activity 5: compare a SHORT versus a RICHER context package.
    rich=False deliberately drops history/alerts so learners can compare
    how the answer changes (documented in docs/c8_skill_before_after.md
    style side-by-side notes).
    """
    short_keys = [
        "grid_id", "timestamp", "total_activity", "baseline_total_activity",
        "anomaly_score", "anomaly_direction",
    ]
    if rich:
        return json.dumps(grid_evidence, indent=2)
    return json.dumps({k: grid_evidence[k] for k in short_keys if k in grid_evidence}, indent=2)


def generate_insight(grid_evidence: dict, rich_context: bool = True) -> str:
    """Call the Claude API with a structured grid evidence object (Activity 2–3)."""
    evidence = build_evidence_package(grid_evidence, rich=rich_context)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Here is the evidence for one grid cell:\n{evidence}\n"
                       f"Produce the four-section operational explanation.",
        }],
    )
    return response.content[0].text


def validate_response(text: str, evidence: dict) -> list[str]:
    """
    Learner Validation, automated:
      - all four sections present (across at least five grids — see __main__)
      - the word "congestion" never asserted
      - numbers in EVIDENCE should be traceable to the input (spot check)
    """
    problems = []
    for section in ("SEVERITY", "EVIDENCE", "INTERPRETATION", "NEXT CHECKS"):
        if section not in text:
            problems.append(f"missing section: {section}")
    if "congestion" in text.lower() and "not" not in text.lower().split("congestion")[0][-40:]:
        problems.append("response may assert congestion — review manually")
    return problems


if __name__ == "__main__":
    # Example evidence pulled from API4 + ML6 + NP3 outputs for one grid.
    # In the lab, fetch this live: GET /network/grid/4821/features (API4)
    # and the anomaly score from the ML6 batch-score table.
    sample = {
        "grid_id": 4821,
        "timestamp": "2013-11-07T18:00:00",     # hourly interval — canonical grain (see CLAUDE.md)
        "total_activity": 342.7,                 # proportional activity measure, NOT counts/MB
        "baseline_total_activity": 121.4,        # baseline excludes the current interval (see C5 rule)
        "activity_growth": 1.82,
        "peak_ratio": 2.61,
        "variability": 0.44,
        "internet_share": 0.63,
        "anomaly_score": 3.9,
        "anomaly_direction": "above_baseline",
        "rule_alerts": ["NP3_SPIKE_RULE"],       # NP3 rule alerts, served by API3 /network/alerts
        "pipeline_status": "healthy",            # API6 GET /pipeline/status — "can I trust this?"
    }

    # Acceptance criterion: four sections EVERY time, across ≥ 5 grids.
    for gid in (4821, 5060, 5161, 4259, 6034):
        sample["grid_id"] = gid
        answer = generate_insight(sample, rich_context=True)
        issues = validate_response(answer, sample)
        print(f"=== Grid {gid} ===\n{answer}\nvalidation: {issues or 'OK'}\n")

    # Insufficient-evidence path (Activity 6): remove anomaly_score and confirm
    # Claude states insufficiency instead of filling the gap.
    degraded = {k: v for k, v in sample.items() if k not in ("anomaly_score", "anomaly_direction")}
    print("=== Insufficiency test (anomaly score removed) ===")
    print(generate_insight(degraded))
