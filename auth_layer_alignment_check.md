# Authentication Layer Alignment Check

## 3 Authentication Layers to Align

### 1. **Frontend Authentication**

- Location: `frontend/src/utils/functionPermissions.ts`
- Purpose: UI permission checks, role-based component rendering
- Current Status: ✅ Already supports new role structure

### 2. **Backend Authentication**

- Location: `backend/shared/auth_utils.py`
- Purpose: API endpoint permission validation
- Current Status: ⚠️ Updated but needs verification

### 3. **Docker/Container Authentication**

- Location: Parquet generation container + other containerized functions
- Purpose: Container-based Lambda function authentication
- Current Status: ❓ Needs checking

## Alignment Requirements

All 3 layers must:

- ✅ Recognize the same role names
- ✅ Apply the same permission logic
- ✅ Support regional filtering consistently
- ✅ Handle backward compatibility during transition

## Checking Strategy

1. **Frontend Check**: Verify `functionPermissions.ts` supports new roles
2. **Backend Check**: Verify `auth_utils.py` role mappings are complete
3. **Docker Check**: Verify containerized functions use correct auth layer
4. **Integration Test**: Test end-to-end authentication flow

## New Role Structure (Reference)

### Permission Roles

- Members: `Members_CRUD`, `Members_Read`, `Members_Export`, `Members_Status_Approve`
- Events: `Events_CRUD`, `Events_Read`, `Events_Export`
- Products: `Products_CRUD`, `Products_Read`, `Products_Export`
- Communication: `Communication_CRUD`, `Communication_Read`, `Communication_Export`
- System: `System_CRUD`, `System_User_Management`, `System_Logs_Read`

### Region Roles

- `Regio_All` + 9 specific regional roles

### Special Roles

- `Verzoek_lid` - New user registration
- `hdcnLeden` - Basic member rights
- `Webshop_Management` - Webshop management
