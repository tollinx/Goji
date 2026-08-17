#!/bin/bash
# PostToolUse hook — runs the eval quick-subset after any edit to retrieval.py or generation.py
#
# Claude Code fires this hook after every tool use. We only act when the edited
# file is one of the two files that most affect RAG quality.
#
# Register in .claude/settings.json:
# {
#   "hooks": {
#     "PostToolUse": [
#       {
#         "matcher": "write_file|str_replace_based_edit_tool",
#         "hooks": [{ "type": "command", "command": ".claude/hooks/post_tool_use_eval.sh" }]
#       }
#     ]
#   }
# }

# Claude Code passes the tool result as JSON on stdin
TOOL_RESULT=$(cat)

# Extract the file path from the tool result (works for write_file and str_replace outputs)
FILE_PATH=$(echo "$TOOL_RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    # str_replace_based_edit_tool puts path in 'path'; write_file in 'path' too
    print(data.get('path', data.get('file_path', '')))
except:
    print('')
" 2>/dev/null)

# Only run evals if the edited file is retrieval.py or generation.py
if [[ "$FILE_PATH" != *"retrieval.py"* ]] && [[ "$FILE_PATH" != *"generation.py"* ]]; then
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 PostToolUse eval triggered by: $FILE_PATH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check the backend directory exists
if [ ! -d "backend" ]; then
    echo "⚠️  No backend/ directory found — skipping eval."
    exit 0
fi

# Check the eval script exists
if [ ! -f "backend/evals/run_evals.py" ]; then
    echo "⚠️  backend/evals/run_evals.py not found — skipping eval."
    echo "    Build phase 2 (golden set + harness) first."
    exit 0
fi

# Run the quick subset (first 20 questions from golden set)
cd backend
echo "Running quick eval subset (20 questions)..."
python evals/run_evals.py --quick --subset 20 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Eval run failed (exit $EXIT_CODE)."
    echo "   Check backend/evals/run_evals.py for errors before continuing."
else
    echo ""
    echo "✅ Eval run complete. Check scores above for regressions."
fi

exit $EXIT_CODE