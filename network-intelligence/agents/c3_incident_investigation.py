"""
C3 — Long-Context Incident Investigation
========================================
Phase 7, Lab C3. Context engineering: compare a "dump everything" prompt
against a curated context package for the question "has this abnormal
pattern happened before, and can the data be trusted?"

Cross-references:
  - Historical evidence and prior alerts come from the warehouse built in
    DE7 (analytics layer) — summarized here BEFORE insertion into context
    (Activity 3), never as raw rows (Phase 7 data-scope rule).
  - Pipeline quality status comes from API6 GET /pipeline/status; the
    failure injections learners performed in DE8 are exactly what makes
    the UNCERTAINTY section meaningful here (Trainer Focus).
  - The written checklist output lives at docs/context_engineering_checklist.md.
  - The final incident report is a hand-over document — assemble in Cowork
    (docs/c3_incident_report_grid4821.md is the template).
"""

import json
import os

import anthropic

MODEL = os.environ.get("C3_MODEL", "claude-sonnet-4-5")
client = anthropic.Anthropic()

# The Suggested Learner Prompt from the guide, verbatim three-section contract.
INVESTIGATION_PROMPT = """Investigate an unusual activity pattern at Grid {grid_id}.
Answer in exactly three sections:
  CURRENT EVIDENCE     what is true right now, with figures
  HISTORICAL EVIDENCE  whether this has happened before, and how often
  UNCERTAINTY          what you do NOT know, including anything the
                       pipeline status makes doubtful
If the pipeline status indicates rejected rows, handled nulls or a stale
analytics layer, treat that as material and say how it limits the conclusion.
Do not restate raw rows back to me. Do not claim congestion."""


def summarize_history(raw_history_rows: list[dict]) -> dict:
    """Activity 3: summarize older evidence BEFORE it enters the context.
    In the real lab this aggregation runs in Spark/SQL over the DE7 analytics
    layer, not in Python over raw rows — shown here for shape only."""
    scores = [r["anomaly_score"] for r in raw_history_rows]
    return {
        "intervals_summarized": len(raw_history_rows),
        "prior_intervals_with_anomaly_score_gt_3": sum(s > 3 for s in scores),
        "max_prior_anomaly_score": max(scores, default=None),
        "note": "aggregated from DE7 analytics layer; raw rows excluded by design",
    }


def build_curated_package(grid_id: int, pipeline_healthy: bool = True) -> dict:
    """The curated evidence package (Activity 1). Each key maps to a source:
       current_metrics   API2 + API4    history_summary  DE7 (summarized)
       prior_alerts      API3 / NP3     model_scores     ML3 + ML4/ML6
       pipeline_status   API6 / DE7 status record (DE8 injections show here)
    """
    return {
        "grid_id": grid_id,
        "current_metrics": {"timestamp": "2013-11-07T18:00:00", "total_activity": 342.7,
                            "baseline_total_activity": 121.4, "activity_growth": 1.82},
        "history_summary": summarize_history(
            [{"anomaly_score": s} for s in (1.1, 0.8, 3.4, 1.0, 4.1, 0.9)]),
        "prior_alerts": ["NP3_SPIKE_RULE fired 2013-10-31T19:00", "NP3_SPIKE_RULE fired 2013-11-01T18:00"],
        "model_scores": {"risk_class": "elevated", "anomaly_score": 3.9, "direction": "above_baseline"},
        "pipeline_status": (
            {"status": "healthy", "rejected_rows": 0, "analytics_staleness_hours": 1}
            if pipeline_healthy else
            # DE8-style injected failure: this MUST materially change UNCERTAINTY
            {"status": "degraded", "rejected_rows": 5231, "handled_nulls": 812,
             "analytics_staleness_hours": 26}
        ),
    }


def investigate(grid_id: int, package: dict) -> str:
    response = client.messages.create(
        model=MODEL, max_tokens=1200,
        messages=[{"role": "user", "content":
            INVESTIGATION_PROMPT.format(grid_id=grid_id)
            + "\n\nCurated evidence package:\n" + json.dumps(package, indent=2)}],
    )
    return response.content[0].text


if __name__ == "__main__":
    # Acceptance: both runs recorded and compared. The "dump everything" run
    # is performed in the lab by pasting the raw multi-grid extract (see C16,
    # which quantifies exactly how large that context is); we record only the
    # curated runs here.
    healthy = investigate(4821, build_curated_package(4821, pipeline_healthy=True))
    degraded = investigate(4821, build_curated_package(4821, pipeline_healthy=False))
    print("=== HEALTHY PIPELINE ===\n", healthy)
    print("\n=== DEGRADED PIPELINE (DE8-style injection) ===\n", degraded)
    # Acceptance criterion: the UNCERTAINTY section must change MATERIALLY
    # between these two runs — record both in docs/c3_incident_report_grid4821.md.
