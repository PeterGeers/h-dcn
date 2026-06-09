"""
Unit tests for shared.channel_resolver module.

Tests resolve_channels() and validate_channel_access() covering the
channel-to-role mapping and access enforcement logic.
"""

import json
import pytest
import sys
import os

# Ensure shared layer is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')))

from shared.channel_resolver import resolve_channels, validate_channel_access, GROUP_CHANNEL_MAP


class TestResolveChannels:
    """Tests for resolve_channels()."""

    def test_hdcn_leden_grants_h_dcn(self):
        result = resolve_channels(["hdcnLeden"])
        assert result == {"h-dcn"}

    def test_regio_pressmeet_grants_presmeet(self):
        result = resolve_channels(["Regio_Pressmeet"])
        assert result == {"presmeet"}

    def test_regio_all_grants_presmeet(self):
        result = resolve_channels(["Regio_All"])
        assert result == {"presmeet"}

    def test_both_hdcn_and_pressmeet_grants_union(self):
        result = resolve_channels(["hdcnLeden", "Regio_Pressmeet"])
        assert result == {"h-dcn", "presmeet"}

    def test_both_hdcn_and_regio_all_grants_union(self):
        result = resolve_channels(["hdcnLeden", "Regio_All"])
        assert result == {"h-dcn", "presmeet"}

    def test_no_relevant_groups_returns_empty(self):
        result = resolve_channels(["verzoek_lid", "System_CRUD"])
        assert result == set()

    def test_empty_list_returns_empty(self):
        result = resolve_channels([])
        assert result == set()

    def test_none_returns_empty(self):
        result = resolve_channels(None)
        assert result == set()

    def test_duplicate_mapping_deduplicates(self):
        """Regio_Pressmeet and Regio_All both map to presmeet — no duplicates."""
        result = resolve_channels(["Regio_Pressmeet", "Regio_All"])
        assert result == {"presmeet"}

    def test_all_three_groups_grants_both_channels(self):
        result = resolve_channels(["hdcnLeden", "Regio_Pressmeet", "Regio_All"])
        assert result == {"h-dcn", "presmeet"}

    def test_irrelevant_groups_ignored(self):
        result = resolve_channels(["hdcnLeden", "Members_CRUD", "Regio_Noord"])
        assert result == {"h-dcn"}


class TestValidateChannelAccess:
    """Tests for validate_channel_access()."""

    def test_allowed_single_channel_returns_none(self):
        result = validate_channel_access("h-dcn", {"h-dcn", "presmeet"})
        assert result is None

    def test_allowed_multiple_channels_returns_none(self):
        result = validate_channel_access("h-dcn,presmeet", {"h-dcn", "presmeet"})
        assert result is None

    def test_denied_channel_returns_403(self):
        result = validate_channel_access("presmeet", {"h-dcn"})
        assert result is not None
        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert body["error"] == "channel_access_denied"
        assert "presmeet" in body["details"]["requested_channel"]
        assert "h-dcn" in body["details"]["allowed_channels"]

    def test_partial_denied_returns_403(self):
        """If one of the requested channels is not allowed, deny."""
        result = validate_channel_access("h-dcn,presmeet", {"h-dcn"})
        assert result is not None
        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert body["error"] == "channel_access_denied"
        assert "presmeet" in body["details"]["requested_channel"]

    def test_empty_requested_returns_403(self):
        result = validate_channel_access("", {"h-dcn"})
        assert result is not None
        assert result["statusCode"] == 403

    def test_none_requested_returns_403(self):
        result = validate_channel_access(None, {"h-dcn"})
        assert result is not None
        assert result["statusCode"] == 403

    def test_whitespace_handling(self):
        """Spaces around channel values should be trimmed."""
        result = validate_channel_access(" h-dcn , presmeet ", {"h-dcn", "presmeet"})
        assert result is None

    def test_empty_user_channels_always_denies(self):
        result = validate_channel_access("h-dcn", set())
        assert result is not None
        assert result["statusCode"] == 403

    def test_cors_headers_present(self):
        result = validate_channel_access("presmeet", {"h-dcn"})
        assert "Access-Control-Allow-Origin" in result["headers"]


class TestGroupChannelMap:
    """Tests for GROUP_CHANNEL_MAP constant."""

    def test_hdcn_leden_maps_to_h_dcn(self):
        assert GROUP_CHANNEL_MAP["hdcnLeden"] == "h-dcn"

    def test_regio_pressmeet_maps_to_presmeet(self):
        assert GROUP_CHANNEL_MAP["Regio_Pressmeet"] == "presmeet"

    def test_regio_all_maps_to_presmeet(self):
        assert GROUP_CHANNEL_MAP["Regio_All"] == "presmeet"

    def test_map_has_exactly_three_entries(self):
        assert len(GROUP_CHANNEL_MAP) == 3


class TestBackwardCompatibleAliases:
    """Tests that backward-compatible aliases in __init__.py still work."""

    def test_resolve_tenants_alias_works(self):
        from shared import resolve_tenants
        result = resolve_tenants(["hdcnLeden"])
        assert result == {"h-dcn"}

    def test_validate_tenant_access_alias_works(self):
        from shared import validate_tenant_access
        result = validate_tenant_access("h-dcn", {"h-dcn"})
        assert result is None

    def test_group_tenant_map_alias_works(self):
        from shared import GROUP_TENANT_MAP
        assert GROUP_TENANT_MAP["hdcnLeden"] == "h-dcn"
