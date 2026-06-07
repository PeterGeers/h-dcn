"""
Property-Based Test: Backend split preserves public API

Verifies that all 31 original function names from hdcn_cognito_admin/app.py
remain importable from the refactored sub-modules, and that the router
app.py still exposes a callable lambda_handler.

**Validates: Requirements 1.1**
"""

import importlib
import sys
import os

import pytest
from hypothesis import given, settings, note
from hypothesis import strategies as st


# --- Setup: add handler directory to sys.path for imports ---
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_handler_dir = os.path.join(_backend_dir, "handler", "hdcn_cognito_admin")
if _handler_dir not in sys.path:
    sys.path.insert(0, _handler_dir)


# --- Expected function registry per sub-module ---

EXPECTED_MODULES = {
    "user_operations": [
        "get_users",
        "verify_user_exists",
        "create_user",
        "update_user",
        "delete_user",
        "import_users",
        "passwordless_signup",
        "passkey_migration_check",
    ],
    "group_operations": [
        "get_groups",
        "create_group",
        "delete_group",
        "add_user_to_group",
        "remove_user_from_group",
        "get_user_groups",
        "import_groups",
        "assign_user_groups",
        "get_users_in_group",
    ],
    "auth_operations": [
        "get_auth_login",
        "get_auth_permissions",
        "get_pool_info",
        "calculate_user_permissions",
    ],
    "role_operations": [
        "get_user_roles",
        "assign_user_roles_auth",
        "remove_user_role_auth",
        "validate_role_assignment_rules",
        "validate_role_assignment_permission",
        "calculate_user_permissions",
    ],
    "permission_utils": [
        "validate_field_permissions",
        "get_user_field_permissions",
        "check_role_permission",
        "get_role_summary",
    ],
}

# All unique function names across all sub-modules
# 31 total references, but calculate_user_permissions is in both auth_operations
# and role_operations, so the unique count is 30.
ALL_FUNCTION_NAMES = sorted(set(
    fn for fns in EXPECTED_MODULES.values() for fn in fns
))


# =============================================================================
# Property 1: Backend split preserves public API
# =============================================================================


class TestProperty1BackendSplitPreservesPublicAPI:
    """
    # Feature: code-quality-fixes-2026-06, Property 1: Backend split preserves public API

    **Validates: Requirements 1.1**

    For any function name that was exported by the original hdcn_cognito_admin/app.py,
    the refactored module structure shall export a callable with the same name.
    """

    def test_all_expected_unique_function_names_exist(self):
        """
        **Validates: Requirements 1.1**

        Verify the union of all sub-module functions contains exactly 30 unique names.
        (31 total across sub-modules, but calculate_user_permissions appears in both
        auth_operations and role_operations, yielding 30 unique names.)
        """
        # 8 + 9 + 4 + 6 + 4 = 31 total, minus 1 shared = 30 unique
        assert len(ALL_FUNCTION_NAMES) == 30, (
            f"Expected 30 unique function names, got {len(ALL_FUNCTION_NAMES)}: {ALL_FUNCTION_NAMES}"
        )

    @given(module_name=st.sampled_from(list(EXPECTED_MODULES.keys())))
    @settings(max_examples=20)
    def test_submodule_is_importable(self, module_name: str):
        """
        **Validates: Requirements 1.1**

        For any sub-module name, the module can be imported without errors.
        """
        # Clear cached module to avoid stale imports
        if module_name in sys.modules:
            del sys.modules[module_name]

        module = importlib.import_module(module_name)
        assert module is not None
        note(f"Successfully imported {module_name}")

    @given(
        module_and_func=st.sampled_from([
            (mod, fn)
            for mod, fns in EXPECTED_MODULES.items()
            for fn in fns
        ])
    )
    @settings(max_examples=50)
    def test_function_is_importable_and_callable(self, module_and_func):
        """
        **Validates: Requirements 1.1**

        For any (module, function_name) pair from the expected registry,
        the function is importable and callable.
        """
        module_name, func_name = module_and_func

        # Clear cached module
        if module_name in sys.modules:
            del sys.modules[module_name]

        module = importlib.import_module(module_name)
        assert hasattr(module, func_name), (
            f"Module '{module_name}' does not export '{func_name}'"
        )

        func = getattr(module, func_name)
        assert callable(func), (
            f"'{module_name}.{func_name}' is not callable"
        )
        note(f"Verified: {module_name}.{func_name} is callable")

    def test_calculate_user_permissions_in_both_modules(self):
        """
        **Validates: Requirements 1.1**

        calculate_user_permissions appears in both auth_operations and role_operations.
        Both must be callable.
        """
        for module_name in ["auth_operations", "role_operations"]:
            if module_name in sys.modules:
                del sys.modules[module_name]

            module = importlib.import_module(module_name)
            assert hasattr(module, "calculate_user_permissions"), (
                f"'{module_name}' missing calculate_user_permissions"
            )
            assert callable(getattr(module, "calculate_user_permissions"))

    def test_router_app_has_callable_lambda_handler(self):
        """
        **Validates: Requirements 1.1**

        The router app.py exposes a callable lambda_handler entry point.
        """
        # We need to mock the shared auth layer imports since they won't
        # be available in a plain test environment. The important thing is
        # that the module structure is correct and lambda_handler is defined.
        # The conftest.py already adds the layers path, so shared.auth_utils
        # should be importable.
        if "app" in sys.modules:
            del sys.modules["app"]

        app = importlib.import_module("app")
        assert hasattr(app, "lambda_handler"), (
            "app.py does not export 'lambda_handler'"
        )
        assert callable(app.lambda_handler), (
            "app.lambda_handler is not callable"
        )
