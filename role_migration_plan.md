# Role Migration Plan - Interactive Task Execution

## Current Status

- ✅ **Users migrated**: All users successfully moved to new permission + region structure
- ✅ **Old roles removed**: Old `_All` roles no longer exist in Cognito
- ❌ **Code broken**: Backend code still expects old role names that no longer exist
- 🎯 **URGENT**: Update codebase to use new role structure (system currently broken)

---

## Phase 1: Critical Backend Authentication (URGENT)

### Task 1.1: Update Parquet Generation Authentication

**Goal**: Fix broken parquet generation by updating to new role structure

**File**: `backend/handler/generate_member_parquet/app.py`

#### Subtask 1.1.1: Remove old Members_CRUD_All references from parquet generation ✅ COMPLETED

- [x] **Remove old Members_CRUD_All references from parquet generation**: Update authentication logic to use new role structure

#### Subtask 1.1.2: Add new role checking for Members_CRUD + Regio combinations

- [ ] **Add new role checking for Members_CRUD + Regio combinations**: Implement validation for permission + region role pairs

#### Subtask 1.1.3: Test parquet generation with Members_CRUD + Regio_All

- [ ] **Test parquet generation with Members_CRUD + Regio_All**: Verify full access works with new roles

#### Subtask 1.1.4: Test parquet generation with Members_CRUD + Regio_Groningen/Drenthe

- [ ] **Test parquet generation with Members_CRUD + Regio_Groningen/Drenthe**: Verify regional access works correctly

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Task 1.2

---

### Task 1.2: Update Parquet Download Authentication

**Goal**: Fix broken parquet download by updating to new role structure with regional filtering

**File**: `backend/handler/download_parquet/app.py`

#### Subtask 1.2.1: Remove old Members_Read_All references from parquet download

- [ ] **Remove old Members_Read_All references from parquet download**: Update download handler authentication logic

#### Subtask 1.2.2: Add new role checking for Members_Read + Regio combinations

- [ ] **Add new role checking for Members_Read + Regio combinations**: Implement validation for read permissions with regions

#### Subtask 1.2.3: Implement regional filtering in parquet download

- [ ] **Implement regional filtering in parquet download**: Add server-side regional data filtering

#### Subtask 1.2.4: Test parquet download with Members_Read + Regio_All

- [ ] **Test parquet download with Members_Read + Regio_All**: Verify national read access works

#### Subtask 1.2.5: Test parquet download with Members_Read + Regio_Groningen/Drenthe

- [ ] **Test parquet download with Members_Read + Regio_Groningen/Drenthe**: Verify regional read access works

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Task 1.3

---

### Task 1.3: Clean Up Backend Auth Utils

**Goal**: Remove backward compatibility code from shared auth utilities

**File**: `backend/shared/auth_utils.py`

**Tasks**:

- [ ] **Remove backward compatibility code from auth_utils.py**

- [ ] **Update role mapping functions for new structure only**

- [ ] **Remove legacy role checking functions**

- [ ] **Test auth_utils with new role combinations**

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Phase 2

---

## Phase 2: Member Management Handlers

### Task 2.1: Update Member CRUD Handler

**Goal**: Fix member update functionality with new role structure

**File**: `backend/handler/update_member/app.py`

**Tasks**:

- [ ] Remove old Members_CRUD_All references from update_member
- [ ] Add new role checking for Members_CRUD + Regio combinations
- [ ] Implement regional access controls for member updates
- [ ] Test member update with regional restrictions

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Task 2.2

---

### Task 2.2: Update Member Read Handlers

**Goal**: Fix member read functionality with new role structure

**Files**: `backend/handler/get_member_byid/app.py`, `backend/handler/get_members/app.py`

**Tasks**:

- [ ] Remove old Members_Read_All references from get_member_byid
- [ ] Add new role checking for Members_Read + Regio combinations
- [ ] Remove old Members_Read_All references from get_members
- [ ] Add regional filtering to get_members handler
- [ ] Test member reads with regional restrictions

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Phase 3

---

## Phase 3: Secondary Handlers

### Task 3.1: Update Product Handlers

**Goal**: Update product management to use new role structure

**File**: `backend/handler/update_product/app.py`

**Tasks**:

- [ ] Remove old Products_CRUD_All references from update_product
- [ ] Add new role checking for Products_CRUD + Regio combinations
- [ ] Test product operations with new role structure

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Task 3.2

---

### Task 3.2: Update Event Handlers

**Goal**: Update event management to use new role structure

**File**: `backend/handler/update_event/app.py`

**Tasks**:

- [ ] Remove old Events_CRUD_All references from update_event
- [ ] Add new role checking for Events_CRUD + Regio combinations
- [ ] Test event operations with new role structure

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Task 3.3

---

### Task 3.3: Update Order and Payment Handlers

**Goal**: Update order and payment handlers to use new role structure

**Files**: `backend/handler/update_order_status/app.py`, `backend/handler/update_payment/app.py`

**Tasks**:

- [ ] Remove old role references from update_order_status
- [ ] Add new role checking to update_order_status
- [ ] Remove old role references from update_payment
- [ ] Add new role checking to update_payment
- [ ] Test order and payment operations with new roles

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Phase 4

---

## Phase 4: Frontend Updates

### Task 4.1: Update Frontend Function Permissions

**Goal**: Update frontend to use new role structure

**File**: `frontend/src/utils/functionPermissions.ts`

**Tasks**:

- [ ] Remove old \_All role references from functionPermissions.ts
- [ ] Add support for new permission + region role combinations
- [ ] Update role checking logic for UI permissions
- [ ] Test frontend UI with new role combinations

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Task 4.2

---

### Task 4.2: Update Frontend Parquet Service

**Goal**: Update frontend parquet data service for new role structure

**File**: `frontend/src/services/ParquetDataService.ts`

**Tasks**:

- [ ] Remove old role references from ParquetDataService.ts
- [ ] Update role checking for parquet data access
- [ ] Implement regional filtering logic for new role structure
- [ ] Test parquet loading with regional users

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Phase 5

---

## Phase 5: Final Cleanup

### Task 5.1: Update Auth Fallback Files

**Goal**: Clean up all remaining auth_fallback.py files

**Files**: `backend/handler/*/auth_fallback.py` (multiple files)

**Tasks**:

- [ ] Find all auth_fallback.py files in backend
- [ ] Remove old role references from all auth_fallback files
- [ ] Update auth_fallback files to new role structure
- [ ] Test handlers with updated auth_fallback files

**Approval Gate**: ✋ **STOP** - Get approval before proceeding to Task 5.2

---

### Task 5.2: Final System Testing

**Goal**: Remove any remaining old role references and comprehensive testing

**Files**: All system components

**Tasks**:

- [ ] Search codebase for remaining old role references
- [ ] Update test scripts to use new role combinations
- [ ] Run comprehensive end-to-end system tests
- [ ] Validate system works with all new role combinations

**Final Approval Gate**: ✋ **STOP** - Get final approval for production deployment

---

## Testing Strategy

### After Each Task

Test with these role combinations:

- `Members_CRUD + Regio_All` (full access)
- `Members_Read + Regio_All` (national read-only)
- `Members_Read + Regio_Groningen/Drenthe` (regional access)
- User with incomplete roles (should fail gracefully)

### Success Criteria

- [ ] All handlers work with new role structure ONLY
- [ ] Regional filtering works correctly
- [ ] No authentication errors for users with proper role combinations
- [ ] Authentication properly fails for users without required roles
- [ ] Parquet system works end-to-end
- [ ] Frontend can authenticate and download data
- [ ] No references to old `_All` roles remain in codebase

---

## Current Role Structure Reference

### Permission Roles (What you can do)

- `Members_CRUD` - Full member management (includes read and export)
- `Members_Read` - Read member data
- `Members_Export` - Export member data (for mailing lists, reports, etc.)
- `Events_CRUD` - Full event management (includes read and export)
- `Events_Read` - Read event data
- `Events_Export` - Export event data
- `Products_CRUD` - Full product management (includes read and export)
- `Products_Read` - Read product data
- `Products_Export` - Export product data
- `Communication_CRUD` - Full communication management (includes read and export)
- `Communication_Read` - Read communication data
- `Communication_Export` - Export communication data
- `System_CRUD` - Full system administration permissions
- `System_Logs_Read` - Permission to read system logs and audit trails
- `System_User_Management` - System user management permissions
- `Verzoek Lid` - Role for new user registration (no permissions except signup)

### Region Roles (Where you can access)

- `Regio_All` - Access to all regions including Overig
- `Regio_Noord-Holland` - Access to Noord-Holland region
- `Regio_Zuid-Holland` - Access to Zuid-Holland region
- `Regio_Friesland` - Access to Friesland region
- `Regio_Utrecht` - Access to Utrecht region
- `Regio_Oost` - Access to Oost region
- `Regio_Limburg` - Access to Limburg region
- `Regio_Groningen/Drenthe` - Access to Groningen/Drenthe region
- `Regio_Brabant/Zeeland` - Access to Brabant/Zeeland region
- `Regio_Duitsland` - Access to Duitsland region

---

## Ready to Start?

**Next Action**: Click the "Start task" button next to the first task:

**"Remove old Members_CRUD_All references from parquet generation"**

This will start the systematic migration process with interactive task buttons and approval gates.
