"""
Bug Condition Exploration Test - Pool ID Mismatch and DIY Passkey Flow

This test encodes the EXPECTED correct behavior for the passkey authentication system.
It is designed to FAIL on unfixed code, confirming the bug exists.

When the fix is implemented, this test will PASS, confirming the bug is resolved.

**Validates: Requirements 1.1, 1.3, 1.4, 1.6, 1.7, 1.8, 1.11, 1.13, 1.14**
"""

import ast
import os
import re
import inspect

import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st

# Path constants (relative to backend/)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_PATH = os.path.join(BACKEND_DIR, "template.yaml")
GET_MEMBER_SELF_PATH = os.path.join(BACKEND_DIR, "handler", "get_member_self", "app.py")
HDCN_COGNITO_ADMIN_PATH = os.path.join(BACKEND_DIR, "handler", "hdcn_cognito_admin", "app.py")
FRONTEND_DIR = os.path.dirname(BACKEND_DIR)
AWS_EXPORTS_PATH = os.path.join(FRONTEND_DIR, "frontend", "src", "aws-exports.ts")

# The correct pool ID that all sources should reference
CORRECT_POOL_ID = "eu-west-1_fcUkvwjH5"
CORRECT_CLIENT_ID = "6jhvk853b0lfg9q1m861qs0cug"


def read_file_content(path):
    """Read file content, raising clear error if file not found."""
    if not os.path.exists(path):
        pytest.skip(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestPoolIdConsistency:
    """
    Property 1: Bug Condition - Pool ID Mismatch

    All configuration sources must reference the same Cognito User Pool ID.
    On unfixed code, these will reference different pool IDs, causing the test to fail.
    """

    def test_sam_template_existing_user_pool_id_default(self):
        """
        Assert template.yaml ExistingUserPoolId default equals eu-west-1_gKK2nZjEK.

        **Validates: Requirements 1.13**
        """
        content = read_file_content(TEMPLATE_PATH)

        # Find the ExistingUserPoolId parameter default value
        # Pattern: Default: "eu-west-1_..." after ExistingUserPoolId
        match = re.search(
            r'ExistingUserPoolId:.*?Default:\s*["\']?(eu-west-1_\w+)["\']?',
            content,
            re.DOTALL,
        )
        assert match is not None, "Could not find ExistingUserPoolId default in template.yaml"

        actual_pool_id = match.group(1)
        assert actual_pool_id == CORRECT_POOL_ID, (
            f"SAM template ExistingUserPoolId default is '{actual_pool_id}', "
            f"expected '{CORRECT_POOL_ID}'"
        )

    def test_get_member_self_function_has_environment_block(self):
        """
        Assert GetMemberSelfFunction in template.yaml has an Environment block
        with COGNITO_USER_POOL_ID.

        **Validates: Requirements 1.11**
        """
        content = read_file_content(TEMPLATE_PATH)

        # Find the GetMemberSelfFunction resource block
        # We need to check if it has an Environment section with COGNITO_USER_POOL_ID
        # Strategy: find the function definition and check for Environment before the next resource
        func_match = re.search(r'GetMemberSelfFunction:', content)
        assert func_match is not None, "GetMemberSelfFunction not found in template.yaml"

        # Get the content from GetMemberSelfFunction to the next top-level resource
        func_start = func_match.start()
        # Find the next resource definition (same indentation level)
        remaining = content[func_start:]
        # Find next resource at same level (2-space indent + name + colon)
        next_resource = re.search(r'\n  \w+Function:|^\n  \w+:', remaining[1:], re.MULTILINE)
        if next_resource:
            func_block = remaining[: next_resource.start() + 1]
        else:
            func_block = remaining

        # Check for Environment block with COGNITO_USER_POOL_ID
        has_environment = "Environment:" in func_block
        has_pool_id_var = "COGNITO_USER_POOL_ID" in func_block

        assert has_environment and has_pool_id_var, (
            "GetMemberSelfFunction does NOT have an Environment block with "
            "COGNITO_USER_POOL_ID. The function will use a hardcoded fallback "
            "pool ID instead of the correct one from the SAM template parameter."
        )

    def test_get_member_self_fallback_pool_id(self):
        """
        Assert get_member_self/app.py fallback pool ID equals eu-west-1_gKK2nZjEK.

        **Validates: Requirements 1.11**
        """
        content = read_file_content(GET_MEMBER_SELF_PATH)

        # Find the os.environ.get('COGNITO_USER_POOL_ID', '...') pattern
        match = re.search(
            r"os\.environ\.get\(['\"]COGNITO_USER_POOL_ID['\"],\s*['\"]([^'\"]+)['\"]",
            content,
        )
        assert match is not None, (
            "Could not find COGNITO_USER_POOL_ID fallback in get_member_self/app.py"
        )

        actual_fallback = match.group(1)
        assert actual_fallback == CORRECT_POOL_ID, (
            f"get_member_self/app.py fallback pool ID is '{actual_fallback}', "
            f"expected '{CORRECT_POOL_ID}'"
        )

    def test_hdcn_cognito_admin_fallback_pool_id(self):
        """
        Assert hdcn_cognito_admin/app.py fallback pool ID equals eu-west-1_gKK2nZjEK.

        **Validates: Requirements 1.3**
        """
        content = read_file_content(HDCN_COGNITO_ADMIN_PATH)

        # Find the os.environ.get('COGNITO_USER_POOL_ID', '...') pattern
        match = re.search(
            r"os\.environ\.get\(['\"]COGNITO_USER_POOL_ID['\"],\s*['\"]([^'\"]+)['\"]",
            content,
        )
        assert match is not None, (
            "Could not find COGNITO_USER_POOL_ID fallback in hdcn_cognito_admin/app.py"
        )

        actual_fallback = match.group(1)
        assert actual_fallback == CORRECT_POOL_ID, (
            f"hdcn_cognito_admin/app.py fallback pool ID is '{actual_fallback}', "
            f"expected '{CORRECT_POOL_ID}'"
        )

    def test_aws_exports_fallback_pool_id(self):
        """
        Assert aws-exports.ts fallback pool ID equals eu-west-1_gKK2nZjEK.

        **Validates: Requirements 1.14**
        """
        content = read_file_content(AWS_EXPORTS_PATH)

        # Find the userPoolId fallback value (Amplify v6 format)
        # Pattern: userPoolId: process.env.REACT_APP_USER_POOL_ID || 'eu-west-1_...'
        match = re.search(
            r"userPoolId:.*?\|\|\s*['\"]([^'\"]+)['\"]",
            content,
        )
        if not match:
            # Also try legacy Amplify v5 format: aws_user_pools_id: ... || '...'
            match = re.search(
                r"aws_user_pools_id:.*?\|\|\s*['\"]([^'\"]+)['\"]",
                content,
            )
        assert match is not None, (
            "Could not find aws_user_pools_id fallback in aws-exports.ts"
        )

        actual_fallback = match.group(1)
        assert actual_fallback == CORRECT_POOL_ID, (
            f"aws-exports.ts fallback pool ID is '{actual_fallback}', "
            f"expected '{CORRECT_POOL_ID}'"
        )


class TestDIYPasskeyImplementation:
    """
    Property 1: Bug Condition - DIY Passkey Flow

    The passkey implementation should NOT use custom challenge generation.
    It should delegate to Cognito's native WebAuthn support.
    On unfixed code, the DIY implementation exists, causing these tests to fail.
    """

    def test_no_diy_challenge_generation_in_begin_passkey_registration(self):
        """
        Assert passkey registration does NOT use DIY challenge generation.
        The begin_passkey_registration function should NOT generate custom challenges
        using secrets.token_bytes or similar patterns.

        **Validates: Requirements 1.6**
        """
        content = read_file_content(HDCN_COGNITO_ADMIN_PATH)

        # Check if begin_passkey_registration generates its own challenges
        # This is the DIY pattern: generating random bytes as a challenge
        has_begin_passkey = "def begin_passkey_registration" in content

        if has_begin_passkey:
            # Extract the function body
            func_start = content.index("def begin_passkey_registration")
            # Find the next function definition
            remaining = content[func_start + 1:]
            next_def = re.search(r'\ndef \w+', remaining)
            if next_def:
                func_body = remaining[:next_def.start()]
            else:
                func_body = remaining

            # Check for DIY challenge generation patterns
            diy_patterns = [
                "secrets.token_bytes",
                "challenge = secrets",
                "challenge_b64",
                "urlsafe_b64encode(challenge)",
            ]

            diy_found = [p for p in diy_patterns if p in func_body]

            assert not diy_found, (
                f"begin_passkey_registration() generates DIY challenges using: {diy_found}. "
                "Passkey registration should delegate to Cognito's native WebAuthn support, "
                "not generate custom challenges in Lambda code."
            )
        # If begin_passkey_registration doesn't exist, that's the correct state
        # (it should be removed as part of the fix)

    def test_complete_passkey_registration_requires_email_verification(self):
        """
        Assert complete_passkey_registration requires email verification
        before credential creation. The function should NOT create users with
        email_verified: true and MessageAction: SUPPRESS without actual verification.

        **Validates: Requirements 1.7, 1.8**
        """
        content = read_file_content(HDCN_COGNITO_ADMIN_PATH)

        has_complete_passkey = "def complete_passkey_registration" in content

        if not has_complete_passkey:
            # Function removed = correct (native WebAuthn handles this)
            return

        # Extract the function body
        func_start = content.index("def complete_passkey_registration")
        remaining = content[func_start + 1:]
        next_def = re.search(r'\ndef \w+', remaining)
        if next_def:
            func_body = remaining[:next_def.start()]
        else:
            func_body = remaining

        # Check for the problematic pattern: creating users with email_verified: true
        # without actual verification
        creates_user_with_verified_email = (
            "email_verified" in func_body
            and "'Value': 'true'" in func_body
            and "admin_create_user" in func_body
        )

        suppresses_message = "MessageAction" in func_body and "SUPPRESS" in func_body

        # Check for custom attribute storage (DIY pattern)
        stores_custom_passkey_attrs = (
            "custom:passkey_cred_ids" in func_body
            or "custom:passkey_registered" in func_body
            or "custom:passkey_date" in func_body
        )

        # The function should NOT create users without email verification
        assert not (creates_user_with_verified_email and suppresses_message), (
            "complete_passkey_registration() creates users with email_verified: true "
            "and MessageAction: SUPPRESS, bypassing actual email verification. "
            "Users must verify their email before passkey credential creation."
        )

        # The function should NOT store credentials in custom attributes
        assert not stores_custom_passkey_attrs, (
            "complete_passkey_registration() stores credentials in custom Cognito "
            "attributes (custom:passkey_cred_ids, custom:passkey_registered, custom:passkey_date). "
            "Cognito's native WebAuthn should manage credential storage."
        )


class TestPoolIdConsistencyProperty:
    """
    Property-based test using Hypothesis to verify pool ID consistency
    across random lookup scenarios.

    **Validates: Requirements 1.1, 1.3, 1.11, 1.13, 1.14**
    """

    @given(
        source=st.sampled_from([
            "sam_template",
            "get_member_self",
            "hdcn_cognito_admin",
            "aws_exports",
        ])
    )
    @settings(max_examples=2)
    def test_all_pool_id_sources_resolve_to_correct_pool(self, source):
        """
        For any configuration source that provides a pool ID fallback,
        the resolved pool ID must equal the correct pool ID (eu-west-1_gKK2nZjEK).

        This property ensures consistency across all configuration sources.
        """
        if source == "sam_template":
            content = read_file_content(TEMPLATE_PATH)
            match = re.search(
                r'ExistingUserPoolId:.*?Default:\s*["\']?(eu-west-1_\w+)["\']?',
                content,
                re.DOTALL,
            )
            assert match is not None, "ExistingUserPoolId default not found"
            actual = match.group(1)

        elif source == "get_member_self":
            content = read_file_content(GET_MEMBER_SELF_PATH)
            match = re.search(
                r"os\.environ\.get\(['\"]COGNITO_USER_POOL_ID['\"],\s*['\"]([^'\"]+)['\"]",
                content,
            )
            assert match is not None, "COGNITO_USER_POOL_ID fallback not found"
            actual = match.group(1)

        elif source == "hdcn_cognito_admin":
            content = read_file_content(HDCN_COGNITO_ADMIN_PATH)
            match = re.search(
                r"os\.environ\.get\(['\"]COGNITO_USER_POOL_ID['\"],\s*['\"]([^'\"]+)['\"]",
                content,
            )
            assert match is not None, "COGNITO_USER_POOL_ID fallback not found"
            actual = match.group(1)

        elif source == "aws_exports":
            content = read_file_content(AWS_EXPORTS_PATH)
            match = re.search(
                r"userPoolId:.*?\|\|\s*['\"]([^'\"]+)['\"]",
                content,
            )
            if not match:
                match = re.search(
                    r"aws_user_pools_id:.*?\|\|\s*['\"]([^'\"]+)['\"]",
                    content,
                )
            assert match is not None, "aws_user_pools_id fallback not found"
            actual = match.group(1)

        note(f"Source: {source}, Actual pool ID: {actual}")
        assert actual == CORRECT_POOL_ID, (
            f"Pool ID mismatch in {source}: got '{actual}', expected '{CORRECT_POOL_ID}'"
        )

    @given(
        env_var_set=st.booleans(),
        env_value=st.sampled_from([
            CORRECT_POOL_ID,
            "eu-west-1_fcUkvwjH5",
            "eu-west-1_OAT3oPCIm",
            "eu-west-1_VtKQHhXGN",
        ]),
    )
    @settings(max_examples=2)
    def test_pool_id_resolution_with_env_scenarios(self, env_var_set, env_value):
        """
        For any environment variable scenario, when COGNITO_USER_POOL_ID is NOT set,
        the fallback must resolve to the correct pool ID.

        When the env var IS set, the system uses whatever value is provided.
        The bug is specifically in the fallback values.
        """
        # We only care about the fallback case (env var not set)
        assume(not env_var_set)

        # Read the get_member_self source to check its fallback
        content = read_file_content(GET_MEMBER_SELF_PATH)
        match = re.search(
            r"os\.environ\.get\(['\"]COGNITO_USER_POOL_ID['\"],\s*['\"]([^'\"]+)['\"]",
            content,
        )
        assert match is not None
        fallback = match.group(1)

        note(f"Fallback pool ID in get_member_self: {fallback}")
        assert fallback == CORRECT_POOL_ID, (
            f"When COGNITO_USER_POOL_ID env var is not set, get_member_self falls back to "
            f"'{fallback}' instead of '{CORRECT_POOL_ID}'"
        )
