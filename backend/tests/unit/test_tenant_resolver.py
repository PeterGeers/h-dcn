"""
Unit tests for shared.tenant_resolver module.

Tests resolve_tenants() and validate_tenant_access() covering the
tenant-to-role mapping and access enforcement logic.
"""

import json
import pytest
import sys
import os

# Ensure shared layer is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')))

from shared.tenant_resolver import resolve_tenants, validate_tenant_access


class TestResolveTenants:
    """Tests for resolve_tenants()."""

    def test_hdcn_leden_grants_h_dcn(self):
        result = resolve_tenants(["hdcnLeden"])
        assert result == {"h-dcn"}

    def test_regio_pressmeet_grants_presmeet(self):
        result = resolve_tenants(["Regio_Pressmeet"])
        assert result == {"presmeet"}

    def test_regio_all_grants_presmeet(self):
        result = resolve_tenants(["Regio_All"])
        assert result == {"presmeet"}

    def test_both_hdcn_and_pressmeet_grants_union(self):
        result = resolve_tenants(["hdcnLeden", "Regio_Pressmeet"])
        assert result == {"h-dcn", "presmeet"}

    def test_both_hdcn_and_regio_all_grants_union(self):
        result = resolve_tenants(["hdcnLeden", "Regio_All"])
        assert result == {"h-dcn", "presmeet"}

    def test_no_relevant_groups_returns_empty(self):
        result = resolve_tenants(["verzoek_lid", "System_CRUD"])
        assert result == set()

    def test_empty_list_returns_empty(self):
        result = resolve_tenants([])
        assert result == set()

    def test_none_returns_empty(self):
        result = resolve_tenants(None)
        assert result == set()

    def test_duplicate_mapping_deduplicates(self):
        """Regio_Pressmeet and Regio_All both map to presmeet — no duplicates."""
        result = resolve_tenants(["Regio_Pressmeet", "Regio_All"])
        assert result == {"presmeet"}

    def test_all_three_groups_grants_both_tenants(self):
        result = resolve_tenants(["hdcnLeden", "Regio_Pressmeet", "Regio_All"])
        assert result == {"h-dcn", "presmeet"}

    def test_irrelevant_groups_ignored(self):
        result = resolve_tenants(["hdcnLeden", "Members_CRUD", "Regio_Noord"])
        assert result == {"h-dcn"}


class TestValidateTenantAccess:
    """Tests for validate_tenant_access()."""

    def test_allowed_single_tenant_returns_none(self):
        result = validate_tenant_access("h-dcn", {"h-dcn", "presmeet"})
        assert result is None

    def test_allowed_multiple_tenants_returns_none(self):
        result = validate_tenant_access("h-dcn,presmeet", {"h-dcn", "presmeet"})
        assert result is None

    def test_denied_tenant_returns_403(self):
        result = validate_tenant_access("presmeet", {"h-dcn"})
        assert result is not None
        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert body["error"] == "tenant_access_denied"
        assert "presmeet" in body["details"]["requested_tenant"]
        assert "h-dcn" in body["details"]["allowed_tenants"]

    def test_partial_denied_returns_403(self):
        """If one of the requested tenants is not allowed, deny."""
        result = validate_tenant_access("h-dcn,presmeet", {"h-dcn"})
        assert result is not None
        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert body["error"] == "tenant_access_denied"
        assert "presmeet" in body["details"]["requested_tenant"]

    def test_empty_requested_returns_403(self):
        result = validate_tenant_access("", {"h-dcn"})
        assert result is not None
        assert result["statusCode"] == 403

    def test_none_requested_returns_403(self):
        result = validate_tenant_access(None, {"h-dcn"})
        assert result is not None
        assert result["statusCode"] == 403

    def test_whitespace_handling(self):
        """Spaces around tenant values should be trimmed."""
        result = validate_tenant_access(" h-dcn , presmeet ", {"h-dcn", "presmeet"})
        assert result is None

    def test_empty_user_tenants_always_denies(self):
        result = validate_tenant_access("h-dcn", set())
        assert result is not None
        assert result["statusCode"] == 403

    def test_cors_headers_present(self):
        result = validate_tenant_access("presmeet", {"h-dcn"})
        assert "Access-Control-Allow-Origin" in result["headers"]
