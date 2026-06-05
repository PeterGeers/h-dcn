# Integration Testing Guide - Member Reporting Performance

This guide provides step-by-step instructions for performing integration testing of the Member Reporting Performance feature in the development environment.

## Prerequisites

### Backend

- ✅ Backend Lambda function deployed to development
- ✅ API Gateway endpoint configured: `GET /api/members`
- ✅ DynamoDB Members table populated with test data
- ✅ Auth layer configured and working

### Frontend

- ✅ Frontend deployed to development environment
- ✅ MemberDataService implemented
- ✅ MemberList component updated with refresh functionality
- ✅ Session storage caching enabled

### Test Users

You need access to test accounts with different roles:

- **Regional User (Utrecht)**: User with `Regio_Utrecht` and `members_read` permissions
- **Regional User (Zuid-Holland)**: User with `Regio_Zuid-Holland` and `members_read` permissions
- **Regio_All User**: User with `Regio_All` and `members_read` permissions
- **CRUD User**: User with `members_update` or `members_create` permissions

---

## Test Suite 1: Complete User Flow

### Test 1.1: Regional User (Utrecht) - Load → Filter → Refresh

**Objective**: Test complete flow for a regional user

**Steps**:

1. Log in as a regional user (Utrecht)
2. Navigate to the member reporting page
3. **Verify Initial Load**:
   - [ ] Loading spinner appears
   - [ ] Data loads within 1 second
   - [ ] Only Utrecht members are displayed
   - [ ] All statuses are visible (Actief, Inactief, Opgezegd, etc.)
   - [ ] Member count badge shows correct number
   - [ ] No error messages appear

4. **Verify Session Storage**:
   - [ ] Open browser DevTools → Application → Session Storage
   - [ ] Verify `hdcn_member_data` key exists
   - [ ] Verify `hdcn_member_data_timestamp` key exists
   - [ ] Verify data contains only Utrecht members

5. **Test Client-Side Filtering**:
   - [ ] Apply status filter (e.g., "Actief")
   - [ ] Verify filter response time <200ms
   - [ ] Verify filtered count updates correctly
   - [ ] Apply region filter (should show only Utrecht)
   - [ ] Apply search filter (search by name)
   - [ ] Apply multiple filters (AND logic)
   - [ ] Verify all filters work correctly

6. **Test Navigation (Cache Persistence)**:
   - [ ] Navigate to another page (e.g., member details)
   - [ ] Navigate back to member list
   - [ ] Verify data loads instantly (from cache)
   - [ ] Verify no API call in Network tab
   - [ ] Verify filters are preserved (if applicable)

7. **Test Refresh (if CRUD user)**:
   - [ ] Click "Refresh Data" button
   - [ ] Verify loading indicator appears
   - [ ] Verify data refreshes successfully
   - [ ] Verify success toast appears
   - [ ] Verify timestamp in session storage is updated
   - [ ] Verify UI state is preserved (scroll position, filters)

**Expected Results**:

- ✅ Load time <1 second
- ✅ Only Utrecht members visible
- ✅ All statuses included
- ✅ Session storage caching works
- ✅ Filters respond <200ms
- ✅ Cache persists across navigation
- ✅ Refresh works correctly

---

### Test 1.2: Regional User (Zuid-Holland) - Regional Isolation

**Objective**: Verify regional users cannot see other regions' data

**Steps**:

1. Log in as a regional user (Zuid-Holland)
2. Navigate to the member reporting page
3. **Verify Regional Filtering**:
   - [ ] Only Zuid-Holland members are displayed
   - [ ] No Utrecht members visible
   - [ ] No Noord-Holland members visible
   - [ ] Member count matches Zuid-Holland members only

4. **Verify in Browser DevTools**:
   - [ ] Open Network tab
   - [ ] Inspect API response
   - [ ] Verify response contains only Zuid-Holland members
   - [ ] Verify no other regions in response data

**Expected Results**:

- ✅ Only Zuid-Holland members visible
- ✅ Regional isolation enforced by backend
- ✅ No data leakage from other regions

---

### Test 1.3: Regio_All User - All Regions Visible

**Objective**: Verify Regio_All users can see all members from all regions

**Steps**:

1. Log in as a Regio_All user
2. Navigate to the member reporting page
3. **Verify All Regions Visible**:
   - [ ] Members from Utrecht are visible
   - [ ] Members from Zuid-Holland are visible
   - [ ] Members from Noord-Holland are visible
   - [ ] Members from all other regions are visible
   - [ ] Member count shows total across all regions

4. **Test Filtering by Region**:
   - [ ] Apply region filter for Utrecht
   - [ ] Verify only Utrecht members shown
   - [ ] Apply region filter for Zuid-Holland
   - [ ] Verify only Zuid-Holland members shown
   - [ ] Clear filter
   - [ ] Verify all regions visible again

5. **Verify Performance**:
   - [ ] Load time <2 seconds (larger dataset)
   - [ ] Filter response time <200ms

**Expected Results**:

- ✅ All regions visible
- ✅ Load time <2 seconds
- ✅ Filters work correctly
- ✅ Member count accurate

---

### Test 1.4: CRUD User - Refresh Functionality

**Objective**: Test refresh button for CRUD users

**Steps**:

1. Log in as a CRUD user (has `members_update` or `members_create` permission)
2. Navigate to the member reporting page
3. **Verify Refresh Button Visible**:
   - [ ] "Refresh Data" button is visible
   - [ ] Button has refresh icon
   - [ ] Button is enabled

4. **Test Refresh Flow**:
   - [ ] Note current member count
   - [ ] Click "Refresh Data" button
   - [ ] Verify loading indicator appears
   - [ ] Verify button is disabled during refresh
   - [ ] Verify data refreshes successfully
   - [ ] Verify success toast appears: "Data Refreshed"
   - [ ] Verify member count updates (if data changed)

5. **Verify Cache Cleared**:
   - [ ] Open DevTools → Application → Session Storage
   - [ ] Verify timestamp is updated
   - [ ] Open Network tab
   - [ ] Verify API call was made

6. **Test UI State Preservation**:
   - [ ] Apply a filter (e.g., status = "Actief")
   - [ ] Scroll down the member list
   - [ ] Click "Refresh Data"
   - [ ] Verify filter is preserved after refresh
   - [ ] Verify scroll position is preserved

**Expected Results**:

- ✅ Refresh button visible for CRUD users
- ✅ Refresh clears cache and fetches fresh data
- ✅ Success toast appears
- ✅ UI state preserved during refresh

---

### Test 1.5: Non-CRUD User - No Refresh Button

**Objective**: Verify non-CRUD users don't see refresh button

**Steps**:

1. Log in as a non-CRUD user (only has `members_read` permission)
2. Navigate to the member reporting page
3. **Verify No Refresh Button**:
   - [ ] "Refresh Data" button is NOT visible
   - [ ] Member list displays normally
   - [ ] All other functionality works

**Expected Results**:

- ✅ No refresh button for non-CRUD users
- ✅ All other functionality works normally

---

## Test Suite 2: Performance Testing

### Test 2.1: Regional User Load Time

**Objective**: Verify regional users get data within 1 second

**Steps**:

1. Log in as a regional user
2. Clear browser cache and session storage
3. Navigate to member reporting page
4. **Measure Load Time**:
   - [ ] Open DevTools → Network tab
   - [ ] Clear network log
   - [ ] Refresh page
   - [ ] Find `/api/members` request
   - [ ] Note response time

5. **Repeat 5 times**:
   - [ ] Clear session storage
   - [ ] Refresh page
   - [ ] Record load time
   - [ ] Calculate average

**Expected Results**:

- ✅ Average load time <1 second
- ✅ Max load time <1.5 seconds
- ✅ Consistent performance across runs

**Performance Metrics**:
| Run | Load Time | Status |
|-----|-----------|--------|
| 1 | **\_**s | ✅/❌ |
| 2 | **\_**s | ✅/❌ |
| 3 | **\_**s | ✅/❌ |
| 4 | **\_**s | ✅/❌ |
| 5 | **\_**s | ✅/❌ |
| Avg | **\_**s | ✅/❌ |

---

### Test 2.2: Regio_All User Load Time

**Objective**: Verify Regio_All users get data within 2 seconds

**Steps**:

1. Log in as a Regio_All user
2. Clear browser cache and session storage
3. Navigate to member reporting page
4. **Measure Load Time** (same as Test 2.1)
5. **Repeat 3 times**

**Expected Results**:

- ✅ Average load time <2 seconds
- ✅ Max load time <3 seconds

**Performance Metrics**:
| Run | Load Time | Status |
|-----|-----------|--------|
| 1 | **\_**s | ✅/❌ |
| 2 | **\_**s | ✅/❌ |
| 3 | **\_**s | ✅/❌ |
| Avg | **\_**s | ✅/❌ |

---

### Test 2.3: Filter Response Time

**Objective**: Verify filters respond within 200ms

**Steps**:

1. Log in as any user
2. Load member data
3. **Test Various Filters**:
   - [ ] Open DevTools → Console
   - [ ] Run: `console.time('filter'); /* apply filter */; console.timeEnd('filter');`
   - [ ] Test status filter
   - [ ] Test region filter
   - [ ] Test search filter
   - [ ] Test combined filters

**Expected Results**:

- ✅ All filters respond <200ms
- ✅ No UI lag or freezing

**Performance Metrics**:
| Filter Type | Response Time | Status |
|-------------|---------------|--------|
| Status | **\_**ms | ✅/❌ |
| Region | **\_**ms | ✅/❌ |
| Search | **\_**ms | ✅/❌ |
| Combined | **\_**ms | ✅/❌ |

---

### Test 2.4: Cache Performance Benefit

**Objective**: Verify session storage caching provides performance benefit

**Steps**:

1. Log in as any user
2. Clear session storage
3. **First Load (No Cache)**:
   - [ ] Navigate to member reporting page
   - [ ] Measure load time: **\_**s
   - [ ] Verify API call in Network tab

4. **Second Load (With Cache)**:
   - [ ] Navigate away and back
   - [ ] Measure load time: **\_**s
   - [ ] Verify NO API call in Network tab
   - [ ] Verify instant load from cache

**Expected Results**:

- ✅ First load: <1-2 seconds (API call)
- ✅ Second load: <100ms (instant from cache)
- ✅ Significant performance improvement

---

## Test Suite 3: Error Scenarios

### Test 3.1: Missing JWT Token

**Objective**: Verify authentication is required

**Steps**:

1. Log out of the application
2. Try to access member reporting page directly
3. **Verify Error Handling**:
   - [ ] Redirected to login page, OR
   - [ ] Error message: "Authentication required"
   - [ ] No member data displayed

**Expected Results**:

- ✅ Access denied without authentication
- ✅ Clear error message or redirect

---

### Test 3.2: Invalid JWT Token

**Objective**: Verify invalid tokens are rejected

**Steps**:

1. Open DevTools → Application → Local Storage
2. Modify JWT token to invalid value
3. Navigate to member reporting page
4. **Verify Error Handling**:
   - [ ] Error message appears
   - [ ] No member data displayed
   - [ ] User prompted to log in again

**Expected Results**:

- ✅ Invalid token rejected
- ✅ Clear error message

---

### Test 3.3: Network Failure

**Objective**: Verify graceful handling of network errors

**Steps**:

1. Log in as any user
2. Open DevTools → Network tab
3. Enable "Offline" mode
4. Navigate to member reporting page (or click refresh)
5. **Verify Error Handling**:
   - [ ] Error message appears: "Failed to load member data"
   - [ ] "Try Again" button appears
   - [ ] No crash or blank screen

6. **Test Recovery**:
   - [ ] Disable "Offline" mode
   - [ ] Click "Try Again"
   - [ ] Verify data loads successfully

**Expected Results**:

- ✅ Graceful error handling
- ✅ Clear error message
- ✅ Recovery mechanism works

---

### Test 3.4: Server Error (500)

**Objective**: Verify handling of server errors

**Steps**:

1. (This requires backend configuration to simulate 500 error)
2. Navigate to member reporting page
3. **Verify Error Handling**:
   - [ ] Error message: "Server error. Please try again later."
   - [ ] No crash or blank screen
   - [ ] Error logged to console

**Expected Results**:

- ✅ Server error handled gracefully
- ✅ User-friendly error message

---

### Test 3.5: Permission Denied (403)

**Objective**: Verify handling of permission errors

**Steps**:

1. Log in as a user without member permissions
2. Try to access member reporting page
3. **Verify Error Handling**:
   - [ ] Error message: "You do not have permission to view member data"
   - [ ] No member data displayed
   - [ ] Clear explanation of issue

**Expected Results**:

- ✅ Permission error handled gracefully
- ✅ Clear error message

---

### Test 3.6: Empty Database

**Objective**: Verify handling of empty member list

**Steps**:

1. (This requires backend configuration to return empty list)
2. Navigate to member reporting page
3. **Verify Empty State**:
   - [ ] "No Members Found" message appears
   - [ ] No error message
   - [ ] UI displays correctly

**Expected Results**:

- ✅ Empty state handled gracefully
- ✅ Clear message to user

---

### Test 3.7: Session Storage Unavailable

**Objective**: Verify app works without session storage

**Steps**:

1. Open DevTools → Console
2. Run: `sessionStorage.clear(); Object.defineProperty(window, 'sessionStorage', { get: () => { throw new Error('Disabled'); } });`
3. Navigate to member reporting page
4. **Verify Functionality**:
   - [ ] Data loads successfully (no caching)
   - [ ] No errors in console
   - [ ] All features work normally
   - [ ] Each navigation triggers API call

**Expected Results**:

- ✅ App works without session storage
- ✅ No crashes or errors
- ✅ Graceful degradation

---

## Test Suite 4: Data Integrity

### Test 4.1: Decimal Conversion

**Objective**: Verify numeric fields are properly converted

**Steps**:

1. Log in as any user
2. Load member data
3. **Inspect API Response**:
   - [ ] Open DevTools → Network tab
   - [ ] Find `/api/members` request
   - [ ] View response
   - [ ] Verify no "Decimal" objects in response
   - [ ] Verify numeric fields are proper JSON types (int/float)

**Expected Results**:

- ✅ All numeric fields are JSON-serializable
- ✅ No Decimal objects in response

---

### Test 4.2: Calculated Fields

**Objective**: Verify calculated fields are computed correctly

**Steps**:

1. Log in as any user
2. Load member data
3. **Verify Calculated Fields**:
   - [ ] Open a member detail
   - [ ] Verify `korte_naam` is correct (voornaam + tussenvoegsel + achternaam)
   - [ ] Verify `leeftijd` is correct (age in years)
   - [ ] Verify `verjaardag` is correct (birthday in Dutch format)
   - [ ] Verify `jaren_lid` is correct (years of membership)
   - [ ] Verify `aanmeldingsjaar` is correct (year of membership start)

**Expected Results**:

- ✅ All calculated fields present
- ✅ All calculated fields correct

---

### Test 4.3: All Statuses Included

**Objective**: Verify no status filtering is applied by backend

**Steps**:

1. Log in as a regional user
2. Load member data
3. **Verify All Statuses**:
   - [ ] Check for "Actief" members
   - [ ] Check for "Inactief" members
   - [ ] Check for "Opgezegd" members
   - [ ] Check for "Verwijderd" members
   - [ ] Check for any other statuses

**Expected Results**:

- ✅ All statuses visible (no backend filtering)
- ✅ Frontend can filter by status

---

## Test Suite 5: Browser Compatibility

### Test 5.1: Chrome

**Steps**:

1. Open application in Chrome
2. Run all tests from Test Suite 1
3. **Verify**:
   - [ ] All functionality works
   - [ ] Session storage works
   - [ ] No console errors

**Expected Results**:

- ✅ Full functionality in Chrome

---

### Test 5.2: Firefox

**Steps**:

1. Open application in Firefox
2. Run all tests from Test Suite 1
3. **Verify**:
   - [ ] All functionality works
   - [ ] Session storage works
   - [ ] No console errors

**Expected Results**:

- ✅ Full functionality in Firefox

---

### Test 5.3: Safari

**Steps**:

1. Open application in Safari
2. Run all tests from Test Suite 1
3. **Verify**:
   - [ ] All functionality works
   - [ ] Session storage works
   - [ ] No console errors

**Expected Results**:

- ✅ Full functionality in Safari

---

### Test 5.4: Edge

**Steps**:

1. Open application in Edge
2. Run all tests from Test Suite 1
3. **Verify**:
   - [ ] All functionality works
   - [ ] Session storage works
   - [ ] No console errors

**Expected Results**:

- ✅ Full functionality in Edge

---

## Test Suite 6: Mobile Testing

### Test 6.1: Mobile Chrome (Android)

**Steps**:

1. Open application on Android device
2. Run key tests from Test Suite 1
3. **Verify**:
   - [ ] Responsive layout
   - [ ] Touch interactions work
   - [ ] Session storage works
   - [ ] Performance acceptable

**Expected Results**:

- ✅ Full functionality on mobile

---

### Test 6.2: Mobile Safari (iOS)

**Steps**:

1. Open application on iOS device
2. Run key tests from Test Suite 1
3. **Verify**:
   - [ ] Responsive layout
   - [ ] Touch interactions work
   - [ ] Session storage works
   - [ ] Performance acceptable

**Expected Results**:

- ✅ Full functionality on iOS

---

## Automated Test Execution

### Backend Integration Tests

```bash
# Run all backend integration tests
cd backend
pytest tests/integration/test_member_reporting_e2e.py -v

# Run specific test class
pytest tests/integration/test_member_reporting_e2e.py::TestCompleteUserFlowE2E -v

# Run with detailed output
pytest tests/integration/test_member_reporting_e2e.py -v -s
```

### Frontend Integration Tests

```bash
# Run all frontend integration tests
cd frontend
npm test -- memberReportingIntegration.test.ts

# Run with coverage
npm test -- memberReportingIntegration.test.ts --coverage

# Run in watch mode
npm test -- memberReportingIntegration.test.ts --watch
```

---

## Test Results Summary

### Overall Status

| Test Suite            | Status | Notes |
| --------------------- | ------ | ----- |
| Complete User Flow    | ⬜     |       |
| Performance Testing   | ⬜     |       |
| Error Scenarios       | ⬜     |       |
| Data Integrity        | ⬜     |       |
| Browser Compatibility | ⬜     |       |
| Mobile Testing        | ⬜     |       |

### Issues Found

| Issue # | Description | Severity | Status |
| ------- | ----------- | -------- | ------ |
|         |             |          |        |

### Performance Summary

| Metric                   | Target | Actual   | Status |
| ------------------------ | ------ | -------- | ------ |
| Regional user load time  | <1s    | **\_**s  | ⬜     |
| Regio_All user load time | <2s    | **\_**s  | ⬜     |
| Filter response time     | <200ms | **\_**ms | ⬜     |
| Cache hit performance    | <100ms | **\_**ms | ⬜     |

---

## Sign-Off

### Development Team

- [ ] All tests passed
- [ ] Performance requirements met
- [ ] No critical issues found
- [ ] Ready for production deployment

**Tested by**: ********\_\_\_********  
**Date**: ********\_\_\_********  
**Signature**: ********\_\_\_********

### Product Owner

- [ ] Functionality meets requirements
- [ ] User experience acceptable
- [ ] Ready for production deployment

**Approved by**: ********\_\_\_********  
**Date**: ********\_\_\_********  
**Signature**: ********\_\_\_********

---

## Next Steps

After successful integration testing:

1. ✅ Deploy to production
2. ✅ Monitor performance metrics
3. ✅ Gather user feedback
4. ✅ Remove old Parquet system (after validation)
5. ✅ Update documentation
6. ✅ Archive this spec as completed
