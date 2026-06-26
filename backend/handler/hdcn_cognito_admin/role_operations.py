"""
Role management operations for Cognito User Pool administration.

This module re-exports role operations from their specific sub-modules
to maintain backward compatibility with existing imports in app.py.

Sub-modules:
- role_helpers: Shared utilities (cognito client, validation, permissions)
- role_queries: Read operations (get_user_roles)
- role_assignment: Write operations (assign_user_roles_auth, remove_user_role_auth)
"""
from role_queries import get_user_roles
from role_assignment import assign_user_roles_auth, remove_user_role_auth
from role_helpers import (
    validate_role_assignment_rules,
    validate_role_assignment_permission,
    calculate_user_permissions,
)

__all__ = [
    'get_user_roles',
    'assign_user_roles_auth',
    'remove_user_role_auth',
    'validate_role_assignment_rules',
    'validate_role_assignment_permission',
    'calculate_user_permissions',
]
