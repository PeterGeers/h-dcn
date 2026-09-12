#!/usr/bin/env bash
#
# Kiro pre-commit guard (bash).
#
# Invoked by the Kiro PreToolUse hook (.kiro/hooks/ggshield-pre-commit.json)
# with the tool-call JSON on stdin. Only acts when the intercepted command is
# a `git commit`. On a commit it:
#   1. Syncs backend/shared/auth_utils.py -> the auth Lambda layer copy
#      (and stages the layer copy) when they differ.
#   2. Runs the local secret scanner and propagates its exit code, so a
#      finding blocks the commit.
#
# Exit codes:
#   0 = allow the commit (not a commit, or synced + clean scan)
#   1 = block the commit (secret scan found something)

set -uo pipefail

# --- Read the tool-call JSON from stdin ---
input=$(cat)

# Extract toolInput.command; tolerate malformed/empty input.
cmd=$(printf '%s' "$input" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
except Exception:
    print("")
    sys.exit(0)
print(data.get("toolInput", {}).get("command", ""))
' 2>/dev/null || true)

# Only guard actual commits.
case "$cmd" in
    *"git commit"*) : ;;
    *) exit 0 ;;
esac

# --- Auth layer sync ---
src="backend/shared/auth_utils.py"
dst="backend/layers/auth-layer/python/shared/auth_utils.py"
if [ -f "$src" ] && [ -f "$dst" ]; then
    if ! cmp -s "$src" "$dst"; then
        cp "$src" "$dst"
        git add "$dst"
        echo "Auth layer synced"
    fi
fi

# --- Secret scan (propagate exit code) ---
exec sh scripts/scan-secrets-local.sh
