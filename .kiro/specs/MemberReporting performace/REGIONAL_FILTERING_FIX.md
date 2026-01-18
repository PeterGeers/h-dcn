# Regional Filtering Fix - Member Admin Page

**Date**: 2026-01-18  
**Issue**: Users seeing all members instead of regionally-filtered members  
**Status**: ✅ FIXED

## Problem Description

User Peter Geers (Regio_Utrecht) was seeing ALL 1229 members instead of only the 106 Utrecht members he should have access to.

### Root Cause

The `/members` page (MemberAdminPage component) was calling the **OLD** `/members` endpoint which returns ALL members without regional filtering, instead of the **NEW** `/api/members` endpoint which implements backend regional filtering.

**Network Analysis**:

- OLD endpoint being called: `https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev/members`
- NEW endpoint should be: `https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev/api/members`

## Technical Details

### Before Fix

**File**: `frontend/src/modules/members/MemberAdminPage.tsx`

```typescript
// OLD CODE - Using API_URLS.members() which calls /members
const loadMembers = async () => {
  try {
    setLoading(true);
    const headers = await getAuthHeadersForGet();
    const data = await apiCall<any>(
      fetch(API_URLS.members(), { headers }), // ❌ Calls /members (no filtering)
      "laden leden",
    );
    setMembers(Array.isArray(data) ? data : data?.members || []);
  } catch (error) {
    handleError(error, "Fout bij het laden van leden");
  } finally {
    setLoading(false);
  }
};
```

### After Fix

```typescript
// NEW CODE - Using MemberDataService which calls /api/members
import { MemberDataService } from "../../services/MemberDataService";

const loadMembers = async () => {
  try {
    setLoading(true);

    // Use NEW MemberDataService which calls /api/members with regional filtering
    const data = await MemberDataService.fetchMembers(); // ✅ Calls /api/members (with filtering)
    setMembers(data);

    console.log(
      `[MemberAdminPage] Loaded ${data.length} members with regional filtering`,
    );
  } catch (error) {
    handleError(error, "Fout bij het laden van leden");
  } finally {
    setLoading(false);
  }
};
```

## Changes Made

### 1. Updated MemberAdminPage.tsx

**Import Added**:

```typescript
import { MemberDataService } from "../../services/MemberDataService";
```

**Load Members Function**:

- Replaced `fetch(API_URLS.members())` with `MemberDataService.fetchMembers()`
- This ensures the component uses `/api/members` endpoint with regional filtering

**Refresh Members Function**:

- Replaced manual fetch with `MemberDataService.refreshMembers()`
- Maintains consistency with the new service

### 2. Benefits of Using MemberDataService

1. **Regional Filtering**: Backend filters members by user's region BEFORE sending to frontend
2. **Session Storage Caching**: Faster subsequent loads (no repeated API calls)
3. **Calculated Fields**: Automatically computes korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar
4. **Error Handling**: Comprehensive error handling with user-friendly messages
5. **Consistent API**: Single source of truth for member data fetching

## Verification

### Expected Behavior After Fix

**For Peter Geers (Regio_Utrecht)**:

- Should see: **106 Utrecht members**
- Should NOT see: Members from other regions (Noord-Holland, Zuid-Holland, etc.)

**For Regio_All users**:

- Should see: **ALL 1229 members** (no filtering)

### Testing Steps

1. Login as Peter Geers (peter@pgeers.nl)
2. Navigate to `/members` page
3. Check member count badge
4. Verify only Utrecht members are displayed
5. Check browser console for log: `[MemberAdminPage] Loaded 106 members with regional filtering`
6. Check Network tab: Should call `/api/members` NOT `/members`

## Backend Endpoints

### OLD Endpoint (No Filtering)

- **Path**: `/members`
- **Handler**: `backend/handler/get_members/app.py`
- **Behavior**: Returns ALL members (with some regional filtering logic but not working correctly)
- **Status**: ⚠️ Still exists for backward compatibility

### NEW Endpoint (With Filtering)

- **Path**: `/api/members`
- **Handler**: `backend/handler/get_members_filtered/app.py`
- **Behavior**: Filters members by user's regional permissions BEFORE sending
- **Status**: ✅ Active and working correctly

## Deployment

**Deployment Script**: `scripts/deployment/frontend-build-and-deploy-fast.ps1`

**Deployment Time**: 48.3 seconds

- Build: 33.1 seconds
- Deploy: 14.6 seconds
- Smoke tests: 1.4 seconds

**Smoke Test Results**: ✅ All 4 tests passed

**CloudFront URL**: https://de1irtdutlxqu.cloudfront.net

## Related Files

### Frontend

- `frontend/src/modules/members/MemberAdminPage.tsx` - Fixed to use MemberDataService
- `frontend/src/services/MemberDataService.ts` - Service that calls /api/members
- `frontend/src/components/MemberList.tsx` - Example component using MemberDataService
- `frontend/src/config/api.ts` - API endpoint configuration

### Backend

- `backend/handler/get_members_filtered/app.py` - NEW handler with regional filtering
- `backend/handler/get_members/app.py` - OLD handler (still exists)

## Future Improvements

1. **Deprecate OLD Endpoint**: Consider removing `/members` endpoint once all components are migrated
2. **Update Other Components**: Check if any other components are still using the old endpoint
3. **Add Regional Indicator**: Show user's region in the UI header
4. **Add Refresh Button**: Allow users to manually refresh data (already in MemberList component)

## Related Spec Tasks

This fix addresses issues discovered during:

- **Task 15**: Remove old Parquet system from production
- **Task 14**: Update member reporting page to use new service

The regional filtering was working in the NEW components but the main `/members` page was still using the OLD API endpoint.
