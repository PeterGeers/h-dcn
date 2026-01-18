# Manual Testing Guide - Critical User Journeys with Current Role Structure

## Overview

This guide provides step-by-step manual testing procedures for critical user journeys using the current role structure (permission + region roles). This testing validates that users have a smooth experience with the new authentication system and that all role combinations work correctly.

## Test Environment Setup

### Prerequisites

- Access to the H-DCN system with test accounts
- Test users configured with different role combinations
- Browser with developer tools for debugging
- Network access to both frontend and backend systems

### Test User Accounts Required

Create or verify the following test accounts exist:

1. **National Administrator**: `Members_CRUD + Regio_All`
2. **Regional Coordinator**: `Members_CRUD + Regio_Utrecht`
3. **Read-Only User**: `Members_Read + Regio_All`
4. **Export User**: `Members_Export + Regio_All`
5. **Incomplete Role User**: `Members_CRUD` (missing region role)
6. **Basic Member**: `hdcnLeden`

## Critical Test Scenarios

### Test Scenario 1: National Administrator (`Members_CRUD + Regio_All`)

**Expected Behavior**: Full access to all members across all regions with complete CRUD operations.

#### Test Steps:

1. **Login Process**

   - [ ] Navigate to login page
   - [ ] Enter credentials for national admin user
   - [ ] Verify successful login without errors
   - [ ] Check that dashboard loads completely
   - **Expected**: Smooth login, no error messages, full dashboard visible

2. **Member Management Access**

   - [ ] Navigate to member management section
   - [ ] Verify member list loads showing members from all regions
   - [ ] Check that region filter shows "All Regions" or similar
   - [ ] Verify member count matches expected total
   - **Expected**: All members visible, no regional restrictions

3. **CRUD Operations**

   - [ ] Create a new member (any region)
   - [ ] Edit an existing member from different regions
   - [ ] Delete a test member (if safe to do so)
   - [ ] Verify all operations complete successfully
   - **Expected**: All CRUD operations work without restrictions

4. **Regional Access Validation**

   - [ ] Filter members by different regions (Utrecht, Limburg, etc.)
   - [ ] Verify data appears for all selected regions
   - [ ] Switch between regions and verify data updates
   - **Expected**: Access to all regional data without restrictions

5. **Export and Parquet Generation**
   - [ ] Access export functionality
   - [ ] Generate parquet file (if available)
   - [ ] Download member data export
   - [ ] Verify export contains data from all regions
   - **Expected**: Full export access, all regional data included

#### Success Criteria:

- [ ] Login successful without errors
- [ ] Full access to all members across all regions
- [ ] All CRUD operations work correctly
- [ ] Export functionality works with full dataset
- [ ] No permission errors or access restrictions

---

### Test Scenario 2: Regional Coordinator (`Members_CRUD + Regio_Utrecht`)

**Expected Behavior**: Full CRUD access but restricted to Utrecht region only.

#### Test Steps:

1. **Login and Initial Access**

   - [ ] Login with regional coordinator credentials
   - [ ] Verify dashboard loads successfully
   - [ ] Check that regional restriction is clearly indicated
   - **Expected**: Successful login with clear regional context

2. **Regional Data Filtering**

   - [ ] Navigate to member management
   - [ ] Verify only Utrecht members are visible
   - [ ] Check that region filter shows "Utrecht" only
   - [ ] Attempt to access other regions (should be blocked)
   - **Expected**: Only Utrecht data visible, other regions inaccessible

3. **CRUD Operations Within Region**

   - [ ] Create a new member in Utrecht region
   - [ ] Edit existing Utrecht members
   - [ ] Verify operations complete successfully
   - [ ] Check that created members are assigned to Utrecht
   - **Expected**: Full CRUD within Utrecht, automatic region assignment

4. **Access Restriction Validation**

   - [ ] Attempt to view members from other regions
   - [ ] Try to edit members from other regions (if visible)
   - [ ] Verify appropriate error messages appear
   - **Expected**: Clear error messages, no access to other regions

5. **Export Functionality**
   - [ ] Access export features
   - [ ] Generate exports and verify only Utrecht data included
   - [ ] Check parquet generation (if available) contains only Utrecht data
   - **Expected**: Exports contain only Utrecht data

#### Success Criteria:

- [ ] Login successful with regional context clear
- [ ] Only Utrecht members visible and accessible
- [ ] CRUD operations work within Utrecht region
- [ ] Other regions properly blocked with clear error messages
- [ ] Exports contain only Utrecht data

---

### Test Scenario 3: Read-Only User (`Members_Read + Regio_All`)

**Expected Behavior**: View access to all members but no modification capabilities.

#### Test Steps:

1. **Login and Dashboard Access**

   - [ ] Login with read-only user credentials
   - [ ] Verify dashboard loads with appropriate interface
   - [ ] Check that modification buttons are hidden/disabled
   - **Expected**: Read-only interface, no edit capabilities visible

2. **Member Data Viewing**

   - [ ] Navigate to member management
   - [ ] Verify all members from all regions are visible
   - [ ] Check that member details can be viewed
   - [ ] Confirm no edit/delete buttons are present
   - **Expected**: Full viewing access, no modification options

3. **Modification Attempt Validation**

   - [ ] Attempt to create a new member (should be blocked)
   - [ ] Try to edit existing member data (should be blocked)
   - [ ] Attempt to delete members (should be blocked)
   - [ ] Verify appropriate error messages appear
   - **Expected**: All modification attempts blocked with clear messages

4. **Regional Access**

   - [ ] Filter by different regions
   - [ ] Verify data from all regions is accessible
   - [ ] Check that regional filtering works correctly
   - **Expected**: Full regional access for viewing only

5. **Export Limitations**
   - [ ] Check export functionality availability
   - [ ] Verify limited export options (if any)
   - [ ] Confirm no sensitive data export capabilities
   - **Expected**: Limited or no export access

#### Success Criteria:

- [ ] Full viewing access to all regional data
- [ ] All modification attempts properly blocked
- [ ] Clear error messages for unauthorized actions
- [ ] Read-only interface consistently maintained
- [ ] No access to sensitive export functions

---

### Test Scenario 4: Export User (`Members_Export + Regio_All`)

**Expected Behavior**: Export access to all regions but no CRUD operations.

#### Test Steps:

1. **Login and Interface**

   - [ ] Login with export user credentials
   - [ ] Verify appropriate dashboard interface
   - [ ] Check that export functions are prominently available
   - **Expected**: Export-focused interface, limited other functions

2. **Export Functionality**

   - [ ] Access member export features
   - [ ] Generate various export formats (CSV, Excel, etc.)
   - [ ] Verify exports contain data from all regions
   - [ ] Test parquet file generation (if available)
   - **Expected**: Full export access with all regional data

3. **CRUD Restriction Validation**

   - [ ] Attempt to create new members (should be blocked)
   - [ ] Try to edit existing members (should be blocked)
   - [ ] Attempt to delete members (should be blocked)
   - **Expected**: All CRUD operations blocked with clear messages

4. **Regional Export Access**
   - [ ] Export data filtered by specific regions
   - [ ] Verify regional filtering works in exports
   - [ ] Check that all regions are accessible for export
   - **Expected**: Full regional access for export purposes

#### Success Criteria:

- [ ] Full export functionality works correctly
- [ ] Access to all regional data for export
- [ ] All CRUD operations properly blocked
- [ ] Export files contain expected data from all regions

---

### Test Scenario 5: Incomplete Role User (`Members_CRUD` only)

**Expected Behavior**: Access denied with clear error messages about missing region role.

#### Test Steps:

1. **Login Process**

   - [ ] Login with incomplete role user credentials
   - [ ] Verify login completes (authentication succeeds)
   - [ ] Check initial dashboard state
   - **Expected**: Login succeeds but limited functionality

2. **Access Attempt Validation**

   - [ ] Attempt to access member management
   - [ ] Try to navigate to any member-related features
   - [ ] Verify clear error messages appear
   - **Expected**: Access blocked with helpful error messages

3. **Error Message Quality**

   - [ ] Check that error messages mention missing region assignment
   - [ ] Verify messages provide actionable guidance
   - [ ] Confirm messages suggest contacting administrator
   - **Expected**: Clear, helpful error messages with next steps

4. **System Behavior**
   - [ ] Verify system doesn't crash or show confusing errors
   - [ ] Check that user can still access basic profile functions
   - [ ] Confirm logout functionality works
   - **Expected**: Graceful handling, basic functions still work

#### Success Criteria:

- [ ] Login succeeds but member functions blocked
- [ ] Clear error messages about missing region role
- [ ] Actionable guidance provided to user
- [ ] System remains stable and usable for basic functions

---

### Test Scenario 6: Basic Member (`hdcnLeden`)

**Expected Behavior**: Access to personal data and webshop only, no admin functions.

#### Test Steps:

1. **Login and Personal Access**

   - [ ] Login with basic member credentials
   - [ ] Verify personal dashboard loads
   - [ ] Check that only personal functions are visible
   - **Expected**: Personal interface, no admin functions

2. **Personal Data Management**

   - [ ] View personal profile information
   - [ ] Edit personal details (if allowed)
   - [ ] Verify changes save correctly
   - **Expected**: Full access to own data only

3. **Webshop Access**

   - [ ] Navigate to webshop functionality
   - [ ] Browse products and services
   - [ ] Test shopping cart functionality (if safe)
   - **Expected**: Full webshop access and functionality

4. **Admin Function Blocking**
   - [ ] Attempt to access member management (should be blocked)
   - [ ] Try to access admin functions (should be blocked)
   - [ ] Verify appropriate error messages
   - **Expected**: All admin functions blocked with clear messages

#### Success Criteria:

- [ ] Full access to personal data and webshop
- [ ] All admin functions properly blocked
- [ ] Clear separation between member and admin interfaces
- [ ] Error messages appropriate for member users

---

## Docker Container Testing (Parquet Generation)

### Test Scenario 7: Docker Container Authentication

**Purpose**: Verify that Docker container handlers work correctly with the new role structure.

#### Test Steps:

1. **National Admin Parquet Generation**

   - [ ] Login as national admin (`Members_CRUD + Regio_All`)
   - [ ] Navigate to parquet generation feature
   - [ ] Trigger parquet file generation
   - [ ] Verify generation completes successfully
   - [ ] Download and verify file contains all regional data
   - **Expected**: Successful generation with full dataset

2. **Regional User Parquet Access**

   - [ ] Login as regional coordinator (`Members_CRUD + Regio_Utrecht`)
   - [ ] Attempt parquet generation
   - [ ] Verify appropriate access level (full file with frontend filtering)
   - [ ] Check that regional filtering works correctly
   - **Expected**: Access granted, regional filtering applied correctly

3. **Insufficient Permission Testing**

   - [ ] Login as read-only user (`Members_Read + Regio_All`)
   - [ ] Attempt parquet generation
   - [ ] Verify appropriate error message
   - **Expected**: Access denied with clear error message

4. **Docker Container Error Handling**
   - [ ] Test with incomplete roles
   - [ ] Verify error messages are clear and helpful
   - [ ] Check that container doesn't crash or hang
   - **Expected**: Graceful error handling in containerized environment

---

## Performance and User Experience Validation

### Test Scenario 8: Performance and Responsiveness

#### Test Steps:

1. **Login Performance**

   - [ ] Measure login time (should be < 3 seconds)
   - [ ] Verify dashboard loads quickly
   - [ ] Check for any performance regressions
   - **Expected**: Fast, responsive login process

2. **Member List Loading**

   - [ ] Time member list loading (should be < 2 seconds)
   - [ ] Test with different role combinations
   - [ ] Verify regional filtering doesn't slow down interface
   - **Expected**: Fast data loading regardless of role

3. **Permission Checking Performance**
   - [ ] Navigate between different sections quickly
   - [ ] Verify permission checks don't cause delays
   - [ ] Test rapid role-based UI updates
   - **Expected**: Instant permission validation and UI updates

---

## Error Handling and Edge Cases

### Test Scenario 9: Edge Case Validation

#### Test Steps:

1. **Network Interruption**

   - [ ] Simulate network issues during authentication
   - [ ] Verify graceful error handling
   - [ ] Check recovery when network restored
   - **Expected**: Graceful degradation and recovery

2. **Session Expiration**

   - [ ] Test behavior when session expires
   - [ ] Verify appropriate re-authentication prompts
   - [ ] Check that user data is preserved when possible
   - **Expected**: Smooth session management

3. **Concurrent User Testing**
   - [ ] Test multiple users with different roles simultaneously
   - [ ] Verify no role conflicts or data leakage
   - [ ] Check system stability under load
   - **Expected**: Stable multi-user operation

---

## Test Execution Checklist

### Pre-Test Setup

- [ ] Verify all test user accounts are configured correctly
- [ ] Confirm test environment is stable and accessible
- [ ] Prepare test data and backup procedures
- [ ] Set up monitoring and logging for test session

### During Testing

- [ ] Document all issues found with screenshots
- [ ] Record response times for performance validation
- [ ] Note any confusing UI elements or error messages
- [ ] Test on multiple browsers if possible

### Post-Test Validation

- [ ] Verify no test data remains in production systems
- [ ] Document all findings in test results
- [ ] Prioritize issues by severity and user impact
- [ ] Create action items for any failures found

---

## Test Results Documentation

### For Each Test Scenario, Document:

1. **Test Execution Status**: Pass/Fail/Partial
2. **Performance Metrics**: Response times, load times
3. **User Experience Notes**: Confusing elements, unclear messages
4. **Issues Found**: Detailed description with reproduction steps
5. **Screenshots**: Visual evidence of issues or successful flows
6. **Recommendations**: Suggested improvements or fixes

### Overall Assessment Criteria:

- **Critical Issues**: Any functionality that completely blocks users
- **High Impact Issues**: Significant workflow disruptions
- **Medium Issues**: Minor inconveniences that don't block work
- **Low Issues**: Cosmetic or edge case problems

### Success Criteria for Manual Testing:

- [ ] All critical user journeys work correctly
- [ ] Role-based access control functions properly
- [ ] Error messages are clear and actionable
- [ ] Performance meets acceptable standards
- [ ] No security vulnerabilities identified
- [ ] User experience is smooth and intuitive

---

## Next Steps After Manual Testing

1. **Document all findings** in a comprehensive test report
2. **Prioritize issues** by severity and user impact
3. **Create action items** for any failures or improvements needed
4. **Update automated tests** to cover any gaps found during manual testing
5. **Plan remediation** for any critical or high-impact issues
6. **Schedule follow-up testing** after fixes are implemented

This manual testing guide ensures comprehensive validation of the current role structure and provides confidence that users will have a smooth experience with the new authentication system.
