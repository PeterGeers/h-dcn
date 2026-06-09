# Shared authentication layer for H-DCN Lambda functions

# Backward-compatible aliases for tenant_resolver → channel_resolver rename
from shared.channel_resolver import resolve_channels as resolve_tenants  # noqa: F401
from shared.channel_resolver import validate_channel_access as validate_tenant_access  # noqa: F401
from shared.channel_resolver import GROUP_CHANNEL_MAP as GROUP_TENANT_MAP  # noqa: F401