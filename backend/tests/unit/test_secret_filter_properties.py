# Feature: risk-management, Property 1: Secret pattern detection
# Feature: risk-management, Property 2: Non-secret passthrough
"""
Property-based tests for the secret filter module.

Uses Hypothesis to validate that:
1. Any command containing a known secret pattern is detected
2. Commands without secret patterns are allowed through

Requirements: 3.1, 3.2, 3.4, 3.5
"""

import sys
import os
import string

import pytest
from hypothesis import given, strategies as st, settings, assume

# Add handler path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'handler'))
from secret_filter.secret_patterns import contains_secret


# --- Generators ---

def _aws_key() -> st.SearchStrategy[str]:
    """Generate valid AWS access key IDs (AKIA + 16 uppercase alphanumeric)."""
    return st.text(
        alphabet=string.ascii_uppercase + string.digits,
        min_size=16, max_size=16
    ).map(lambda s: f'AKIA{s}')


def _private_key_header() -> st.SearchStrategy[str]:
    """Generate private key BEGIN headers."""
    key_types = st.sampled_from(['RSA', 'DSA', 'EC', 'OPENSSH', ''])
    return key_types.map(
        lambda t: f'BEGIN {t} PRIVATE KEY' if t else 'BEGIN PRIVATE KEY'
    )


def _stripe_secret_key() -> st.SearchStrategy[str]:
    """Generate Stripe secret keys."""
    return st.text(
        alphabet=string.ascii_letters + string.digits,
        min_size=10, max_size=40
    ).map(lambda s: f'sk_live_{s}')


def _stripe_publishable_key() -> st.SearchStrategy[str]:
    """Generate Stripe publishable keys."""
    return st.text(
        alphabet=string.ascii_letters + string.digits,
        min_size=10, max_size=40
    ).map(lambda s: f'pk_live_{s}')


def _mollie_key() -> st.SearchStrategy[str]:
    """Generate Mollie API keys (live_ or test_ + 20+ alphanumeric)."""
    prefix = st.sampled_from(['live_', 'test_'])
    suffix = st.text(
        alphabet=string.ascii_letters + string.digits,
        min_size=20, max_size=40
    )
    return st.tuples(prefix, suffix).map(lambda t: f'{t[0]}{t[1]}')


def _github_pat() -> st.SearchStrategy[str]:
    """Generate GitHub PATs (ghp_ + 36+ alphanumeric)."""
    return st.text(
        alphabet=string.ascii_letters + string.digits,
        min_size=36, max_size=50
    ).map(lambda s: f'ghp_{s}')


def _gitlab_pat() -> st.SearchStrategy[str]:
    """Generate GitLab PATs (glpat- + 20+ alphanumeric/dash)."""
    return st.text(
        alphabet=string.ascii_letters + string.digits + '-',
        min_size=20, max_size=40
    ).map(lambda s: f'glpat-{s}')


def _google_api_key() -> st.SearchStrategy[str]:
    """Generate Google API keys (AIza + 35 alphanumeric/dash/underscore)."""
    return st.text(
        alphabet=string.ascii_letters + string.digits + '-_',
        min_size=35, max_size=35
    ).map(lambda s: f'AIza{s}')


def _slack_token() -> st.SearchStrategy[str]:
    """Generate Slack tokens (xox[bpors]- + alphanumeric/dash)."""
    token_type = st.sampled_from(['b', 'p', 'o', 'r', 's'])
    suffix = st.text(
        alphabet=string.ascii_letters + string.digits + '-',
        min_size=10, max_size=50
    )
    return st.tuples(token_type, suffix).map(lambda t: f'xox{t[0]}-{t[1]}')


def _bearer_token() -> st.SearchStrategy[str]:
    """Generate Bearer token headers."""
    token = st.text(
        alphabet=string.ascii_letters + string.digits + '-._~+/=',
        min_size=10, max_size=80
    )
    return token.map(lambda s: f'Bearer {s}')


def secret_commands() -> st.SearchStrategy[str]:
    """
    Generate command strings containing at least one secret pattern.
    Randomly chooses a pattern type and embeds it in surrounding text.
    """
    secret = st.one_of(
        _aws_key(),
        _private_key_header(),
        _stripe_secret_key(),
        _stripe_publishable_key(),
        _mollie_key(),
        _github_pat(),
        _gitlab_pat(),
        _google_api_key(),
        _slack_token(),
        _bearer_token(),
    )
    prefix = st.text(
        alphabet=string.ascii_letters + string.digits + ' -_=/',
        min_size=0, max_size=30
    )
    suffix = st.text(
        alphabet=string.ascii_letters + string.digits + ' -_=/',
        min_size=0, max_size=30
    )
    return st.tuples(prefix, secret, suffix).map(
        lambda t: f'{t[0]}{t[1]}{t[2]}'
    )


# Safe command alphabet: lowercase letters, digits, spaces, common shell chars
# Deliberately excludes uppercase runs and patterns that could accidentally match
_SAFE_ALPHABET = string.ascii_lowercase + string.digits + ' /-_.'

# Common PowerShell/shell commands that should never match
_SAFE_COMMAND_PREFIXES = [
    'Get-Process', 'Set-Location', 'Get-ChildItem', 'ls -la',
    'git status', 'git push', 'git pull', 'git commit -m',
    'cd ', 'mkdir ', 'rm -rf ', 'npm install', 'npm run build',
    'pip install', 'python -m pytest', 'sam build', 'sam deploy',
    'docker run', 'docker build', 'kubectl get pods',
    'New-Item', 'Remove-Item', 'Copy-Item', 'Move-Item',
    'Write-Host', 'Invoke-WebRequest', 'Select-Object',
    'aws s3 ls', 'aws dynamodb list-tables',
]


def safe_commands() -> st.SearchStrategy[str]:
    """
    Generate plausible commands that should NOT match secret patterns.
    Uses common shell commands with safe arguments.
    """
    prefix = st.sampled_from(_SAFE_COMMAND_PREFIXES)
    # Safe argument: short lowercase/digit string
    arg = st.text(alphabet=_SAFE_ALPHABET, min_size=0, max_size=40)
    return st.tuples(prefix, arg).map(lambda t: f'{t[0]} {t[1]}')


# --- Property Tests ---


# Feature: risk-management, Property 1: Secret pattern detection
class TestSecretPatternDetection:
    """Property 1: Any command containing a secret pattern MUST be detected."""

    @given(command=secret_commands())
    @settings(max_examples=200)
    def test_secrets_are_always_detected(self, command: str):
        """
        For any command string containing at least one secret pattern,
        contains_secret() must return True.

        Validates: Requirements 3.1, 3.2, 3.5
        """
        assert contains_secret(command) is True, (
            f"Secret pattern not detected in: {command!r}"
        )


# Feature: risk-management, Property 2: Non-secret passthrough
class TestNonSecretPassthrough:
    """Property 2: Commands without secrets MUST pass through."""

    @given(command=safe_commands())
    @settings(max_examples=200)
    def test_safe_commands_pass_through(self, command: str):
        """
        For any command string that does NOT contain a secret pattern,
        contains_secret() must return False.

        Validates: Requirements 3.1, 3.4, 3.5
        """
        assert contains_secret(command) is False, (
            f"False positive — safe command flagged as secret: {command!r}"
        )
