# C8 — Before/After Skill Comparison (documented, acceptance criterion)

Question: "Why is grid 4821 flagged?" (only a grid ID supplied — no evidence)

## WITHOUT network-anomaly-analysis skill
Claude produced a fluent narrative: guessed an evening commuter surge, implied
heavy network *usage* and offered a confident "likely high load" reading — no
severity discipline, no sources, and it accepted the bare grid ID.

## WITH the skill
Claude refused to assign a severity: listed the five required evidence items
(current activity, ML2 baseline, ML4/ML6 anomaly score + direction, NP3 rule
alerts, API6 pipeline status), asked for them or offered to fetch via the C2
tools, and reiterated the terminology rules. After evidence was supplied, it
answered in the exact four-section format with every figure sourced.

## Rule-change experiment (Activity 6)
Changed the severity rule from "anomaly score alone never yields HIGH" to
"score > 5 alone may yield HIGH", re-ran the same evidence (score 3.9):
output unchanged (still ATTENTION). With a synthetic score 5.6 the WITH-skill
answer moved to HIGH — the skill, not the prompt, is governing behaviour. ✔

Acceptance met: ≥2 skills exist (3), before/after documented, the anomaly
skill refuses severity on incomplete evidence.
