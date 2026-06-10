"""
Property-Based Tests for Local Test Runner Exit Code Correctness

Feature: test-staging-environment, Property 3: Local test runner exit code correctness

Validates that the combined exit code logic returns 0 if and only if both
the backend and frontend exit codes are 0.
"""

import os
import sys

import pytest
from hypothesis import given, settings, note
from hypothesis import strategies as st

# Add tests/ directory to path so we can import test_runner_utils
_tests_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)

from test_runner_utils import compute_combined_exit_code


class TestProperty3LocalTestRunnerExitCodeCorrectness:
    """
    # Feature: test-staging-environment, Property 3: Local test runner exit code correctness

    **Validates: Requirements 4.5, 4.6**

    For any pair of (backend_exit_code, frontend_exit_code) integers,
    the combined exit code is 0 if and only if both are 0.
    """

    @given(
        backend_exit_code=st.integers(),
        frontend_exit_code=st.integers(),
    )
    @settings(max_examples=200)
    def test_combined_exit_zero_iff_both_zero(
        self, backend_exit_code: int, frontend_exit_code: int
    ):
        """
        **Validates: Requirements 4.5, 4.6**

        For any pair of integers, combined exit code == 0 iff both inputs == 0.
        """
        result = compute_combined_exit_code(backend_exit_code, frontend_exit_code)

        both_zero = (backend_exit_code == 0 and frontend_exit_code == 0)

        note(
            f"backend={backend_exit_code}, frontend={frontend_exit_code}, "
            f"result={result}, both_zero={both_zero}"
        )

        if both_zero:
            assert result == 0, (
                f"Expected exit code 0 when both inputs are 0, got {result}"
            )
        else:
            assert result != 0, (
                f"Expected non-zero exit code when inputs are "
                f"({backend_exit_code}, {frontend_exit_code}), got {result}"
            )

    @given(
        backend_exit_code=st.integers().filter(lambda x: x != 0),
        frontend_exit_code=st.integers(),
    )
    @settings(max_examples=100)
    def test_nonzero_backend_always_produces_nonzero_combined(
        self, backend_exit_code: int, frontend_exit_code: int
    ):
        """
        **Validates: Requirements 4.5, 4.6**

        If the backend exit code is non-zero, the combined exit code must be non-zero
        regardless of the frontend exit code.
        """
        result = compute_combined_exit_code(backend_exit_code, frontend_exit_code)

        note(f"backend={backend_exit_code}, frontend={frontend_exit_code}, result={result}")

        assert result != 0, (
            f"Expected non-zero combined exit code when backend fails "
            f"(exit={backend_exit_code}), got {result}"
        )

    @given(
        backend_exit_code=st.integers(),
        frontend_exit_code=st.integers().filter(lambda x: x != 0),
    )
    @settings(max_examples=100)
    def test_nonzero_frontend_always_produces_nonzero_combined(
        self, backend_exit_code: int, frontend_exit_code: int
    ):
        """
        **Validates: Requirements 4.5, 4.6**

        If the frontend exit code is non-zero, the combined exit code must be non-zero
        regardless of the backend exit code.
        """
        result = compute_combined_exit_code(backend_exit_code, frontend_exit_code)

        note(f"backend={backend_exit_code}, frontend={frontend_exit_code}, result={result}")

        assert result != 0, (
            f"Expected non-zero combined exit code when frontend fails "
            f"(exit={frontend_exit_code}), got {result}"
        )
