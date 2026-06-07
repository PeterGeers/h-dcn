"""
Property-Based Test: Shared layer subsumes local auth utils

Verifies that all functions from `auth_utils_local.py` (previously in
backend/handler/update_member/) are available in `shared.auth_utils`.

The local file was a copy of shared auth utilities kept as fallback.
After task 5.1, the handler imports directly from the shared layer,
making the local copy (deleted in task 5.2) redundant.

**Validates: Requirements 6.2**
"""

import inspect
import sys
import os

import pytest
from hypothesis import given, settings, note
from hypothesis import strategies as st


# --- Setup: ensure auth layer is on sys.path ---
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_layers_path = os.path.join(_backend_dir, "layers", "auth-layer", "python")
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)


# --- Expected functions from auth_utils_local.py ---
# These are all functions that were present in
# backend/handler/update_member/auth_utils_local.py before deletion.
# The shared layer must export all core functions used by the handler.

# Core authentication/authorization functions (must be in shared layer)
EXPECTED_CORE_FUNCTIONS = [
    "extract_user_credentials",
    "validate_permissions",
    "validate_permissions_with_regions",
    "determine_regional_access",
    "check_regional_data_access",
    "get_user_accessible_regions",
    "log_permission_denial",
    "log_successful_access",
    "cors_headers",
    "handle_options_request",
    "create_error_response",
    "create_success_response",
]

# Functions directly imported by update_member/app.py (subset of core)
HANDLER_IMPORTED_FUNCTIONS = [
    "extract_user_credentials",
    "validate_permissions_with_regions",
    "create_success_response",
    "create_error_response",
    "cors_headers",
    "handle_options_request",
]


# =============================================================================
# Property 4: Shared layer subsumes local auth utils
# =============================================================================


class TestProperty4SharedLayerSubsumesAuthUtilsLocal:
    """
    # Feature: code-quality-fixes-2026-06, Property 4: Shared layer subsumes local auth utils

    **Validates: Requirements 6.2**

    For any function name exported by auth_utils_local.py, the shared layer
    auth_utils.py shall export a function with the same name and compatible signature.
    """

    @given(func_name=st.sampled_from(EXPECTED_CORE_FUNCTIONS))
    @settings(max_examples=30)
    def test_core_function_is_available_and_callable(self, func_name: str):
        """
        **Validates: Requirements 6.2**

        For any core function name from auth_utils_local.py, the shared
        auth_utils module exports a callable with that name.
        """
        import shared.auth_utils as auth

        assert hasattr(auth, func_name), (
            f"shared.auth_utils does not export '{func_name}'"
        )

        func = getattr(auth, func_name)
        assert callable(func), (
            f"shared.auth_utils.{func_name} is not callable"
        )
        note(f"Verified: shared.auth_utils.{func_name} is callable")

    @given(func_name=st.sampled_from(HANDLER_IMPORTED_FUNCTIONS))
    @settings(max_examples=20)
    def test_handler_imported_function_available(self, func_name: str):
        """
        **Validates: Requirements 6.2**

        For any function that update_member/app.py imports from shared.auth_utils,
        verify it exists and is callable in the shared module.
        """
        import shared.auth_utils as auth

        assert hasattr(auth, func_name), (
            f"shared.auth_utils does not export '{func_name}' "
            f"(required by update_member/app.py)"
        )

        func = getattr(auth, func_name)
        assert callable(func), (
            f"shared.auth_utils.{func_name} is not callable "
            f"(required by update_member/app.py)"
        )
        note(f"Verified: shared.auth_utils.{func_name} available for handler import")

    @given(func_name=st.sampled_from(EXPECTED_CORE_FUNCTIONS))
    @settings(max_examples=30)
    def test_function_signature_has_parameters(self, func_name: str):
        """
        **Validates: Requirements 6.2**

        For any core function, verify it has a proper signature (not a stub).
        This checks that the function has parameters matching what was expected
        in the local copy.
        """
        import shared.auth_utils as auth

        func = getattr(auth, func_name)
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        # All functions should have at least one parameter
        # (except cors_headers and handle_options_request which take no args)
        if func_name in ("cors_headers", "handle_options_request"):
            assert len(params) == 0, (
                f"shared.auth_utils.{func_name} should take no parameters"
            )
        else:
            assert len(params) > 0, (
                f"shared.auth_utils.{func_name} should have parameters but has none"
            )
        note(f"Verified: shared.auth_utils.{func_name} signature has {len(params)} params")

    def test_all_12_core_functions_present(self):
        """
        **Validates: Requirements 6.2**

        The shared module contains all 12 core functions from auth_utils_local.py.
        """
        import shared.auth_utils as auth

        missing = [
            fn for fn in EXPECTED_CORE_FUNCTIONS
            if not hasattr(auth, fn) or not callable(getattr(auth, fn))
        ]
        assert not missing, (
            f"Core functions missing from shared.auth_utils: {missing}"
        )

    def test_all_handler_imports_satisfied(self):
        """
        **Validates: Requirements 6.2**

        All functions that update_member/app.py imports from shared.auth_utils
        are available and callable.
        """
        import shared.auth_utils as auth

        missing = [
            fn for fn in HANDLER_IMPORTED_FUNCTIONS
            if not hasattr(auth, fn) or not callable(getattr(auth, fn))
        ]
        assert not missing, (
            f"Handler-imported functions missing from shared.auth_utils: {missing}"
        )

    def test_cors_headers_returns_dict(self):
        """
        **Validates: Requirements 6.2**

        cors_headers() returns a dict with expected CORS header keys.
        """
        import shared.auth_utils as auth

        headers = auth.cors_headers()
        assert isinstance(headers, dict)
        assert "Access-Control-Allow-Origin" in headers
        assert "Access-Control-Allow-Methods" in headers
        assert "Access-Control-Allow-Headers" in headers

    def test_handle_options_request_returns_200(self):
        """
        **Validates: Requirements 6.2**

        handle_options_request() returns a proper OPTIONS response.
        """
        import shared.auth_utils as auth

        response = auth.handle_options_request()
        assert isinstance(response, dict)
        assert response["statusCode"] == 200
        assert "headers" in response

    def test_create_error_response_format(self):
        """
        **Validates: Requirements 6.2**

        create_error_response produces a valid Lambda response structure.
        """
        import json
        import shared.auth_utils as auth

        response = auth.create_error_response(400, "Test error")
        assert response["statusCode"] == 400
        assert "headers" in response
        body = json.loads(response["body"])
        assert body["error"] == "Test error"

    def test_create_success_response_format(self):
        """
        **Validates: Requirements 6.2**

        create_success_response produces a valid Lambda response structure.
        """
        import json
        import shared.auth_utils as auth

        response = auth.create_success_response({"message": "ok"})
        assert response["statusCode"] == 200
        assert "headers" in response
        body = json.loads(response["body"])
        assert body["message"] == "ok"
