# User Management Guide

## Overview

This guide covers user management in the H-DCN Portal, including user roles, permissions, account lifecycle, and administrative procedures. The system uses AWS Cognito for user authentication and role-based access control.

## User Types and Roles

### User Categories

1. **Staff Members** (`@h-dcn.nl` emails)

   - Automatic elevated permissions
   - Access to administrative functions
   - Google OAuth authentication available

2. **Regular Members** (all other emails)

   - Basic member permissions
   - Passkey or Google OAuth authentication
   - Self-service account management

3. **System Administrators**
   - Full system access
   - User management capabilities
   - System configuration access

### Role Hierarchy

| Role                       | Precedence | Description             | Typical Users              |
| -------------------------- | ---------- | ----------------------- | -------------------------- |
| `System_User_Management`   | 5          | System administration   | Webmaster, IT Admin        |
| `Members_CRUD_All`         | 10         | Full member management  | Board members, Admin staff |
| `Members_Status_Approve`   | 15         | Approve member changes  | Chairman, Secretary        |
| `Members_Read_All`         | 20         | View all member data    | Regional coordinators      |
| `Events_CRUD_All`          | 25         | Full event management   | Event coordinators         |
| `Events_Read_All`          | 30         | View events             | All staff                  |
| `Products_CRUD_All`        | 35         | Webshop management      | Webshop managers           |
| `Products_Read_All`        | 40         | View products           | Sales staff                |
| `Communication_Export_All` | 45         | Export member data      | Marketing team             |
| `Communication_Read_All`   | 50         | View communication data | Communication team         |
| `System_Logs_Read`         | 55         | View system logs        | Technical staff            |
| `hdcnLeden`                | 100        | Basic member access     | All members                |

## User Account Lifecycle

### 1. Account Creation

#### Google OAuth Users

1. **Automatic Creation**

   - User clicks "Sign in with Google"
   - Google OAuth validates Google account
   - Account created automatically in Cognito
   - Roles assigned based on email domain via post-confirmation trigger

2. **Manual Creation by Admin**
   ```bash
   # Create user via AWS CLI
   aws cognito-idp admin-create-user \
     --user-pool-id eu-west-1_OAT3oPCIm \
     --username user@example.com \
     --user-attributes Name=email,Value=user@example.com \
     --temporary-password "TempPass123!" \
     --message-action SUPPRESS
   ```

#### Regular Members (Passkey)

1. **Self-Registration**

   - User visits registration page
   - Enters email address
   - Receives verification email
   - Completes email verification
   - Sets up passkey authentication
   - Account activated with basic role

2. **Bulk Import**
   - Admin uploads CSV file
   - System creates accounts in batch
   - Verification emails sent automatically
   - Users complete passkey setup individually

### 2. Account Activation

#### Email Verification Process

1. **Verification Email Sent**

   - Dutch language template
   - 24-hour validity
   - Clear instructions

2. **User Clicks Verification Link**

   - Email marked as verified
   - Account status updated to confirmed
   - Post-confirmation trigger executes

3. **Role Assignment**
   - Staff users: Multiple roles assigned
   - Regular members: `hdcnLeden` role assigned
   - Custom attributes populated

#### Passkey Setup (Regular Members)

1. **Passkey Registration Prompt**

   - User guided through setup process
   - Browser shows biometric prompt
   - Credential stored in Cognito

2. **Backup Authentication**
   - Email verification as fallback
   - Cross-device authentication options
   - Recovery procedures documented

### 3. Account Maintenance

#### Regular Updates

- **Profile Information**: Users can update their own profile
- **Email Changes**: Require re-verification
- **Passkey Management**: Add/remove authentication methods
- **Preference Settings**: Communication and privacy preferences

#### Administrative Updates

- **Role Changes**: Admin can modify user roles
- **Account Status**: Enable/disable accounts
- **Attribute Updates**: Modify custom attributes
- **Group Membership**: Add/remove from groups

### 4. Account Deactivation

#### Temporary Suspension

```bash
# Disable user account
aws cognito-idp admin-disable-user \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --username user@example.com
```

#### Permanent Deletion

```bash
# Delete user account (irreversible)
aws cognito-idp admin-delete-user \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --username user@example.com
```

## Permission System

### Role-Based Access Control (RBAC)

#### Permission Calculation

```typescript
// Frontend permission checking
const hasPermission = (user: CognitoUser, requiredRoles: string[]): boolean => {
  const userRoles =
    user.signInUserSession?.idToken?.payload["cognito:groups"] || [];
  return requiredRoles.some((role) => userRoles.includes(role));
};

// Usage example
if (hasPermission(user, ["Members_CRUD_All", "System_User_Management"])) {
  // Show admin interface
}
```

#### Function-Level Permissions

```typescript
// Function-specific access control
const FUNCTION_PERMISSIONS = {
  member_management: {
    read: ["Members_Read_All", "Members_CRUD_All"],
    write: ["Members_CRUD_All"],
  },
  event_management: {
    read: ["Events_Read_All", "Events_CRUD_All"],
    write: ["Events_CRUD_All"],
  },
};
```

### Permission Inheritance

- **Additive Model**: Users can have multiple roles
- **Highest Precedence**: Lower precedence numbers override higher ones
- **No Conflicts**: Permissions are combined, not conflicted

## Administrative Procedures

### User Management Interface

#### Accessing User Management

1. **Login as Administrator**

   - Must have `System_User_Management` role
   - Navigate to "Ledenadministratie" → "Cognito Beheer"

2. **User Management Tab**
   - View all users
   - Search and filter users
   - Create new users
   - Edit user details
   - Manage user roles

#### Common Administrative Tasks

##### 1. Create New Staff User

```typescript
// Via admin interface
const createStaffUser = async (email: string, name: string) => {
  const userData = {
    email: email,
    given_name: name.split(" ")[0],
    family_name: name.split(" ").slice(1).join(" "),
    email_verified: "true",
  };

  await cognitoService.createUser(userData);
  await cognitoService.assignRoles(email, STAFF_ROLES);
};
```

##### 2. Bulk User Import

```csv
# CSV format for bulk import
email,given_name,family_name,member_id
john.doe@example.com,John,Doe,12345
jane.smith@example.com,Jane,Smith,12346
```

```typescript
// Process CSV upload
const processBulkImport = async (csvData: string) => {
  const users = parseCSV(csvData);

  for (const user of users) {
    await createUser(user);
    await sendVerificationEmail(user.email);
  }
};
```

##### 3. Role Assignment

```typescript
// Assign roles to user
const assignUserRoles = async (email: string, roles: string[]) => {
  for (const role of roles) {
    await cognitoService.addUserToGroup(email, role);
  }
};

// Remove roles from user
const removeUserRoles = async (email: string, roles: string[]) => {
  for (const role of roles) {
    await cognitoService.removeUserFromGroup(email, role);
  }
};
```

### Monitoring and Auditing

#### User Activity Monitoring

```bash
# Monitor authentication events
aws logs filter-log-events \
  --log-group-name /aws/cognito/userpools/eu-west-1_OAT3oPCIm \
  --filter-pattern "{ $.eventName = \"SignIn\" }"
```

#### Role Change Auditing

```python
# Log role changes
def log_role_change(admin_user: str, target_user: str, action: str, role: str):
    logger.info(f"Role change: {admin_user} {action} role {role} for {target_user}")

    # Send to audit system
    audit_service.log_event({
        'event_type': 'role_change',
        'admin_user': admin_user,
        'target_user': target_user,
        'action': action,
        'role': role,
        'timestamp': datetime.utcnow().isoformat()
    })
```

#### Security Monitoring

- **Failed Login Attempts**: Monitor for brute force attacks
- **Unusual Access Patterns**: Detect anomalous behavior
- **Permission Escalation**: Track role assignment changes
- **Account Lockouts**: Monitor account security events

## Troubleshooting User Issues

### Common User Problems

#### 1. User Can't Login

**Diagnosis Steps**:

1. Check account status (enabled/disabled)
2. Verify email address is correct
3. Check authentication method availability
4. Test WebAuthn support (for passkey users)

**Solutions**:

```bash
# Check user status
aws cognito-idp admin-get-user \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --username user@example.com

# Enable disabled account
aws cognito-idp admin-enable-user \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --username user@example.com
```

#### 2. User Has Wrong Permissions

**Diagnosis Steps**:

1. Check user's group memberships
2. Verify role assignments
3. Test permission calculation

**Solutions**:

```bash
# List user's groups
aws cognito-idp admin-list-groups-for-user \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --username user@example.com

# Add user to group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --username user@example.com \
  --group-name Members_Read_All
```

#### 3. Passkey Authentication Fails

**Common Causes**:

- Browser doesn't support WebAuthn
- User cancelled biometric prompt
- Credential not properly stored
- Mobile timeout issues

**Solutions**:

1. Guide user through passkey re-setup
2. Provide email verification fallback
3. Check browser compatibility
4. Test on different device

### Account Recovery Procedures

#### Google OAuth Account Recovery

1. **Google OAuth Issues**

   - Verify Google Workspace account status
   - Check OAuth configuration
   - Test with different browser

2. **Account Lockout**
   - Admin can unlock account via Cognito Console
   - Reset authentication methods if needed
   - Provide temporary access if urgent

#### Member Account Recovery

1. **Lost Passkey Access**

   - Email verification fallback available
   - Guide through passkey re-setup
   - Cross-device authentication options

2. **Email Access Lost**
   - Admin verification required
   - Update email address in system
   - Re-verify new email address

## Best Practices

### Security Best Practices

1. **Regular Role Reviews**

   - Quarterly review of user roles
   - Remove unnecessary permissions
   - Audit administrative access

2. **Account Lifecycle Management**

   - Prompt deactivation of departed staff
   - Regular cleanup of inactive accounts
   - Monitor for unused accounts

3. **Authentication Security**
   - Encourage passkey adoption
   - Monitor for authentication anomalies
   - Regular security awareness training

### Operational Best Practices

1. **User Onboarding**

   - Clear setup instructions
   - Support during initial setup
   - Documentation for common issues

2. **Change Management**

   - Test role changes in development
   - Document all permission changes
   - Communicate changes to affected users

3. **Monitoring and Alerting**
   - Set up alerts for authentication failures
   - Monitor role assignment changes
   - Regular audit of user permissions

## Integration with External Systems

### Member Database Synchronization

```python
# Sync with existing member database
def sync_member_data():
    cognito_users = get_all_cognito_users()
    member_db_users = get_member_database_users()

    for cognito_user in cognito_users:
        member_data = find_member_by_email(cognito_user.email)
        if member_data:
            update_cognito_attributes(cognito_user, member_data)
```

### CRM Integration

```typescript
// Update CRM when user data changes
const updateCRM = async (userId: string, changes: UserChanges) => {
  await crmService.updateContact(userId, {
    email: changes.email,
    firstName: changes.given_name,
    lastName: changes.family_name,
    membershipStatus: changes.membership_status,
  });
};
```

### Email Marketing Integration

```python
# Sync user preferences with email marketing platform
def sync_email_preferences(user_email: str, preferences: dict):
    marketing_service.update_subscriber(user_email, {
        'newsletter_opt_in': preferences.get('newsletter', False),
        'event_notifications': preferences.get('events', True),
        'product_updates': preferences.get('products', False)
    })
```

---

**Last Updated**: December 29, 2025  
**Version**: Production v2.0  
**Maintained By**: H-DCN Development Team
