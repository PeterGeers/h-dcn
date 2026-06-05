# Regional Filtering Bug Fix - Complete

**Date**: 2026-01-18  
**Status**: ✅ RESOLVED  
**User**: Peter Geers (peter@pgeers.nl)

## Problem Summary

User Peter Geers has `Regio_Utrecht` group in Cognito but was seeing 0 members instead of 106 Utrecht members in the member list.

## Root Causes Identified

### 1. Backend Auth Layer Bug (FIXED)

**Location**: `backend/layers/auth-layer/python/shared/auth_utils.py` lines 185-186

**Problem**: When a user had BOTH `hdcnLeden` AND regional roles (like `Regio_Utrecht`), the auth layer returned early with empty `allowed_regions` without checking for regional roles.

**Buggy Code**:

```python
# Basic member roles (hdcnLeden, verzoek_lid) don't need region roles
if any(role in ['hdcnLeden', 'verzoek_lid'] for role in user_roles):
    return True, None, {'has_full_access': False, 'allowed_regions': [], 'access_type': 'basic_member'}
```

**Fix Applied**:

```python
# Check for regional roles FIRST
region_roles = [role for role in user_roles if role.startswith('Regio_')]

# If user has regional roles, use regional access (even if they also have hdcnLeden)
if region_roles:
    regional_info = determine_regional_access(user_roles, resource_context)
    print(f"[AUTH_DEBUG] User has regional roles: {region_roles}, regional_info: {regional_info}")
    return True, None, regional_info

# Basic member roles (hdcnLeden, verzoek_lid) without regional roles
if any(role in ['hdcnLeden', 'verzoek_lid'] for role in user_roles):
    print(f"[AUTH_DEBUG] User has basic member role without regional roles")
    return True, None, {'has_full_access': False, 'allowed_regions': [], 'access_type': 'basic_member'}
```

### 2. Frontend Region Extraction Bug (FIXED)

**Location**: `frontend/src/modules/members/MemberAdminPage.tsx` line 88

**Problem**: The frontend was hardcoded to set `userRegion` to "Noord-Holland" instead of extracting it from the user's roles.

**Buggy Code**:

```typescript
// In a real implementation, you'd fetch the user's region from the API
// For now, we'll use a placeholder
setUserRegion("Noord-Holland"); // This should come from user profile
```

**Fix Applied**:

```typescript
// Extract region from user's Regio_* roles
const regionRole = roles.find(
  (role) => role.startsWith("Regio_") && role !== "Regio_All",
);
if (regionRole) {
  // Extract region name from role (e.g., "Regio_Utrecht" -> "Utrecht")
  const region = regionRole.replace("Regio_", "");
  setUserRegion(region);
  console.log(`[MemberAdminPage] User region set to: ${region}`);
} else if (roles.includes("Regio_All")) {
  // User has national access
  setUserRegion("All");
  console.log("[MemberAdminPage] User has national access (Regio_All)");
} else {
  // No regional role found
  setUserRegion("");
  console.log("[MemberAdminPage] No regional role found");
}
```

## Verification

### Backend Logs (CloudWatch)

```
✅ [AUTH_DEBUG] User has regional roles: ['Regio_Utrecht'], regional_info: {'has_full_access': False, 'allowed_regions': ['Utrecht'], 'access_type': 'regional'}
✅ [FILTER] Filtered 1229 members to 106 members for regions: ['Utrecht']
✅ [HANDLER] Success: Returning 106 members to user peter@pgeers.nl
```

### Frontend Result

- User sees: **"106 van 106 leden"** (106 of 106 members)
- All Utrecht members are displayed correctly
- Regional filtering works as expected

## Deployments

1. **Backend Deployment** (13:58 UTC)
   - New auth layer version: `AuthLayer6587e9c6b1` (version 15)
   - All Lambda functions updated to use new layer
   - Commit: `eddb58b`

2. **Frontend Deployment** (14:05 UTC)
   - Updated `MemberAdminPage.tsx` with region extraction logic
   - CloudFront cache invalidated
   - Commit: `471d939`

## Impact

- ✅ Users with both `hdcnLeden` and regional roles now see correct regional data
- ✅ Backend correctly identifies regional access from `Regio_*` roles
- ✅ Frontend correctly extracts region from user roles
- ✅ No impact on users with only `hdcnLeden` or only regional roles
- ✅ No impact on users with `Regio_All` (national access)

## Testing Performed

1. **Backend Testing**:
   - Verified auth layer returns correct `allowed_regions` for Peter's roles
   - Verified backend filters 1229 members to 106 Utrecht members
   - Verified response includes correct metadata

2. **Frontend Testing**:
   - Verified frontend extracts "Utrecht" from `Regio_Utrecht` role
   - Verified MemberAdminTable receives correct `userRegion` prop
   - Verified 106 Utrecht members are displayed

3. **User Acceptance**:
   - User confirmed: "Top the data from Utrecht is loaded as expected"

## Related Files

- `backend/layers/auth-layer/python/shared/auth_utils.py` (auth layer fix)
- `backend/shared/auth_utils.py` (sync copy of auth layer)
- `frontend/src/modules/members/MemberAdminPage.tsx` (region extraction fix)
- `backend/handler/get_members_filtered/app.py` (backend handler)
- `frontend/src/components/MemberAdminTable.tsx` (frontend table component)

## Lessons Learned

1. **Check for regional roles BEFORE checking for basic member roles** in auth validation
2. **Never hardcode user attributes** - always extract from actual user data
3. **Frontend and backend must agree** on how regional access is determined
4. **Comprehensive logging** in auth layer helped identify the issue quickly
5. **CloudWatch logs are essential** for debugging Lambda issues

## Status

✅ **RESOLVED** - Regional filtering now works correctly for all user role combinations.
