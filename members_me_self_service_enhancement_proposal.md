# /members/me Self-Service Enhancement Proposal

## Executive Summary

**EXCELLENT IDEA!** Extending the `/members/me` endpoint to handle both GET and PUT operations for personal data would be the cleanest, most logical solution to the permission issue. This approach provides better separation of concerns and user experience.

## Current State Analysis

### Current `/members/me` Endpoint

- **Method**: GET only
- **Handler**: `backend/handler/get_member_self/app.py`
- **Permission**: Uses `members_self_read` permission
- **Functionality**:
  - ✅ Optimized with `custom:member_id` direct lookup
  - ✅ Falls back to email lookup
  - ✅ Self-lookup only (security enforced)
  - ✅ Works perfectly for hdcnLeden users

### Current Update Flow (PROBLEMATIC)

- **Endpoint**: `PUT /members/{id}`
- **Handler**: `backend/handler/update_member/app.py`
- **Permission**: Requires `['members_update', 'members_create']`
- **Problem**: ❌ hdcnLeden users get 403 Forbidden
- **Frontend**: MyAccount.tsx calls this endpoint and fails

## Proposed Solution: Enhanced /members/me Endpoint

### 1. Add PUT Method Support

Extend the current `/members/me` handler to support both GET and PUT methods:

```python
def lambda_handler(event, context):
    """
    Enhanced member self-service handler
    GET: Read own member data (existing functionality)
    PUT: Update own member data (new functionality)
    """
    method = event.get('httpMethod', 'GET')

    if method == 'GET':
        return handle_get_member_self(event, context)
    elif method == 'PUT':
        return handle_put_member_self(event, context)
    else:
        return create_error_response(405, 'Method not allowed')
```

### 2. Self-Update Logic

```python
def handle_put_member_self(event, context):
    """Handle PUT requests for self-updates"""
    try:
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Check if user has self-update permission
        if 'hdcnLeden' not in user_roles:
            return create_error_response(403, 'Self-update requires hdcnLeden role')

        # Get member record using optimized lookup
        member_id_from_token = extract_member_id_from_jwt(event)
        member_record = get_own_member_record(user_email, member_id_from_token)

        if not member_record:
            return create_error_response(404, 'Member record not found')

        # Parse update data
        body = json.loads(event['body'])

        # Validate field permissions (reuse existing logic)
        forbidden_fields = []
        for field_name in body.keys():
            if not can_edit_field(['hdcnLeden'], field_name, is_own_record=True):
                forbidden_fields.append(field_name)

        if forbidden_fields:
            return create_error_response(403,
                f'Cannot update fields: {forbidden_fields}. Only personal and motorcycle fields allowed.')

        # Perform update
        update_member_record(member_record['member_id'], body)

        # Return updated record
        updated_record = get_own_member_record(user_email, member_id_from_token)
        return create_success_response(updated_record)

    except Exception as e:
        return create_error_response(500, 'Internal server error')
```

### 3. API Gateway Configuration Update

```yaml
# In backend/template.yaml
GetMemberSelfFunction:
  # ... existing configuration ...
  Events:
    GetMemberSelf:
      Type: Api
      Properties:
        RestApiId: !Ref MyApi
        Path: /members/me
        Method: get
    PutMemberSelf: # ADD THIS
      Type: Api
      Properties:
        RestApiId: !Ref MyApi
        Path: /members/me
        Method: put
```

### 4. Frontend Update

```typescript
// In MyAccount.tsx - change the update call
const handleMemberUpdate = async (memberData: any) => {
  try {
    const headers = await getAuthHeaders();
    const updatedMember = await apiCall<Member>(
      fetch(API_URLS.memberSelf(), {
        // Changed from member(id) to memberSelf()
        method: "PUT",
        headers,
        body: JSON.stringify({
          ...memberData,
          updated_at: new Date().toISOString(),
        }),
      }),
      "bijwerken gegevens"
    );

    setMember(updatedMember);
  } catch (error) {
    handleError(error, "Fout bij het bijwerken van uw gegevens");
    throw error;
  }
};
```

## Benefits of This Approach

### 1. **Logical Consistency**

- `/members/me` for all self-service operations (GET and PUT)
- `/members/{id}` for admin operations only
- Clear separation of concerns

### 2. **Security Benefits**

- ✅ No need to modify existing admin permission system
- ✅ Self-contained permission logic for hdcnLeden users
- ✅ Reuses existing field-level validation
- ✅ No risk of breaking admin functionality

### 3. **Performance Benefits**

- ✅ Reuses optimized `custom:member_id` lookup
- ✅ No need for member_id in URL (self-lookup)
- ✅ Consistent caching behavior

### 4. **User Experience**

- ✅ Intuitive API design (`/me` for self-operations)
- ✅ No permission errors for regular users
- ✅ Consistent error messages

### 5. **Maintenance Benefits**

- ✅ Single handler for all self-service operations
- ✅ Shared authentication and lookup logic
- ✅ Easier to test and debug

## Implementation Plan

### Phase 1: Backend Enhancement

1. ✅ Extend `get_member_self/app.py` to handle PUT method
2. ✅ Add field validation logic (reuse from update_member)
3. ✅ Add update functionality with proper logging
4. ✅ Update API Gateway configuration

### Phase 2: Frontend Update

1. ✅ Update MyAccount.tsx to use `/members/me` for updates
2. ✅ Test self-service update flow
3. ✅ Verify error handling

### Phase 3: Testing & Validation

1. ✅ Test hdcnLeden user self-updates (should work)
2. ✅ Test field restrictions (admin fields should be blocked)
3. ✅ Test admin users still work with `/members/{id}`
4. ✅ Performance testing

## Comparison with Alternative Solutions

| Approach                        | Pros                                   | Cons                                    | Complexity |
| ------------------------------- | -------------------------------------- | --------------------------------------- | ---------- |
| **Enhanced /members/me**        | Clean API, logical, secure, performant | Requires new handler code               | Medium     |
| Fix /members/{id} permissions   | Minimal code change                    | Complex permission logic, security risk | High       |
| New /members/me/update endpoint | Keeps existing logic intact            | API inconsistency, more endpoints       | Low        |

## Recommendation

**Implement the Enhanced /members/me approach** because:

1. **Best API Design**: RESTful and intuitive
2. **Security**: Clean separation between self-service and admin operations
3. **Performance**: Reuses optimized lookup logic
4. **Maintainability**: Single handler for related operations
5. **User Experience**: No permission errors for regular users

This solution addresses the root cause (permission mismatch) while improving the overall architecture.
