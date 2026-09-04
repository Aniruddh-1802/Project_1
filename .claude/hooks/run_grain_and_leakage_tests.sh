#!/usr/bin/env bash
# C10 post-edit hook. Fires after Edit/Write; acts only for the real Spark
# and ML directories in this project: spark/ and Machine_learning/ (the
# guide's canonical "ml/" name does not exist here).
# Runs the two silent-and-expensive checks that must never wait for CI:
#   1. grain duplicate check on (grid_id, timestamp)  -> tests/test_grain.py
#      (guards CLAUDE.md rules 1–2; same check as /network-health, C7)
#   2. ML2 feature leakage test                       -> tests/test_ml.py::test_no_leakage
# Both live at the repository root's tests/, not a network-intelligence-
# local copy. Outcomes appended to logs/hook_outcomes.log (acceptance
# criterion) - also at the repository root.
INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
case "$FILE" in
  *spark/*|*Machine_learning/*)
    if python -m pytest tests/test_grain.py tests/test_ml.py::test_no_leakage -q; then
      echo "$(date -Is) PASS post-edit grain+leakage after edit of $FILE" >> logs/hook_outcomes.log
      exit 0
    else
      echo "$(date -Is) FAIL post-edit grain+leakage after edit of $FILE" >> logs/hook_outcomes.log
      echo "Grain or leakage test failed after editing $FILE — fix before continuing." >&2
      exit 2   # blocking: feed the failure back to Claude Code
    fi ;;
  *) exit 0 ;;
esac
