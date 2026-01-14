# Get Member Self Handler

## Purpose

This handler allows users to look up their own member record using the `/members/me` endpoint. It provides a secure way for users to access their own data without requiring admin permissions.

## Endpoint

- **Path**: `/members/me`
- **Method**: `GET`
- **Authentication**: Required (JWT token)

## Permissions

- **Required Permission**: `members_self_read`
- **Granted to Roles**:
  - `hdcnLeden` (existing members)
  - `verzoek_lid` (applicants checking their status)

## Security Features

- Users can only access their own record (extracted from JWT token email)
- No ability to access other users' data
- Proper audit logging for security monitoring
- Regional restrictions don't apply (users can always see their own data)

## Response

Returns the user's complete member record from the Members DynamoDB table.

## Error Handling

- 401: Missing or invalid authorization
- 403: Insufficient permissions
- 404: Member record not found for the authenticated user
- 500: Internal server error

## Implementation Notes

- Uses GSI (email-index) if available, falls back to scan with filter
- Includes both shared auth layer and fallback auth for reliability
- Follows the new permission-based role structure
