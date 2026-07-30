# Feature: risk-management
"""
Unit tests for secret filter edge cases.

Tests each pattern family with known examples and verifies edge cases
where partial matches should NOT trigger detection.

Requirements: 3.2
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'handler'))
from secret_filter.secret_patterns import contains_secret


class TestKnownSecretExamples:
    """Each pattern family matches a known real-world example."""

    def test_aws_access_key(self):
        assert contains_secret('export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE')

    def test_private_key_rsa(self):
        assert contains_secret('echo "-----BEGIN RSA PRIVATE KEY-----"')

    def test_private_key_generic(self):
        assert contains_secret('cat file | grep "BEGIN PRIVATE KEY"')

    def test_private_key_ec(self):
        assert contains_secret('-----BEGIN EC PRIVATE KEY-----')

    def test_private_key_openssh(self):
        assert contains_secret('-----BEGIN OPENSSH PRIVATE KEY-----')

    def test_stripe_secret_key(self):
        # Construct the pattern dynamically to avoid GitHub push protection
        prefix = 'sk_' + 'live_'
        assert contains_secret(f'stripe_key={prefix}abcdefghijklmnop')

    def test_stripe_publishable_key(self):
        prefix = 'pk_' + 'live_'
        assert contains_secret(f'STRIPE_PK={prefix}abcdefghijklmnop')

    def test_mollie_live_key(self):
        assert contains_secret('mollie_key=live_aBcDeFgHiJkLmNoPqRsT')

    def test_mollie_test_key(self):
        assert contains_secret('MOLLIE_API_KEY=test_xYzAbCdEfGhIjKlMnOpQ')

    def test_github_pat(self):
        assert contains_secret(
            'git clone https://ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij@github.com/user/repo'
        )

    def test_gitlab_pat(self):
        assert contains_secret('export GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx')

    def test_google_api_key(self):
        assert contains_secret('API_KEY=AIzaSyA1234567890abcdefghijklmnopqrstuvw')

    def test_slack_bot_token(self):
        assert contains_secret('SLACK_TOKEN=xoxb-123456789012-1234567890123-AbCdEfGhIj')

    def test_slack_user_token(self):
        assert contains_secret('curl -H "Authorization: xoxp-some-long-token-here"')

    def test_bearer_token(self):
        # Construct dynamically to avoid secret scanners flagging test data
        token = 'eyJhbGciOiJ' + 'SUzI1NiJ9.test.signature'
        assert contains_secret(f'curl -H "Authorization: Bearer {token}"')


class TestEdgeCasesNoFalsePositives:
    """Partial matches and lookalikes that should NOT trigger."""

    def test_akia_alone_too_short(self):
        """AKIA without exactly 16 following chars should not match."""
        assert not contains_secret('echo AKIA')
        assert not contains_secret('echo AKIA12345')  # Only 5 chars after

    def test_mollie_test_prefix_too_short(self):
        """test_ with fewer than 20 alphanumeric chars should not match."""
        assert not contains_secret('npm test_results')
        assert not contains_secret('test_short')

    def test_begin_without_private_key(self):
        """BEGIN without PRIVATE KEY should not match."""
        assert not contains_secret('BEGIN TRANSACTION')
        assert not contains_secret('BEGIN WORK')

    def test_normal_bearer_usage(self):
        """Bearer without a token value should not match."""
        assert not contains_secret('echo "Bearer "')

    def test_live_underscore_in_normal_context(self):
        """live_ as part of a short word should not match."""
        assert not contains_secret('go_live_date')

    def test_ghp_too_short(self):
        """ghp_ with fewer than 36 chars should not match."""
        assert not contains_secret('ghp_short')
        assert not contains_secret('ghp_12345678901234567890')  # Only 20 chars

    def test_glpat_too_short(self):
        """glpat- with fewer than 20 chars should not match."""
        assert not contains_secret('glpat-short')

    def test_aiza_too_short(self):
        """AIza with fewer than 35 following chars should not match."""
        assert not contains_secret('AIza1234')

    def test_xox_without_valid_type(self):
        """xox without b/p/o/r/s should not match."""
        assert not contains_secret('xoxa-hugs-and-kisses')
        assert not contains_secret('xoxc-something')
        # Note: xoxo- DOES match because 'o' is in [bpors] (org token)

    def test_normal_commands(self):
        """Common commands that coincidentally have substrings."""
        assert not contains_secret('Get-Process -Name explorer')
        assert not contains_secret('git status')
        assert not contains_secret('npm run test')
        assert not contains_secret('sam deploy --stack-name h-dcn')
        assert not contains_secret('docker build -t myapp .')
        assert not contains_secret('pytest tests/ -v')

    def test_sk_test_not_matched(self):
        """sk_test_ (Stripe test key) is not in the pattern list — only live keys."""
        assert not contains_secret('sk_test_abcdefghij')

    def test_pk_test_not_matched(self):
        """pk_test_ (Stripe test publishable key) is not matched."""
        assert not contains_secret('pk_test_abcdefghij')
