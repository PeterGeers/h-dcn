#!/bin/sh
#
# Install Git Hooks
#
# Copies pre-commit-hook.sh to .git/hooks/pre-commit and sets executable
# permissions. Run this script once after cloning the repository.
#
# Usage: sh install-hooks.sh
#

HOOK_SOURCE="pre-commit-hook.sh"
HOOK_TARGET=".git/hooks/pre-commit"
HOOKS_DIR=".git/hooks"

# Verify the source hook script exists
if [ ! -f "$HOOK_SOURCE" ]; then
    echo "ERROR: $HOOK_SOURCE not found in project root." >&2
    echo "Please run this script from the repository root directory." >&2
    exit 1
fi

# Verify we are in a git repository
if [ ! -d ".git" ]; then
    echo "ERROR: .git directory not found. Are you in the repository root?" >&2
    exit 1
fi

# Create hooks directory if it does not exist
if [ ! -d "$HOOKS_DIR" ]; then
    mkdir -p "$HOOKS_DIR"
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create $HOOKS_DIR directory." >&2
        exit 1
    fi
fi

# Copy the hook script
cp "$HOOK_SOURCE" "$HOOK_TARGET"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to copy $HOOK_SOURCE to $HOOK_TARGET." >&2
    exit 1
fi

# Set executable permissions
chmod +x "$HOOK_TARGET"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to set executable permissions on $HOOK_TARGET." >&2
    exit 1
fi

echo "Pre-commit hook installed successfully: $HOOK_TARGET"
exit 0
