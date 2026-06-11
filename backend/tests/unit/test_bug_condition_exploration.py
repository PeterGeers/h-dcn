"""
Bug Condition Exploration Test

This test confirms that the 82 failing tests across 4 categories actually fail
on unfixed code. Each parameterized case runs pytest on a known-failing test file
and asserts it passes (exit code 0). On unfixed code, these assertions WILL FAIL,
which proves the bug exists.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11, 1.12, 1.13**

Categories:
- Category 1 (stale imports): test_presmeet_generate_report.py, test_update_order_items.py
- Category 2 (test bugs): test_admin_properties.py, test_scan_product.py, test_submit_order.py
- Category 3 (handler bugs): test_admin_record_payment.py, test_create_order.py
- Category 4 (obsolete): test_migrate_channel_to_event_id.py, test_migrate_products.py
"""

import subprocess
import os

import pytest


# All test files known to fail, grouped by category
FAILING_TEST_FILES = [
    # Category 1: Stale imports after refactoring
    pytest.param(
        "test_presmeet_generate_report.py",
        id="cat1-stale-import-presmeet-generate-report",
    ),
    pytest.param(
        "test_update_order_items.py",
        id="cat1-stale-import-update-order-items",
    ),
    # Category 2: Test bugs with incomplete mocks or wrong assertions
    pytest.param(
        "test_admin_properties.py",
        id="cat2-test-bug-admin-properties",
    ),
    pytest.param(
        "test_scan_product.py",
        id="cat2-test-bug-scan-product",
    ),
    pytest.param(
        "test_submit_order.py",
        id="cat2-test-bug-submit-order",
    ),
    # Category 3: Real handler bugs with missing input validation
    pytest.param(
        "test_admin_record_payment.py",
        id="cat3-handler-bug-admin-record-payment",
    ),
    pytest.param(
        "test_create_order.py",
        id="cat3-handler-bug-create-order",
    ),
    # Category 4: Obsolete migration tests
    pytest.param(
        "test_migrate_channel_to_event_id.py",
        id="cat4-obsolete-migrate-channel-to-event-id",
    ),
    pytest.param(
        "test_migrate_products.py",
        id="cat4-obsolete-migrate-products",
    ),
]


@pytest.mark.parametrize("test_file", FAILING_TEST_FILES)
def test_bug_condition_test_file_passes(test_file):
    """
    Assert that each known-failing test file passes (exit code 0).

    On UNFIXED code, this test will FAIL for each file, proving the bugs exist.
    After all fixes are applied, this test will PASS, confirming resolution.
    """
    # Determine path to the test file
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    test_path = os.path.join(tests_dir, test_file)

    # Run pytest on the individual test file with short traceback
    # Timeout after 60 seconds to prevent hanging on import errors or infinite loops
    try:
        result = subprocess.run(
            ["pytest", test_path, "--tb=short", "-q"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(tests_dir),  # Run from backend/ directory
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"\n{'='*60}\n"
            f"BUG CONDITION CONFIRMED: {test_file} TIMED OUT (subprocess killed after 60s)\n"
            f"{'='*60}\n"
        )

    # For obsolete migration tests, deletion IS the fix.
    # pytest exit code 4 = "file or directory not found" which means file was deleted.
    if not os.path.exists(test_path):
        # File was deliberately deleted (Category 4 fix) — this is success
        return

    # Assert the test file passes (exit code 0)
    # On unfixed code this will fail, documenting the bug condition
    assert result.returncode == 0, (
        f"\n{'='*60}\n"
        f"BUG CONDITION CONFIRMED: {test_file} FAILS (exit code {result.returncode})\n"
        f"{'='*60}\n"
        f"STDOUT:\n{result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout}\n"
        f"STDERR:\n{result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr}\n"
        f"{'='*60}\n"
    )
