"""
Test runner utility functions.

Extracts pure logic from run-tests.ps1 into testable Python functions.
This module mirrors the exit-code decision logic used by the PowerShell
local test runner script.
"""


def compute_combined_exit_code(backend_exit_code: int, frontend_exit_code: int) -> int:
    """
    Compute the combined exit code for the local test runner.

    The combined exit code is 0 if and only if both the backend and frontend
    exit codes are 0. Otherwise, it returns 1 (non-zero).

    This mirrors the logic in run-tests.ps1:
        if ($backendExitCode -eq 0 -and $frontendExitCode -eq 0) { exit 0 }
        else { exit 1 }

    Args:
        backend_exit_code: The exit code from the backend test suite (pytest).
        frontend_exit_code: The exit code from the frontend test suite (Jest).

    Returns:
        0 if both exit codes are 0, 1 otherwise.
    """
    if backend_exit_code == 0 and frontend_exit_code == 0:
        return 0
    else:
        return 1


# ---------------------------------------------------------------------------
# Tests for the utility logic above.
#
# This module is named test_runner_utils.py and lives under tests/, so pytest
# collects it. Previously it contained only the helper function and NO tests,
# which made pytest exit 5 ("no tests collected") and fail the suite. These
# tests cover compute_combined_exit_code so the module is a valid test file.
# ---------------------------------------------------------------------------
import pytest


@pytest.mark.parametrize(
    "backend_exit,frontend_exit,expected",
    [
        (0, 0, 0),   # both pass -> combined pass
        (1, 0, 1),   # backend fails -> combined fail
        (0, 1, 1),   # frontend fails -> combined fail
        (1, 1, 1),   # both fail -> combined fail
        (2, 0, 1),   # any non-zero backend -> combined fail
        (0, 5, 1),   # any non-zero frontend -> combined fail
    ],
)
def test_compute_combined_exit_code(backend_exit, frontend_exit, expected):
    assert compute_combined_exit_code(backend_exit, frontend_exit) == expected
