# Role Assignment Error Handling Documentation

## Overview

This document describes the comprehensive error handling implemented for invalid role assignments in the H-DCN Cognito Authentication system.

## Enhanced Error Handling Features

### 1. Role Assignment Validation (`assign_user_roles_auth`)

#### Input Validation Errors

- **400 Bad Request**: Invalid JSON in request body
- **400 Bad Request**: No roles specified for assignment
- **400 Bad Request**: Invalid roles specified (with list of invalid roles and available roles)
- **404 Not Found**: Target user not found

#### Permission Validation Errors

- **401 Unauthorized**: Missing Authorization header
- **401 Unauthorized**: Invalid authorization token
- **401 Unauthorized**: Could not identify requesting user
- **403 Forbidden**: Insufficient permissions to assign user roles

#### Service-Level Errors

- **429 Too Many Requests**: Rate limit exceeded (with retry_after)
- **503 Service Unavailable**: Cognito internal error
- **500 Internal Server Error**: Failed to validate roles or assign roles

#### Business Rule Validation

- **Role Conflict Detection**: Prevents assignment of conflicting roles (e.g., Members_CRUD_All when Members_Read_All already assigned)
- **Self-Assignment Protection**: Prevents users from assigning System_User_Management to themselves unless they already have admin privileges

### 2. Role Removal Validation (`remove_user_role_auth`)

#### Input Validation Errors

- **400 Bad Request**: Role does not exist (with available roles list)
- **400 Bad Request**: User is not assigned to the specified role
- **400 Bad Request**: Cannot remove hdcnLeden role (basic member role protection)
- **400 Bad Request**: Cannot remove System_User_Management from yourself if you're the only admin

#### Service-Level Errors

- **404 Not Found**: User not found
- **404 Not Found**: Role not found
- **429 Too Many Requests**: Rate limit exceeded
- **503 Service Unavailable**: Cognito internal error
- **500 Internal Server Error**: Failed to validate or remove role

### 3. Permission Calculation Error Handling (`calculate_user_permissions`)

#### Robust Error Handling

- **Invalid Input Types**: Handles non-list inputs gracefully
- **Unknown Roles**: Logs warnings for unknown roles but continues processing valid ones
- **Empty/Null Inputs**: Returns empty permissions list for empty or null role lists
- **Exception Safety**: Returns minimal safe permissions in case of unexpected errors

### 4. Business Rule Validation (`validate_role_assignment_rules`)

#### Conflict Detection

- **Hierarchical Roles**: Prevents assignment of redundant roles (CRUD roles include Read permissions)
- **Self-Assignment Rules**: Prevents privilege escalation through self-assignment
- **Regional Validation**: Framework for future regional role validation

## Error Response Format

All error responses follow a consistent structure:

```json
{
  "error": "Brief error description",
  "details": "Detailed explanation of the error",
  "invalid_roles": ["list", "of", "invalid", "roles"],
  "available_roles": ["list", "of", "valid", "roles"],
  "retry_after": 60,
  "service": "cognito"
}
```

## HTTP Status Codes

| Code | Meaning               | Usage                                   |
| ---- | --------------------- | --------------------------------------- |
| 400  | Bad Request           | Invalid input, business rule violations |
| 401  | Unauthorized          | Missing or invalid authentication       |
| 403  | Forbidden             | Insufficient permissions                |
| 404  | Not Found             | User or role not found                  |
| 429  | Too Many Requests     | Rate limiting                           |
| 500  | Internal Server Error | Unexpected errors                       |
| 503  | Service Unavailable   | External service issues                 |

## Logging and Monitoring

### Error Logging

- All errors are logged with detailed context
- Invalid role assignments are logged for audit purposes
- Rate limiting and service errors are tracked
- Business rule violations are logged with user context

### Audit Trail

- All successful role assignments include:
  - Requesting user
  - Target user
  - Assigned/removed roles
  - Timestamp
  - Updated permissions

## Testing

The error handling has been tested with:

- Invalid input types and formats
- Unknown and conflicting roles
- Permission validation scenarios
- Service error simulation
- Business rule validation

## Security Considerations

### Protection Against

- **Privilege Escalation**: Users cannot assign roles they don't have permission for
- **Self-Assignment Abuse**: Prevents users from granting themselves admin privileges
- **Role Conflicts**: Prevents assignment of conflicting or redundant roles
- **Admin Lockout**: Prevents removal of the last System_User_Management user

### Audit and Compliance

- All role changes are logged with full context
- Failed attempts are logged for security monitoring
- Business rule violations are tracked
- Rate limiting prevents abuse

## Future Enhancements

### Planned Improvements

1. **Regional Role Validation**: Validate regional role assignments based on user location
2. **Time-Based Roles**: Support for temporary role assignments
3. **Role Approval Workflow**: Multi-step approval for sensitive role assignments
4. **Enhanced Monitoring**: Real-time alerts for suspicious role assignment patterns

## Usage Examples

### Successful Role Assignment

```bash
POST /auth/users/user@example.com/roles
{
  "roles": ["Members_Read_All", "Events_Read_All"]
}
```

### Error Response for Invalid Role

```json
{
  "statusCode": 400,
  "body": {
    "error": "Invalid roles specified",
    "invalid_roles": ["NonExistentRole"],
    "available_roles": ["hdcnLeden", "Members_CRUD_All", "Members_Read_All"],
    "details": "The following roles do not exist in the system: NonExistentRole"
  }
}
```

### Error Response for Permission Denial

```json
{
  "statusCode": 403,
  "body": {
    "error": "Insufficient permissions to assign user roles",
    "required_roles": ["System_User_Management"]
  }
}
```

This comprehensive error handling ensures robust, secure, and user-friendly role assignment operations in the H-DCN authentication system.
