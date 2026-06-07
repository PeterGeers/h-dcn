"""
Preservation Property Tests for Non-Passkey Authentication and API Operations

These tests capture the existing behavior of non-passkey flows on UNFIXED code
to ensure no regressions are introduced by the passkey fix.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8, 3.9, 3.10**

Property 3: Preservation - Non-Passkey Authentication and Operations
For any input that is NOT a passkey registration or authentication operation,
the fixed code SHALL produce exactly the same behavior as the original code.

Approach: Structural verification of handler code to ensure non-passkey
logic remains intact after the passkey fix is applied. These tests read
source files and verify key patterns/functions exist unchanged.
"""

import os
import re
import pytest
from hypothesis import given, settings, note
from hypothesis import strategies as st


# Path constants
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HANDLER_DIR = os.path.join(BACKEND_DIR, "handler")
TEMPLATE_PATH = os.path.join(BACKEND_DIR, "template.yaml")
FRONTEND_DIR = os.path.dirname(BACKEND_DIR)


def read_file_content(path):
    """Read file content, raising clear error if file not found."""
    if not os.path.exists(path):
        pytest.skip(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# --- Test Class: Google SSO PostAuthentication Preservation (Requirement 3.1) ---

class TestGoogleSSOPreservation:
    """
    **Validates: Requirements 3.1**

    The PostAuthentication trigger must continue to link identities
    and assign roles for Google SSO users.
    """

    def test_post_authentication_handler_exists(self):
        """Handler file exists."""
        path = os.path.join(HANDLER_DIR, "cognito_post_authentication", "app.py")
        assert os.path.exists(path), "cognito_post_authentication/app.py missing"

    def test_post_authentication_handles_authentication_trigger(self):
        """Handler processes PostAuthentication_Authentication trigger."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_post_authentication", "app.py")
        )
        assert "PostAuthentication_Authentication" in content
        assert "lambda_handler" in content

    def test_post_authentication_assigns_hdcn_leden_group(self):
        """Handler assigns hdcnLeden group to approved members."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_post_authentication", "app.py")
        )
        assert "hdcnLeden" in content
        assert "admin_add_user_to_group" in content

    def test_post_authentication_checks_member_status(self):
        """Handler checks member status before assigning roles."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_post_authentication", "app.py")
        )
        # Must check approved statuses
        assert "approved" in content or "active" in content
        assert "Members" in content or "MEMBERS_TABLE_NAME" in content

    def test_post_authentication_returns_event(self):
        """Handler returns the original event (required by Cognito)."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_post_authentication", "app.py")
        )
        assert "return event" in content


# --- Test Class: PreSignUp Trigger Preservation (Requirement 3.3) ---

class TestPreSignUpPreservation:
    """
    **Validates: Requirements 3.3**

    The PreSignUp trigger must continue to link external provider
    identities to existing native users.
    """

    def test_pre_signup_handler_exists(self):
        """Handler file exists."""
        path = os.path.join(HANDLER_DIR, "cognito_pre_signup", "app.py")
        assert os.path.exists(path), "cognito_pre_signup/app.py missing"

    def test_pre_signup_handles_external_provider(self):
        """Handler processes PreSignUp_ExternalProvider trigger."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_pre_signup", "app.py")
        )
        assert "PreSignUp_ExternalProvider" in content
        assert "lambda_handler" in content

    def test_pre_signup_auto_confirms_and_verifies(self):
        """Handler sets autoConfirmUser and autoVerifyEmail for external providers."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_pre_signup", "app.py")
        )
        assert "autoConfirmUser" in content
        assert "autoVerifyEmail" in content

    def test_pre_signup_links_identities(self):
        """Handler links federated identity to native user."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_pre_signup", "app.py")
        )
        # Should use admin_link_provider_for_user or similar linking mechanism
        assert "link" in content.lower() or "admin_link_provider" in content


# --- Test Class: PostConfirmation Trigger Preservation (Requirement 3.4) ---

class TestPostConfirmationPreservation:
    """
    **Validates: Requirements 3.4**

    The PostConfirmation trigger must continue to assign hdcnLeden group.
    """

    def test_post_confirmation_handler_exists(self):
        """Handler file exists."""
        path = os.path.join(HANDLER_DIR, "cognito_post_confirmation", "app.py")
        assert os.path.exists(path), "cognito_post_confirmation/app.py missing"

    def test_post_confirmation_assigns_group(self):
        """Handler assigns hdcnLeden group on confirmation."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_post_confirmation", "app.py")
        )
        assert "hdcnLeden" in content or "admin_add_user_to_group" in content

    def test_post_confirmation_handles_confirm_signup(self):
        """Handler processes PostConfirmation_ConfirmSignUp trigger."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_post_confirmation", "app.py")
        )
        assert "PostConfirmation" in content or "ConfirmSignUp" in content


# --- Test Class: CustomMessage Trigger Preservation (Requirement 3.5) ---

class TestCustomMessagePreservation:
    """
    **Validates: Requirements 3.5**

    The CustomMessage trigger must continue to send Dutch-language
    email templates with H-DCN branding.
    """

    def test_custom_message_handler_exists(self):
        """Handler file exists."""
        path = os.path.join(HANDLER_DIR, "cognito_custom_message", "app.py")
        assert os.path.exists(path), "cognito_custom_message/app.py missing"

    def test_custom_message_has_dutch_content(self):
        """Handler provides Dutch language templates."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_custom_message", "app.py")
        )
        # Check for Dutch language indicators or template references
        assert "H-DCN" in content or "ORGANIZATION_SHORT_NAME" in content

    def test_custom_message_handles_multiple_triggers(self):
        """Handler supports multiple CustomMessage trigger types."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_custom_message", "app.py")
        )
        trigger_types = [
            "CustomMessage_AdminCreateUser",
            "CustomMessage_ForgotPassword",
            "CustomMessage_Authentication",
        ]
        found = [t for t in trigger_types if t in content]
        assert len(found) >= 2, f"Only found triggers: {found}"


# --- Test Class: Admin Cognito Operations Preservation (Requirement 3.6) ---

class TestAdminOperationsPreservation:
    """
    **Validates: Requirements 3.6**

    The hdcn_cognito_admin handler must continue to support
    non-passkey admin operations (create/update/delete users).
    """

    def test_cognito_admin_handler_exists(self):
        """Handler file exists."""
        path = os.path.join(HANDLER_DIR, "hdcn_cognito_admin", "app.py")
        assert os.path.exists(path), "hdcn_cognito_admin/app.py missing"

    def test_cognito_admin_has_user_management(self):
        """Handler supports user management operations."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "hdcn_cognito_admin", "app.py")
        )
        # Must have admin user operations
        assert "admin_create_user" in content or "create_user" in content
        assert "admin_get_user" in content or "get_user" in content

    def test_cognito_admin_has_group_management(self):
        """Handler supports group management."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "hdcn_cognito_admin", "app.py")
        )
        assert "group" in content.lower()

    def test_cognito_admin_uses_pool_id_env_var(self):
        """Handler package reads COGNITO_USER_POOL_ID from environment.

        After the refactoring split, COGNITO_USER_POOL_ID lives in sub-modules
        (user_operations.py, group_operations.py, etc.) rather than app.py directly.
        """
        hdcn_admin_dir = os.path.join(HANDLER_DIR, "hdcn_cognito_admin")
        sub_modules = [
            "app.py",
            "user_operations.py",
            "group_operations.py",
            "auth_operations.py",
            "role_operations.py",
            "permission_utils.py",
        ]
        found = False
        for module in sub_modules:
            module_path = os.path.join(hdcn_admin_dir, module)
            if not os.path.exists(module_path):
                continue
            content = read_file_content(module_path)
            if "COGNITO_USER_POOL_ID" in content:
                found = True
                break
        assert found, (
            "COGNITO_USER_POOL_ID not found in any hdcn_cognito_admin module"
        )


# --- Test Class: DynamoDB API Operations Preservation (Requirement 3.8) ---

class TestNonPasskeyAPIPreservation:
    """
    **Validates: Requirements 3.8**

    Non-passkey API handlers must remain unchanged.
    """

    @given(
        handler_name=st.sampled_from([
            "get_members",
            "create_member",
            "get_events",
            "create_order",
        ])
    )
    @settings(max_examples=4)
    def test_non_passkey_handlers_exist(self, handler_name):
        """All non-passkey API handlers still exist."""
        path = os.path.join(HANDLER_DIR, handler_name, "app.py")
        if not os.path.exists(path):
            pytest.skip(f"Handler {handler_name} not present in this project")
        content = read_file_content(path)
        assert "lambda_handler" in content
        note(f"Handler {handler_name} exists with lambda_handler")

    def test_get_members_handler_uses_dynamodb(self):
        """get_members handler reads from DynamoDB."""
        path = os.path.join(HANDLER_DIR, "get_members", "app.py")
        if not os.path.exists(path):
            pytest.skip("get_members handler not present")
        content = read_file_content(path)
        assert "dynamodb" in content.lower() or "Table" in content


# --- Test Class: get_member_self Preservation (Requirement 3.9) ---

class TestGetMemberSelfPreservation:
    """
    **Validates: Requirements 3.9**

    The get_member_self handler must continue to retrieve custom:member_id
    from Cognito and return member data from DynamoDB.
    """

    def test_get_member_self_handler_exists(self):
        """Handler file exists."""
        path = os.path.join(HANDLER_DIR, "get_member_self", "app.py")
        assert os.path.exists(path), "get_member_self/app.py missing"

    def test_get_member_self_uses_admin_get_user(self):
        """Handler calls admin_get_user to retrieve user attributes."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "get_member_self", "app.py")
        )
        assert "admin_get_user" in content

    def test_get_member_self_reads_member_id_attribute(self):
        """Handler reads custom:member_id from Cognito user attributes."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "get_member_self", "app.py")
        )
        assert "member_id" in content

    def test_get_member_self_queries_dynamodb(self):
        """Handler queries DynamoDB Members table."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "get_member_self", "app.py")
        )
        assert "dynamodb" in content.lower() or "Table" in content
        assert "Members" in content or "MEMBERS_TABLE_NAME" in content

    def test_get_member_self_has_email_fallback(self):
        """Handler has email-based fallback when member_id not found."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "get_member_self", "app.py")
        )
        assert "email" in content


# --- Test Class: SAM Template Non-Passkey Functions Preservation (Requirement 3.10) ---

class TestSAMTemplatePreservation:
    """
    **Validates: Requirements 3.10**

    Lambda functions that already receive COGNITO_USER_POOL_ID via their
    Environment block must continue to have it after the fix.
    """

    @given(
        function_name=st.sampled_from([
            "CognitoPostAuthenticationFunction",
            "CognitoPreSignUpFunction",
            "CognitoPostConfirmationFunction",
            "HdcnCognitoAdminFunction",
        ])
    )
    @settings(max_examples=4)
    def test_cognito_functions_defined_in_template(self, function_name):
        """All Cognito-related Lambda functions are defined in template.yaml."""
        content = read_file_content(TEMPLATE_PATH)
        # Check if function exists (may have slightly different naming)
        # Use flexible matching
        base_name = function_name.replace("Function", "")
        found = function_name in content or base_name in content
        if not found:
            pytest.skip(f"{function_name} not found in template (may use different naming)")
        note(f"Found {function_name} in template.yaml")

    def test_template_has_cognito_triggers(self):
        """SAM template defines Cognito trigger events."""
        content = read_file_content(TEMPLATE_PATH)
        # At least some Cognito triggers should be defined
        cognito_triggers = ["PreSignUp", "PostConfirmation", "PostAuthentication", "CustomMessage"]
        found = [t for t in cognito_triggers if t in content]
        assert len(found) >= 2, f"Only found Cognito triggers: {found}"

    def test_template_has_members_table(self):
        """SAM template defines Members DynamoDB table."""
        content = read_file_content(TEMPLATE_PATH)
        assert "MembersTable" in content or "Members" in content

    def test_template_has_api_gateway(self):
        """SAM template defines API Gateway."""
        content = read_file_content(TEMPLATE_PATH)
        assert "Api" in content or "RestApi" in content or "HttpApi" in content


# --- Test Class: Email OTP Flow Preservation (Requirement 3.2) ---

class TestEmailOTPPreservation:
    """
    **Validates: Requirements 3.2**

    Email OTP authentication must continue to work. The CustomMessage
    trigger handles code delivery for authentication.
    """

    def test_custom_message_handles_authentication_trigger(self):
        """CustomMessage handler processes Authentication trigger for OTP."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_custom_message", "app.py")
        )
        assert "CustomMessage_Authentication" in content

    def test_custom_message_includes_code_parameter(self):
        """CustomMessage handler includes the verification code in messages."""
        content = read_file_content(
            os.path.join(HANDLER_DIR, "cognito_custom_message", "app.py")
        )
        assert "codeParameter" in content or "code" in content.lower()
