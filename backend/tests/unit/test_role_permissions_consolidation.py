"""
Property-Based Test: Role permissions consolidation preserves function availability

Verifies that all function names from the three local role_permissions.py copies
are available in `shared.role_permissions`, and that constants have the correct types.

**Validates: Requirements 6.1**
"""

import importlib
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


# --- Expected functions from the three local copies ---
# These are all functions that were present in the local role_permissions.py files
# in get_member_self/, update_member/, and hdcn_cognito_admin/

EXPECTED_FUNCTIONS = [
    "get_role_permissions",
    "get_combined_permissions",
    "has_permission",
    "has_new_role_structure",
    "can_edit_field",
    "get_regional_permissions",
    "get_organizational_role_combination",
    "assign_organizational_role",
    "convert_legacy_roles_to_new_structure",
    "validate_organizational_role_structure",
    "get_all_organizational_roles",
    "validate_role_combination",
]

# Constants that should be present with specific types
EXPECTED_CONSTANTS = {
    "DEFAULT_ROLE_PERMISSIONS": dict,
    "NEW_ROLE_STRUCTURE_COMBINATIONS": dict,
    "ORGANIZATIONAL_ROLE_COMBINATIONS": dict,
    "ADMINISTRATIVE_FIELDS": list,
    "PERSONAL_FIELDS": list,
    "MOTORCYCLE_FIELDS": list,
}

# All expected names (functions + constants)
ALL_EXPECTED_NAMES = EXPECTED_FUNCTIONS + list(EXPECTED_CONSTANTS.keys())


# =============================================================================
# Property 3: Role permissions consolidation preserves function availability
# =============================================================================


class TestProperty3RolePermissionsConsolidation:
    """
    # Feature: code-quality-fixes-2026-06, Property 3: Role permissions consolidation

    **Validates: Requirements 6.1**

    For any function name exported by any of the three local role_permissions.py
    copies, the consolidated shared/role_permissions.py module shall export a
    function with the same name and compatible behavior.
    """

    @given(func_name=st.sampled_from(EXPECTED_FUNCTIONS))
    @settings(max_examples=30)
    def test_function_is_available_and_callable(self, func_name: str):
        """
        **Validates: Requirements 6.1**

        For any function name from the local copies, the consolidated
        shared.role_permissions exports a callable with that name.
        """
        import shared.role_permissions as rp

        assert hasattr(rp, func_name), (
            f"shared.role_permissions does not export '{func_name}'"
        )

        func = getattr(rp, func_name)
        assert callable(func), (
            f"shared.role_permissions.{func_name} is not callable"
        )
        note(f"Verified: shared.role_permissions.{func_name} is callable")

    @given(
        const_entry=st.sampled_from(list(EXPECTED_CONSTANTS.items()))
    )
    @settings(max_examples=20)
    def test_constant_is_available_and_correct_type(self, const_entry):
        """
        **Validates: Requirements 6.1**

        For any constant from the local copies, the consolidated
        shared.role_permissions exports it with the correct type
        (dict for permission mappings, list for field lists).
        """
        const_name, expected_type = const_entry
        import shared.role_permissions as rp

        assert hasattr(rp, const_name), (
            f"shared.role_permissions does not export '{const_name}'"
        )

        value = getattr(rp, const_name)
        assert isinstance(value, expected_type), (
            f"shared.role_permissions.{const_name} should be {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )
        note(f"Verified: shared.role_permissions.{const_name} is {expected_type.__name__}")

    @given(name=st.sampled_from(ALL_EXPECTED_NAMES))
    @settings(max_examples=30)
    def test_all_names_importable_from_shared_module(self, name: str):
        """
        **Validates: Requirements 6.1**

        For any expected name (function or constant), verify it can be
        accessed from shared.role_permissions without import errors.
        """
        import shared.role_permissions as rp

        assert hasattr(rp, name), (
            f"shared.role_permissions is missing '{name}'"
        )
        note(f"Verified: '{name}' accessible in shared.role_permissions")

    def test_all_12_functions_present(self):
        """
        **Validates: Requirements 6.1**

        The consolidated module contains all 12 expected functions.
        """
        import shared.role_permissions as rp

        missing = [
            fn for fn in EXPECTED_FUNCTIONS
            if not hasattr(rp, fn) or not callable(getattr(rp, fn))
        ]
        assert not missing, (
            f"Functions missing from shared.role_permissions: {missing}"
        )

    def test_all_6_constants_present(self):
        """
        **Validates: Requirements 6.1**

        The consolidated module contains all 6 expected constants with correct types.
        """
        import shared.role_permissions as rp

        missing = []
        wrong_type = []

        for name, expected_type in EXPECTED_CONSTANTS.items():
            if not hasattr(rp, name):
                missing.append(name)
            elif not isinstance(getattr(rp, name), expected_type):
                wrong_type.append(
                    f"{name}: expected {expected_type.__name__}, "
                    f"got {type(getattr(rp, name)).__name__}"
                )

        assert not missing, f"Constants missing: {missing}"
        assert not wrong_type, f"Constants with wrong type: {wrong_type}"
