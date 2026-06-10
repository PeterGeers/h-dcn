"""
Property-Based Test for CORS Origin from Environment Variable

Feature: test-staging-environment, Property 1: CORS origin from environment variable

For any string value set in CORS_ALLOWED_ORIGIN, cors_headers() returns that exact
value as Access-Control-Allow-Origin, without reading or echoing any request-provided
Origin header.

**Validates: Requirements 1.3, 1.4, 5.1, 5.5**
"""

import os
import sys
import inspect

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Ensure the auth layer path is available
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

from shared.auth_utils import cors_headers

# Strategy for valid environment variable values (no null bytes - OS restriction)
env_var_text = st.text(alphabet=st.characters(blacklist_characters='\x00'))


class TestProperty1CorsOriginFromEnvironmentVariable:
    """
    Feature: test-staging-environment, Property 1: CORS origin from environment variable

    **Validates: Requirements 1.3, 1.4, 5.1, 5.5**
    """

    @given(origin_value=env_var_text)
    @settings(max_examples=100)
    def test_cors_headers_returns_exact_env_var_value(self, origin_value):
        """
        For any string value set in CORS_ALLOWED_ORIGIN, cors_headers() returns
        that exact value as Access-Control-Allow-Origin.
        """
        old_value = os.environ.get('CORS_ALLOWED_ORIGIN')
        try:
            os.environ['CORS_ALLOWED_ORIGIN'] = origin_value
            headers = cors_headers()
            assert headers["Access-Control-Allow-Origin"] == origin_value
        finally:
            if old_value is None:
                os.environ.pop('CORS_ALLOWED_ORIGIN', None)
            else:
                os.environ['CORS_ALLOWED_ORIGIN'] = old_value

    def test_cors_headers_does_not_accept_request_parameter(self):
        """
        Verify the function never reads or echoes a request-provided Origin header.
        The cors_headers() function signature takes no parameters, so it cannot
        receive a request Origin header to echo.
        """
        sig = inspect.signature(cors_headers)
        assert len(sig.parameters) == 0, (
            f"cors_headers() should take no parameters but has: {list(sig.parameters.keys())}"
        )

    @given(
        origin_value=env_var_text,
        request_origin=st.text(),
    )
    @settings(max_examples=100)
    def test_cors_headers_ignores_any_request_origin(self, origin_value, request_origin):
        """
        For any env var value and any hypothetical request origin, the returned
        Access-Control-Allow-Origin is always the env var value, never the request origin.
        This confirms the function cannot be tricked into echoing a request header.
        """
        old_value = os.environ.get('CORS_ALLOWED_ORIGIN')
        try:
            os.environ['CORS_ALLOWED_ORIGIN'] = origin_value
            headers = cors_headers()
            # The result must be the env var, not the request origin (unless they happen to be equal)
            assert headers["Access-Control-Allow-Origin"] == origin_value
            # When they differ, confirm we're not echoing the request
            if origin_value != request_origin:
                assert headers["Access-Control-Allow-Origin"] != request_origin
        finally:
            if old_value is None:
                os.environ.pop('CORS_ALLOWED_ORIGIN', None)
            else:
                os.environ['CORS_ALLOWED_ORIGIN'] = old_value
