"""
Bug Condition Exploration Test - SAM Template Circular Dependency via MyApi Reference

This test encodes the EXPECTED correct behavior: CreateOrderFunction's MOLLIE_WEBHOOK_URL
environment variable should NOT contain a ${MyApi} reference, because that creates a
circular dependency with the API Gateway PermissionStage resources.

It is designed to FAIL on unfixed code, confirming the bug exists.
When the fix is implemented, this test will PASS, confirming the bug is resolved.

**Validates: Requirements 1.1, 1.2, 2.1, 2.2**
"""

import os
import re

import pytest
from hypothesis import given, settings, note, assume
from hypothesis import strategies as st

# Path to the SAM template
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_PATH = os.path.join(BACKEND_DIR, "template.yaml")


def read_template():
    """Read the SAM template content."""
    if not os.path.exists(TEMPLATE_PATH):
        pytest.skip(f"Template not found: {TEMPLATE_PATH}")
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def extract_function_block(template_content, function_name):
    """Extract a function's resource block from the template."""
    pattern = rf'^\s{{2}}{function_name}:\s*$'
    match = re.search(pattern, template_content, re.MULTILINE)
    if not match:
        return None

    func_start = match.start()
    remaining = template_content[func_start:]

    # Find the next top-level resource (2-space indented identifier followed by colon)
    next_resource = re.search(r'\n  [A-Za-z]\w+:', remaining[1:])
    if next_resource:
        return remaining[:next_resource.start() + 1]
    return remaining


def env_var_references_my_api(func_block, var_name):
    """
    Check if an environment variable in a function block contains a reference
    to MyApi via !Sub or !Ref.

    Returns the actual value string if it references MyApi, None otherwise.
    """
    # Look for the env var pattern with !Sub containing ${MyApi}
    sub_pattern = rf'{var_name}:\s*!Sub\s+["\']([^"\']*\$\{{MyApi\}}[^"\']*)["\']'
    match = re.search(sub_pattern, func_block)
    if match:
        return match.group(1)

    # Also check for !Ref MyApi
    ref_pattern = rf'{var_name}:\s*!Ref\s+MyApi'
    match = re.search(ref_pattern, func_block)
    if match:
        return "!Ref MyApi"

    return None


def function_has_api_event_with_my_api(func_block):
    """Check if the function has an API event with RestApiId: !Ref MyApi."""
    return bool(re.search(r'RestApiId:\s*!Ref\s+MyApi', func_block))


class TestCircularDependencyBugCondition:
    """
    Property 1: Bug Condition - SAM Template Circular Dependency via MyApi Reference

    The bug condition is: CreateOrderFunction has BOTH:
    1. An Environment.Variables entry (MOLLIE_WEBHOOK_URL) referencing MyApi via !Sub
    2. An Events entry with RestApiId: !Ref MyApi

    This creates a circular dependency:
      CreateOrderFunction → MyApi (via env var !Sub)
      MyApi Stage → CreateOrderFunction (via API event integration)

    The expected behavior (what the test asserts): MOLLIE_WEBHOOK_URL does NOT
    contain ${MyApi}, breaking the circular reference.

    **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
    """

    def test_create_order_function_webhook_url_does_not_reference_my_api(self):
        """
        Assert that CreateOrderFunction's MOLLIE_WEBHOOK_URL does NOT contain
        a ${MyApi} reference that would create a circular dependency.

        On UNFIXED code this test FAILS because the template currently has:
        MOLLIE_WEBHOOK_URL: !Sub "https://${MyApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}/mollie-webhook"

        **Validates: Requirements 1.1, 2.1**
        """
        content = read_template()

        func_block = extract_function_block(content, "CreateOrderFunction")
        assert func_block is not None, "CreateOrderFunction not found in template.yaml"

        # Check if MOLLIE_WEBHOOK_URL references MyApi
        my_api_ref = env_var_references_my_api(func_block, "MOLLIE_WEBHOOK_URL")

        assert my_api_ref is None, (
            f"CreateOrderFunction's MOLLIE_WEBHOOK_URL references MyApi: "
            f"'{my_api_ref}'. This creates a circular dependency because the function "
            f"also has an API event with RestApiId: !Ref MyApi. "
            f"The environment variable should construct the webhook URL without "
            f"referencing the API resource directly."
        )

    def test_circular_dependency_condition_not_present(self):
        """
        Assert the full circular dependency condition does NOT hold:
        CreateOrderFunction should NOT have BOTH a MyApi env var reference
        AND an API event with RestApiId: !Ref MyApi.

        **Validates: Requirements 1.2, 2.2**
        """
        content = read_template()

        func_block = extract_function_block(content, "CreateOrderFunction")
        assert func_block is not None, "CreateOrderFunction not found in template.yaml"

        has_my_api_env_ref = env_var_references_my_api(func_block, "MOLLIE_WEBHOOK_URL") is not None
        has_api_event = function_has_api_event_with_my_api(func_block)

        # The circular dependency exists when BOTH conditions are true
        circular_dependency_exists = has_my_api_env_ref and has_api_event

        assert not circular_dependency_exists, (
            "Circular dependency detected: CreateOrderFunction has BOTH "
            "an environment variable referencing ${MyApi} via !Sub AND "
            "an API event with RestApiId: !Ref MyApi. "
            "This causes CloudFormation to detect a circular dependency between "
            "PermissionStage resources and prevents deployment. "
            "Remove the ${MyApi} reference from MOLLIE_WEBHOOK_URL to break the cycle."
        )

    @given(
        env_var_name=st.sampled_from([
            "MOLLIE_WEBHOOK_URL",
            "MOLLIE_REDIRECT_URL",
            "ORDERS_TABLE_NAME",
            "PRODUCTEN_TABLE_NAME",
            "MEMBERSHIPS_TABLE_NAME",
            "MEMBERS_TABLE_NAME",
            "CARTS_TABLE_NAME",
            "MOLLIE_API_KEY",
        ])
    )
    @settings(max_examples=8)
    def test_no_env_var_in_create_order_function_references_my_api(self, env_var_name):
        """
        For any environment variable in CreateOrderFunction, the value SHALL NOT
        contain a !Sub or !Ref referencing MyApi.

        This property generalizes the bug condition check across all env vars,
        ensuring no new circular dependency can be introduced via any env var.

        **Validates: Requirements 2.1, 2.2**
        """
        content = read_template()

        func_block = extract_function_block(content, "CreateOrderFunction")
        assert func_block is not None, "CreateOrderFunction not found in template.yaml"

        my_api_ref = env_var_references_my_api(func_block, env_var_name)

        note(f"Checking env var: {env_var_name}, MyApi reference: {my_api_ref}")

        assert my_api_ref is None, (
            f"CreateOrderFunction's {env_var_name} references MyApi: '{my_api_ref}'. "
            f"Environment variables in Lambda functions with API events attached to MyApi "
            f"must NOT reference MyApi to avoid circular dependencies."
        )

    @given(
        function_name=st.sampled_from([
            "CreateOrderFunction",
            "GetOrdersFunction",
            "GetOrderByIdFunction",
            "InsertProductFunction",
            "scanProductFunction",
            "GetMembersFilteredFunction",
        ])
    )
    @settings(max_examples=6)
    def test_no_function_with_api_event_has_my_api_env_ref(self, function_name):
        """
        For any Lambda function that has an API event with RestApiId: !Ref MyApi,
        none of its environment variables SHALL reference MyApi via !Sub or !Ref.

        This is the generalized isBugCondition(template) check from the design doc.

        **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
        """
        content = read_template()

        func_block = extract_function_block(content, function_name)
        if func_block is None:
            assume(False)  # Skip if function not found

        # Only check functions that have API events with MyApi
        if not function_has_api_event_with_my_api(func_block):
            assume(False)  # Not relevant - function doesn't have MyApi API event

        # Find all environment variables in the block
        env_section = re.search(r'Environment:\s*\n\s+Variables:', func_block)
        if not env_section:
            return  # No environment variables, no circular dependency possible

        # Check for any !Sub containing ${MyApi} in the environment section
        env_start = env_section.start()
        # Find the section of env vars (indented under Variables:)
        env_block = func_block[env_start:]
        my_api_in_sub = re.search(r'!Sub\s+["\'][^"\']*\$\{MyApi\}[^"\']*["\']', env_block)

        note(f"Checking function: {function_name}, has MyApi in env !Sub: {my_api_in_sub is not None}")

        assert my_api_in_sub is None, (
            f"{function_name} has BOTH an API event with RestApiId: !Ref MyApi "
            f"AND an environment variable using !Sub with ${{MyApi}} reference. "
            f"This creates a circular dependency in CloudFormation. "
            f"Found: {my_api_in_sub.group(0) if my_api_in_sub else 'N/A'}"
        )
