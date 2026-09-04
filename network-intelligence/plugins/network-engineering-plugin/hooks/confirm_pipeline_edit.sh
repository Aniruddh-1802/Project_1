#!/usr/bin/env bash
# C10 pre-action hook. Requires explicit confirmation before any edit to
# airflow/ or pipeline configuration (complements the C6 "ask" policy —
# hooks enforce at the event, permissions at the tool class).
INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
case "$FILE" in
  *airflow/*|*pipeline*config*)
    echo "$(date -Is) ASK  pre-edit confirmation required for $FILE" >> logs/hook_outcomes.log
    # Exit 2 with a message: Claude Code must surface this and get approval.
    echo "Editing pipeline orchestration ($FILE) requires explicit human confirmation (C6/C10 policy)." >&2
    exit 2 ;;
  *) exit 0 ;;
esac
