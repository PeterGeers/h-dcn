"""
Property-Based Tests for PresMeet v2 Access Control Functions

Tests the role-checking functions in shared.club_identity using Hypothesis
to verify correctness across arbitrary role list inputs.

This file covers:
- Property 1: PresMeet access gating (has_presmeet_access)
- Property 2: PresMeet admin role check (is_presmeet_admin) — task 1.3
- Property 3: PresMeet admin write vs read (is_presmeet_admin_write) — task 1.4
"""

import pytest
from hypothesis import given, settings, note, assume
from hypothesis import strategies as st

from shared.club_identity import has_presmeet_access, is_presmeet_admin, is_presmeet_admin_write


# --- Strategies ---

# Valid H-DCN roles that exist in the system
MANAGEMENT_ROLES = ['Products_CRUD', 'Products_Read', 'Webshop_Management']
REGION_ROLES = ['Regio_Pressmeet', 'Regio_All']
OTHER_VALID_ROLES = [
    'hdcnLeden', 'System_User_Management', 'Bestuur', 'Kascommissie',
    'Evenementen_Commissie', 'Regio_Noord', 'Regio_Zuid', 'Regio_Oost',
    'Regio_West', 'verzoek_lid', 'webmaster'
]
ALL_KNOWN_ROLES = MANAGEMENT_ROLES + REGION_ROLES + OTHER_VALID_ROLES

# Strategy: generate role lists from known roles + random strings
role_name_strategy = st.one_of(
    st.sampled_from(ALL_KNOWN_ROLES),
    st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N', 'P')))
)

role_list_strategy = st.lists(role_name_strategy, min_size=0, max_size=15)

# Strategy for roles that do NOT grant PresMeet access (no Regio_Pressmeet or Regio_All)
non_access_role_strategy = st.one_of(
    st.sampled_from([r for r in ALL_KNOWN_ROLES if r not in REGION_ROLES]),
    st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N', 'P'))).filter(
        lambda s: s not in REGION_ROLES
    ),
)


# =============================================================================
# Property 1: PresMeet access gating
# =============================================================================

class TestProperty1PresMeetAccessGating:
    """
    **Validates: Requirements 1.3, 1.4, 3.5**

    Property 1: has_presmeet_access(roles) returns True if and only if
    the role list contains 'Regio_Pressmeet' or 'Regio_All'.
    """

    @given(roles=role_list_strategy)
    @settings(max_examples=500)
    def test_property1_access_iff_regio_pressmeet_or_regio_all(self, roles):
        """
        Property: has_presmeet_access(roles) == True iff roles contain
        'Regio_Pressmeet' or 'Regio_All'.

        **Validates: Requirements 1.3, 1.4, 3.5**
        """
        expected = ('Regio_Pressmeet' in roles or 'Regio_All' in roles)
        result = has_presmeet_access(roles)

        note(f"roles={roles}, expected={expected}")
        assert result == expected, (
            f"has_presmeet_access({roles}) returned {result}, expected {expected}"
        )

    @given(
        access_role=st.sampled_from(REGION_ROLES),
        other_roles=st.lists(non_access_role_strategy, min_size=0, max_size=10),
        insert_position=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=200)
    def test_property1_grants_access_with_valid_role_in_any_position(
        self, access_role, other_roles, insert_position
    ):
        """
        For any list of non-access roles with one access role inserted at any
        position, has_presmeet_access SHALL return True.

        **Validates: Requirements 1.3, 1.4, 3.5**
        """
        roles = list(other_roles)
        pos = min(insert_position, len(roles))
        roles.insert(pos, access_role)

        result = has_presmeet_access(roles)
        assert result is True, (
            f"has_presmeet_access should return True when '{access_role}' is present, "
            f"but returned {result} for roles: {roles}"
        )

    @given(roles=st.lists(non_access_role_strategy, min_size=0, max_size=10))
    @settings(max_examples=300)
    def test_property1_denies_access_without_valid_role(self, roles):
        """
        For any list of roles that does NOT contain 'Regio_Pressmeet' or
        'Regio_All', has_presmeet_access SHALL return False.

        **Validates: Requirements 1.3, 1.4, 3.5**
        """
        result = has_presmeet_access(roles)
        assert result is False, (
            f"has_presmeet_access should return False without access roles, "
            f"but returned {result} for roles: {roles}"
        )

    @given(
        other_roles=st.lists(non_access_role_strategy, min_size=0, max_size=5),
    )
    @settings(max_examples=100)
    def test_property1_both_access_roles_still_grants_access(self, other_roles):
        """
        If both 'Regio_Pressmeet' and 'Regio_All' are present, access SHALL
        still be granted (OR semantics, not exclusive).

        **Validates: Requirements 1.3, 1.4, 3.5**
        """
        roles = list(other_roles) + ['Regio_Pressmeet', 'Regio_All']
        result = has_presmeet_access(roles)
        assert result is True, (
            f"has_presmeet_access should return True with both access roles present, "
            f"but returned {result} for roles: {roles}"
        )

    def test_property1_empty_list_denies_access(self):
        """
        An empty role list SHALL always deny access.

        **Validates: Requirements 1.3, 1.4, 3.5**
        """
        result = has_presmeet_access([])
        assert result is False, "has_presmeet_access([]) should return False"


# =============================================================================
# Property 2: PresMeet admin role check
# =============================================================================

class TestProperty2PresMeetAdminRoleCheck:
    """
    **Validates: Requirements 1.5, 5.1, 5.2, 5.3, 5.6**

    Property 2: is_presmeet_admin(roles) returns True if and only if
    the role list contains at least one management role
    (Products_CRUD, Products_Read, or Webshop_Management)
    AND at least one region role (Regio_Pressmeet or Regio_All).
    """

    @given(roles=role_list_strategy)
    @settings(max_examples=500)
    def test_admin_true_iff_management_and_region(self, roles):
        """
        Property: is_presmeet_admin(roles) == True iff roles contain
        at least one management role AND at least one region role.

        **Validates: Requirements 1.5, 5.1, 5.2, 5.3, 5.6**
        """
        has_management = any(r in MANAGEMENT_ROLES for r in roles)
        has_region = any(r in REGION_ROLES for r in roles)
        expected = has_management and has_region

        result = is_presmeet_admin(roles)

        note(f"roles={roles}, has_management={has_management}, has_region={has_region}")
        assert result == expected, (
            f"is_presmeet_admin({roles}) returned {result}, expected {expected}. "
            f"has_management={has_management}, has_region={has_region}"
        )

    @given(
        management_role=st.sampled_from(MANAGEMENT_ROLES),
        region_role=st.sampled_from(REGION_ROLES),
        extra_roles=st.lists(role_name_strategy, min_size=0, max_size=10)
    )
    @settings(max_examples=200)
    def test_admin_true_when_both_present(self, management_role, region_role, extra_roles):
        """
        When roles contain at least one management role and one region role,
        is_presmeet_admin must return True regardless of other roles present.

        **Validates: Requirements 1.5, 5.1, 5.2, 5.3**
        """
        roles = [management_role, region_role] + extra_roles
        result = is_presmeet_admin(roles)
        assert result is True, (
            f"Expected True with management={management_role}, region={region_role}, "
            f"extra={extra_roles}"
        )

    @given(roles=st.lists(role_name_strategy, min_size=0, max_size=15))
    @settings(max_examples=300)
    def test_admin_false_without_region(self, roles):
        """
        Without any region role (Regio_Pressmeet or Regio_All),
        is_presmeet_admin must return False even with management roles.

        **Validates: Requirements 5.6**
        """
        roles_no_region = [r for r in roles if r not in REGION_ROLES]
        result = is_presmeet_admin(roles_no_region)
        assert result is False, (
            f"Expected False without region roles, got True for {roles_no_region}"
        )

    @given(roles=st.lists(role_name_strategy, min_size=0, max_size=15))
    @settings(max_examples=300)
    def test_admin_false_without_management(self, roles):
        """
        Without any management role (Products_CRUD, Products_Read, Webshop_Management),
        is_presmeet_admin must return False even with region roles.

        **Validates: Requirements 5.6**
        """
        roles_no_mgmt = [r for r in roles if r not in MANAGEMENT_ROLES]
        result = is_presmeet_admin(roles_no_mgmt)
        assert result is False, (
            f"Expected False without management roles, got True for {roles_no_mgmt}"
        )


# =============================================================================
# Property 3: PresMeet admin write vs read distinction
# =============================================================================

class TestPresMeetAdminWriteVsRead:
    """
    **Validates: Requirements 5.4, 5.5**

    Property 3: is_presmeet_admin_write(roles) returns True if and only if
    the role list contains `Products_CRUD` specifically (not Products_Read
    or Webshop_Management) AND at least one region role (Regio_Pressmeet
    or Regio_All). A list with Products_Read + region role satisfies
    is_presmeet_admin but NOT is_presmeet_admin_write.
    """

    @given(roles=role_list_strategy)
    @settings(max_examples=500)
    def test_admin_write_iff_crud_and_region(self, roles):
        """
        Property: is_presmeet_admin_write(roles) == True iff roles contain
        Products_CRUD AND at least one region role.

        **Validates: Requirements 5.4, 5.5**
        """
        has_crud = 'Products_CRUD' in roles
        has_region = any(r in REGION_ROLES for r in roles)
        expected = has_crud and has_region

        result = is_presmeet_admin_write(roles)

        note(f"roles={roles}, has_crud={has_crud}, has_region={has_region}")
        assert result == expected, (
            f"is_presmeet_admin_write({roles}) returned {result}, expected {expected}. "
            f"has_crud={has_crud}, has_region={has_region}"
        )

    @given(roles=role_list_strategy)
    @settings(max_examples=300)
    def test_admin_write_implies_admin(self, roles):
        """
        If is_presmeet_admin_write(roles) is True, then is_presmeet_admin(roles)
        must also be True. Write access is a strict subset of general admin access.

        **Validates: Requirements 5.4, 5.5**
        """
        if is_presmeet_admin_write(roles):
            assert is_presmeet_admin(roles) is True, (
                f"admin_write=True but admin=False for roles={roles}. "
                f"Write access should imply general admin access."
            )

    @given(
        region_role=st.sampled_from(REGION_ROLES),
        extra_roles=st.lists(role_name_strategy, min_size=0, max_size=8)
    )
    @settings(max_examples=300)
    def test_products_read_without_crud_no_write_access(self, region_role, extra_roles):
        """
        Having Products_Read + region role WITHOUT Products_CRUD does NOT grant
        write access, even though it grants general admin (read-only) access.

        **Validates: Requirements 5.4, 5.5**
        """
        roles = ['Products_Read', region_role] + extra_roles
        # Ensure Products_CRUD is NOT in the list
        assume('Products_CRUD' not in roles)

        # Should satisfy general admin check (read-only access)
        assert is_presmeet_admin(roles) is True, (
            f"Expected is_presmeet_admin=True for {roles}"
        )
        # Should NOT satisfy write admin check
        assert is_presmeet_admin_write(roles) is False, (
            f"Expected is_presmeet_admin_write=False for {roles} "
            f"(Products_Read should not grant write access)"
        )
