"""
Property-Based Test for Test User Group Configuration Correctness

Feature: test-staging-environment, Property 5: Test user group configuration correctness

For any test user defined in the seed script configuration, the configured group list
SHALL match exactly the groups specified in the requirements (no extra groups, no missing groups).

**Validates: Requirements 7.1**
"""

import os
import sys

import pytest
from hypothesis import given, settings, note
from hypothesis import strategies as st

# Add scripts/ directory to sys.path so we can import from seed-test-data.py
_scripts_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts')
)
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)

# Import TEST_USERS from the seed script (module name uses hyphens → importlib)
import importlib.util

_seed_script_path = os.path.join(_scripts_path, 'seed-test-data.py')
_spec = importlib.util.spec_from_file_location('seed_test_data', _seed_script_path)
_seed_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_seed_module)

TEST_USERS = _seed_module.TEST_USERS


# Expected groups per user — hard-coded from Requirements 7.1 (source of truth)
EXPECTED_GROUPS = {
    "test-admin": {
        "Products_CRUD",
        "Products_Export",
        "Products_Read",
        "Webshop_Management",
        "Members_Read",
        "Members_CRUD",
        "Members_Export",
        "Members_Status_Approve",
        "System_CRUD",
        "System_Logs_Read",
        "System_User_Management",
        "Communication_CRUD",
        "Communication_Read",
        "Communication_Export",
        "Events_CRUD",
        "Events_Read",
        "Events_Export",
        "Regio_All",
        "Regio_Pressmeet",
        "hdcnLeden",
    },
    "test-lid": {
        "hdcnLeden",
        "Regio_Pressmeet",
        "club_test_presmeet",
    },
    "test-treasurer": {
        "Finance_CRUD",
        "Finance_Read",
        "hdcnLeden",
    },
    "test-presmeet": {
        "Regio_Pressmeet",
        "hdcnLeden",
    },
    "test-readonly": {
        "Products_Read",
        "hdcnLeden",
    },
}


class TestProperty5TestUserGroupConfigurationCorrectness:
    """
    Feature: test-staging-environment, Property 5: Test user group configuration correctness

    **Validates: Requirements 7.1**
    """

    @given(user=st.sampled_from(TEST_USERS))
    @settings(max_examples=100)
    def test_user_groups_match_requirements_exactly(self, user):
        """
        **Validates: Requirements 7.1**

        For any test user sampled from the seed config, the set of groups
        configured matches exactly the set specified in requirements (no extra, no missing).
        """
        username = user["username"]
        actual_groups = set(user["groups"])
        expected_groups = EXPECTED_GROUPS[username]

        note(f"username={username}")
        note(f"actual_groups={sorted(actual_groups)}")
        note(f"expected_groups={sorted(expected_groups)}")

        missing = expected_groups - actual_groups
        extra = actual_groups - expected_groups

        assert actual_groups == expected_groups, (
            f"Group mismatch for user '{username}':\n"
            f"  Missing groups: {sorted(missing)}\n"
            f"  Extra groups: {sorted(extra)}"
        )

    @given(user=st.sampled_from(TEST_USERS))
    @settings(max_examples=100)
    def test_all_configured_users_are_in_requirements(self, user):
        """
        **Validates: Requirements 7.1**

        For any test user in the seed config, their username must be present
        in the expected groups mapping (i.e., requirements define their groups).
        """
        username = user["username"]

        note(f"username={username}")

        assert username in EXPECTED_GROUPS, (
            f"User '{username}' exists in seed config but is not defined in requirements"
        )

    def test_requirements_cover_all_seed_users(self):
        """
        **Validates: Requirements 7.1**

        Verify that all users in EXPECTED_GROUPS (from requirements) exist in
        TEST_USERS (seed config), and vice versa. This ensures no user is
        defined in one place but missing from the other.
        """
        seed_usernames = {u["username"] for u in TEST_USERS}
        requirements_usernames = set(EXPECTED_GROUPS.keys())

        missing_from_seed = requirements_usernames - seed_usernames
        missing_from_requirements = seed_usernames - requirements_usernames

        assert seed_usernames == requirements_usernames, (
            f"User set mismatch:\n"
            f"  In requirements but not in seed: {sorted(missing_from_seed)}\n"
            f"  In seed but not in requirements: {sorted(missing_from_requirements)}"
        )
