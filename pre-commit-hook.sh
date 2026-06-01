#!/bin/sh
#
# Pre-Commit Hook: GitGuardian Secret Scanning & Auth Layer Sync
#
# This hook runs automatically before each commit to:
# 1. Synchronize the auth layer file (backend/shared/auth_utils.py →
#    backend/layers/auth-layer/python/shared/auth_utils.py)
# 2. Run ggshield secret scanning to block commits containing secrets
#
# Designed for Git for Windows sh.exe (POSIX-compliant, no bash extensions).
# Install by copying to .git/hooks/pre-commit or running install-hooks.sh.
#

# --- Auth Layer Synchronization ---
# Keeps the Lambda Layer copy of auth_utils.py in sync with the source.
AUTH_SOURCE="backend/shared/auth_utils.py"
AUTH_LAYER="backend/layers/auth-layer/python/shared/auth_utils.py"

if [ -f "$AUTH_SOURCE" ] && [ -f "$AUTH_LAYER" ]; then
    if ! cmp -s "$AUTH_SOURCE" "$AUTH_LAYER" 2>/dev/null; then
        if cp "$AUTH_SOURCE" "$AUTH_LAYER"; then
            git add "$AUTH_LAYER"
        else
            echo "pre-commit: WARNING - failed to copy auth_utils.py to layer" >&2
        fi
    fi
fi

# --- GitGuardian Secret Scan ---
# Detects secrets in staged files using ggshield.
# Blocks the commit if secrets are found; warns if ggshield is not installed.

if command -v ggshield >/dev/null 2>&1; then
    ggshield secret scan pre-commit
    SCAN_EXIT=$?
    if [ "$SCAN_EXIT" -ne 0 ]; then
        echo "pre-commit: ERROR - ggshield detected secrets in staged files. Commit blocked." >&2
        exit "$SCAN_EXIT"
    fi
else
    echo "pre-commit: WARNING - ggshield is not installed. Skipping secret scan." >&2
fi

exit 0
