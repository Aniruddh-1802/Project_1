"""
C2 — Tool-Using Claude Network Operations Assistant
===================================================
Phase 7, Lab C2. Moves from prompt-only analysis (C1) to an assistant
that retrieves LIVE evidence through tools.

Every tool maps 1:1 onto an endpoint already built in Phase 4 / Phase 6:
  get_network_summary()   -> API1  GET /network/summary
  get_grid_activity()     -> API2  GET /network/grid/{grid_id}
  get_hotspots()          -> API3  GET /network/hotspots
  get_grid_features()     -> API4  GET /network/grid/{grid_id}/features
  get_anomaly_score()     -> ML4/ML6 anomaly output, served via the API
  get_grid_location()     -> API6  GET /network/grid/{grid_id}/location
  get_pipeline_status()   -> API6  GET /pipeline/status   <-- "can I trust this?"

Trainer focus (from the guide): this lab is where a team that skipped API6
discovers why it exists — pipeline status is part of every situation answer.
"""

import json
import os

import anthropic
import requests

API_BASE = os.environ.get("NETWORK_API_BASE", "http://localhost:8000")
MODEL = os.environ.get("C2_MODEL", "claude-sonnet-4-5")
client = anthropic.Anthropic()

# ---------------------------------------------------------------------------
# Tool implementations — THIN wrappers over the Phase 4 endpoints.
# Same "no business logic in the wrapper" rule that C12 enforces on the MCP
# server applies here: if a computation is needed, it belongs in the API.
# ---------------------------------------------------------------------------

def _get(path: str, params: dict | None = None) -> dict:
    """Shared HTTP helper. Failures are returned as structured errors so the
    assistant can report the gap instead of papering over it (Activity 6)."""
    try:
        r = requests.get(f"{API_BASE}{path}", params=params or {}, timeout=10)
        r.raise_for_status()
        return {"ok": True, "data": r.json()}
    except Exception as exc:  # noqa: BLE001 — the model must see the failure
        return {"ok": False, "error": f"{path} failed: {exc}"}


TOOL_IMPLS = {
    # AS_OF convention (see CLAUDE.md): "now" is the configured reporting
    # timestamp over the historical Telecom Italia dataset, not wall-clock time.
    "get_network_summary": lambda a: _get("/network/summary", {"as_of": a.get("as_of")}),          # API1
    "get_grid_activity":   lambda a: _get(f"/network/grid/{a['grid_id']}", {"as_of": a.get("as_of")}),  # API2
    "get_hotspots":        lambda a: _get("/network/hotspots", a),                                  # API3
    "get_grid_features":   lambda a: _get(f"/network/grid/{a['grid_id']}/features"),                # API4
    "get_anomaly_score":   lambda a: _get(f"/network/grid/{a['grid_id']}/anomaly", {"as_of": a.get("as_of")}),  # ML4/ML6
    "get_grid_location":   lambda a: _get(f"/network/grid/{a['grid_id']}/location"),                # API6 (joins on properties.cellId — see CLAUDE.md)
    "get_pipeline_status": lambda a: _get("/pipeline/status"),                                      # API6 (reads logs/ written by DE7)
}

TOOLS = [
    {"name": "get_network_summary", "description": "Network-wide activity summary (API1).",
     "input_schema": {"type": "object", "properties": {"as_of": {"type": "string"}}}},
    {"name": "get_grid_activity", "description": "Hourly activity for one grid (API2).",
     "input_schema": {"type": "object", "properties": {"grid_id": {"type": "integer"}, "as_of": {"type": "string"}}, "required": ["grid_id"]}},
    {"name": "get_hotspots", "description": "Top attention grids with severity and reasons (API3, uses NP3 rule alerts).",
     "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}, "severity": {"type": "string"}, "as_of": {"type": "string"}}}},
    {"name": "get_grid_features", "description": "ML2 engineered features for one grid (API4).",
     "input_schema": {"type": "object", "properties": {"grid_id": {"type": "integer"}}, "required": ["grid_id"]}},
    {"name": "get_anomaly_score", "description": "ML4/ML6 anomaly score and direction for one grid.",
     "input_schema": {"type": "object", "properties": {"grid_id": {"type": "integer"}, "as_of": {"type": "string"}}, "required": ["grid_id"]}},
    {"name": "get_grid_location", "description": "Geographic location of a grid cell in Milan (API6).",
     "input_schema": {"type": "object", "properties": {"grid_id": {"type": "integer"}}, "required": ["grid_id"]}},
    {"name": "get_pipeline_status", "description": "Pipeline health: rejected rows, staleness, last run (API6, data from DE7 status record).",
     "input_schema": {"type": "object", "properties": {}}},
]

# System prompt = the Suggested Learner Prompt from the guide, verbatim rules.
SYSTEM_PROMPT = """You are the Network Operations Assistant for the Milan grid.
Rules:
- ALWAYS call a tool for any factual claim. Never answer network questions
  from memory or from earlier in the conversation if the data may have changed.
- Before reporting a situation as fact, call get_pipeline_status() and say
  whether the underlying data is currently trustworthy.
- Cite which tool produced each figure.
- If a tool fails, say which one failed and what you therefore cannot
  conclude. Do not substitute an estimate.
- Activity measures are not counts or MB. Do not claim congestion."""


def run_agent_loop(messages: list, log_path: str = "logs/c2_tool_calls.jsonl") -> str:
    """The agent loop (core concept of C2): model -> tool_use -> tool_result
    -> model, until a plain text answer. Every call is logged so the learner
    can verify each figure traces to a tool response (acceptance criterion)."""
    while True:
        response = client.messages.create(
            model=MODEL, max_tokens=1500, system=SYSTEM_PROMPT,
            tools=TOOLS, messages=messages,
        )
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = TOOL_IMPLS[block.name](block.input)
            with open(log_path, "a") as f:  # tool-call log — checked in validation
                f.write(json.dumps({"tool": block.name, "input": block.input, "result_ok": result["ok"]}) + "\n")
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": json.dumps(result)})
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    convo = [{"role": "user", "content": 'Which areas need attention right now?'}]
    print(run_agent_loop(convo))

    # Follow-up in the SAME session (Activity 3) — the assistant must still
    # call tools rather than reuse stale context (rule 1).
    convo.append({"role": "user", "content":
        'Follow-up: "Explain Grid 4821." Gather the grid activity, features, '
        'anomaly score and location before answering. Tell me where it is in '
        'Milan, what the evidence shows, what it might mean, and what I should '
        'check next. Separate observed evidence from inference.'})
    print(run_agent_loop(convo))
