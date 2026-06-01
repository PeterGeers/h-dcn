#!/bin/sh
#
# ShellCheck Validation Script
#
# Runs shellcheck --shell=sh on all hook scripts to verify POSIX compliance.
# Exits non-zero if any issues are found.
#
# Usage: sh validate-hooks.sh
#

ERRORS=0

# Check if shellcheck is available
if ! command -v shellcheck >/dev/null 2>&1; then
    echo "WARNING: shellcheck is not installed." >&2
    echo "" >&2
    echo "Install shellcheck to validate POSIX compliance of hook scripts:" >&2
    echo "  - apt-get install shellcheck        (Debian/Ubuntu)" >&2
    echo "  - brew install shellcheck            (macOS)" >&2
    echo "  - scoop install shellcheck           (Windows/Scoop)" >&2
    echo "  - choco install shellcheck           (Windows/Chocolatey)" >&2
    echo "  - https://github.com/koalaman/shellcheck#installing" >&2
    exit 2
fi

echo "Running ShellCheck validation..."
echo ""

# Validate pre-commit-hook.sh
if [ -f "pre-commit-hook.sh" ]; then
    echo "Checking pre-commit-hook.sh..."
    if shellcheck --shell=sh pre-commit-hook.sh; then
        echo "  PASS: pre-commit-hook.sh"
    else
        echo "  FAIL: pre-commit-hook.sh" >&2
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  SKIP: pre-commit-hook.sh not found" >&2
fi

echo ""

# Validate install-hooks.sh
if [ -f "install-hooks.sh" ]; then
    echo "Checking install-hooks.sh..."
    if shellcheck --shell=sh install-hooks.sh; then
        echo "  PASS: install-hooks.sh"
    else
        echo "  FAIL: install-hooks.sh" >&2
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  SKIP: install-hooks.sh not found" >&2
fi

echo ""

# Report results
if [ "$ERRORS" -eq 0 ]; then
    echo "All checks passed."
    exit 0
else
    echo "FAILED: $ERRORS script(s) had ShellCheck issues." >&2
    exit 1
fi
