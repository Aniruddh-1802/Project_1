"""
C14 — Claude Agent SDK — Headless NOC Investigation Agent
=========================================================
Canonical file per the guide's Repository Structure: agents/noc_investigator.py.

A service receives "Investigate Grid <id>" and this agent autonomously
gathers evidence and returns a structured investigation brief — no
interactive input (acceptance criterion).

Tools = the Phase 4 / Phase 6 endpoints, reached through the C12 MCP server
(mcp/network_mcp_server.py): network_summary (API1), grid_activity (API2),
grid_features (API4/ML2), grid_location (API6), anomaly_score/hotspots
(ML4/ML6 via API3), pipeline_status (API6/DE7).

Workflow: gather -> compare -> assess -> summarize.
pipeline_status is ALWAYS called FIRST; if unhealthy it constrains severity
and must appear in `uncertainty` (same rule the C8 anomaly skill encodes).

Graceful degradation: if any tool fails, finish with the remaining evidence,
name the missing source in `uncertainty`, lower confidence — NEVER substitute
an estimate for a failed call (the C2 rule, now enforced headlessly).

Run:  python agents/noc_investigator.py 4821
"""

import asyncio
import json
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)

SYSTEM_PROMPT = """You are a headless NOC investigation agent for the Milan
network grid. Input: a grid_id. Output: ONLY a JSON object, no prose, with:
  severity            "NORMAL" | "ATTENTION" | "HIGH"
  confidence          "high" | "medium" | "low"
  evidence            list of {claim, value, source_tool}
  uncertainty         what is unknown or untrustworthy, including any failed
                      tool named explicitly and anything pipeline status
                      makes doubtful
  recommended_checks  what a human should inspect next

Workflow (strict): gather -> compare -> assess -> summarize.
1. ALWAYS call pipeline_status FIRST. If unhealthy, it must appear in
   uncertainty and must constrain (cap) the severity.
2. Gather grid_activity, grid_features, anomaly evidence and grid_location.
3. Compare current activity to the baseline (the ML2 baseline excludes the
   current interval) and check NP3 rule-alert corroboration.
4. If any tool is unavailable: complete the investigation with the remaining
   evidence, name the missing source in uncertainty, and lower confidence.
   Never substitute an estimate for a failed call.
Rules: activity measures are not counts or MB; never claim congestion; every
evidence item carries its source_tool (acceptance criterion)."""


async def investigate(grid_id: int) -> dict:
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        # The C12 MCP server is the only capability surface — the agent gets
        # exactly the tools the platform exposes, nothing more (C6 spirit).
        mcp_servers={
            "network-intelligence": {
                "command": "python",
                "args": ["mcp/network_mcp_server.py"],
            }
        },
        allowed_tools=[
            "mcp__network-intelligence__pipeline_status",
            "mcp__network-intelligence__network_summary",
            "mcp__network-intelligence__grid_activity",
            "mcp__network-intelligence__grid_features",
            "mcp__network-intelligence__grid_location",
            "mcp__network-intelligence__hotspots",
            "mcp__network-intelligence__alerts",
        ],
        max_turns=15,
        permission_mode="bypassPermissions",  # headless service context; the
        # tool surface itself is read-only thin wrappers (C12), so this is safe.
    )

    brief_text = ""
    async for message in query(prompt=f"Investigate Grid {grid_id}.", options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if getattr(block, "text", None):
                    brief_text = block.text
        elif isinstance(message, ResultMessage) and message.is_error:
            # Agent-level failure path: still return a structured brief.
            return {
                "severity": "NORMAL", "confidence": "low", "evidence": [],
                "uncertainty": f"agent run failed: {message.result}",
                "recommended_checks": ["re-run investigation", "check API availability (C9 API Agent scope)"],
            }
    return json.loads(brief_text)


if __name__ == "__main__":
    grid = int(sys.argv[1]) if len(sys.argv) > 1 else 4821
    brief = asyncio.run(investigate(grid))
    # Structured output for the calling service (and for the Capstone, which
    # consumes this brief in the AI-Powered NOC Control Room).
    print(json.dumps(brief, indent=2))

    # Lab validation, automated:
    assert all("source_tool" in e for e in brief.get("evidence", [])), \
        "every evidence item must carry a source_tool"
