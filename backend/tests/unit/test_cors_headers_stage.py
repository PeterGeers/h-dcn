"""
Unit tests for cors_headers() stage behavior.

Validates that the CORS origin is correctly read from the CORS_ALLOWED_ORIGIN
environment variable for test and production stages, and falls back to '*'
when the variable is not set.

Requirements: 1.3, 1.4, 5.1, 5.5
"""

import os
import pytest


class TestCorsHeadersStageBehavior:
    """Test cors_headers() returns the correct origin per stage."""

    def test_returns_testportal_origin_when_env_var_set(self, monkeypatch):
        """cors_headers() returns https://testportal.h-dcn.nl when CORS_ALLOWED_ORIGIN is set to that value."""
        monkeypatch.setenv('CORS_ALLOWED_ORIGIN', 'https://testportal.h-dcn.nl')

        from shared.auth_utils import cors_headers
        headers = cors_headers()

        assert headers['Access-Control-Allow-Origin'] == 'https://testportal.h-dcn.nl'

    def test_returns_portal_origin_when_env_var_set(self, monkeypatch):
        """cors_headers() returns https://portal.h-dcn.nl when CORS_ALLOWED_ORIGIN is set to that value."""
        monkeypatch.setenv('CORS_ALLOWED_ORIGIN', 'https://portal.h-dcn.nl')

        from shared.auth_utils import cors_headers
        headers = cors_headers()

        assert headers['Access-Control-Allow-Origin'] == 'https://portal.h-dcn.nl'

    def test_returns_wildcard_when_env_var_not_set(self, monkeypatch):
        """cors_headers() returns '*' when CORS_ALLOWED_ORIGIN is not set (default/backward compat)."""
        monkeypatch.delenv('CORS_ALLOWED_ORIGIN', raising=False)

        from shared.auth_utils import cors_headers
        headers = cors_headers()

        assert headers['Access-Control-Allow-Origin'] == '*'
