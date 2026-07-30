"""
Secret pattern detection module.

Mirrors the PowerShell AddToHistoryHandler regex patterns to enable
property-based testing of the secret filter logic in Python (Hypothesis).

Feature: risk-management
Requirements: 3.1, 3.2
"""

import re

# Patterns that indicate a secret value in a command line.
# Each pattern matches a specific type of credential material.
SECRET_PATTERNS: list[str] = [
    r'AKIA[0-9A-Z]{16}',                          # AWS Access Key ID
    r'BEGIN\s+(RSA|DSA|EC|OPENSSH)?\s*PRIVATE\s+KEY',  # Private keys
    r'sk_live_[0-9a-zA-Z]+',                       # Stripe secret key
    r'pk_live_[0-9a-zA-Z]+',                       # Stripe publishable key (live)
    r'(live|test)_[0-9a-zA-Z]{20,}',              # Mollie API keys
    r'ghp_[0-9a-zA-Z]{36,}',                      # GitHub PAT
    r'glpat-[0-9a-zA-Z\-]{20,}',                  # GitLab PAT
    r'AIza[0-9A-Za-z\-_]{35}',                    # Google API key
    r'xox[bpors]-[0-9a-zA-Z\-]+',                 # Slack tokens
    r'Bearer\s+[A-Za-z0-9\-._~+/]+=*',           # Bearer tokens (hardcoded)
]

# Combined pattern for efficient single-pass matching
_COMBINED_PATTERN: re.Pattern[str] = re.compile('|'.join(SECRET_PATTERNS))


def contains_secret(line: str) -> bool:
    """
    Check if a command line contains any secret pattern.

    Returns True if the line matches any known secret pattern,
    indicating it should NOT be written to history.
    Returns False if the line is safe to persist.

    This mirrors the PowerShell AddToHistoryHandler logic:
    - True  → equivalent to SkipAdding (don't write to history)
    - False → equivalent to MemoryAndFile (write normally)
    """
    return bool(_COMBINED_PATTERN.search(line))
