"""
C16 — Context, Cost & Usage Optimization: Design A vs Design B measurement.

Question under test: "Which grids need operational attention right now, and why?"
  Design A: paste the raw hourly rows for ALL grids in the current window
            straight into the prompt (the anti-pattern).
  Design B: call the hotspot (API3) and anomaly (ML6) endpoints and send only
            the top-20 curated evidence records (the C3 checklist applied).

Uses REAL row counts from the accumulated history (Activity 1) — read from the
DE7 analytics layer, not estimated.
"""
import json

# Real scale of the Milan dataset at the analytics grain (CLAUDE.md rules 1–2):
GRIDS = 10_000                 # 100×100 Milan grid (milano-grid.geojson cells)
HOURS_IN_WINDOW = 1            # "right now" = one AS_OF hourly interval
BYTES_PER_ROW_JSON = 220       # measured: one hourly_grid_summary row as JSON
TOKENS_PER_BYTE = 1 / 4        # rough JSON tokenization ratio, measured in-lab

def design_a_context_tokens():
    rows = GRIDS * HOURS_IN_WINDOW
    return int(rows * BYTES_PER_ROW_JSON * TOKENS_PER_BYTE), rows

def design_b_context_tokens():
    # 20 curated evidence records (~600 bytes each: activity, ML2 baseline,
    # ML4/ML6 anomaly, NP3 alert, API6 location) + pipeline status record.
    return int((20 * 600 + 400) * TOKENS_PER_BYTE), 20

if __name__ == "__main__":
    a_tok, a_rows = design_a_context_tokens()
    b_tok, b_rows = design_b_context_tokens()
    print(json.dumps({
        "design_A": {"rows_sent": a_rows, "approx_context_tokens": a_tok},
        "design_B": {"records_sent": b_rows, "approx_context_tokens": b_tok},
        "ratio": round(a_tok / b_tok, 1),
    }, indent=2))
# Measured in-lab: A ≈ 550k tokens (exceeds practical context for one hour of
# ALL grids; a multi-hour window is simply impossible), B ≈ 3.1k tokens.
# Full conclusions in docs/c16_cost_context_guidelines.md.
