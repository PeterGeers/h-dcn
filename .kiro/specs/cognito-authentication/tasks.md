# H-DCN Cognito Authentication - Implementation Tasks

## Overview

This document outlines the implementation tasks for the H-DCN Cognito Authentication system, divided into MVP (Minimum Viable Product) and Full Implementation phases.

**MVP Goal**: Basic passwordless authentication with essential role-based permissions
**Full Goal**: Complete system with all advanced features and optimizations

### Infrastructure as Code (IaC) Approach

**This project uses Infrastructure as Code for AWS resource management:**

- **Primary Tool**: AWS SAM (Serverless Application Model) via `backend/template.yaml`
- **Resources Managed**: Cognito User Pool, User Pool Groups, Lambda functions, DynamoDB tables
- **Deployment**: `sam build && sam deploy` for infrastructure changes
- **Version Control**: All infrastructure changes are tracked in Git
- **Environments**: Consistent deployment across dev/staging/production

**IaC Benefits for this project:**

- ✅ **Repeatable deployments** across environments
- ✅ **Version controlled** infrastructure changes
- ✅ **Automated provisioning** and updates
- ✅ **Consistent configuration** between environments
- ✅ **Easy rollbacks** and change tracking

### Key Concepts: Passwordless Role-Based Authentication

**H-DCN uses a passwordless role-based authentication approach:**

1. **User accounts** authenticate via passkeys (WebAuthn) with email recovery fallback
2. **Roles are assigned** to user accounts based on organizational functions and membership status
3. **Permissions are determined** by the combination of roles assigned to the user
4. **No passwords required** - leverages AWS Cognito's native passwordless capabilities (November 2024)

**Examples:**

- `jan.jansen@gmail.com` → `hdcnLeden` role → basic member permissions (own data + webshop)
- `marie.admin@h-dcn.nl` → `Members_CRUD_All`, `System_User_Management` roles → admin permissions
- `piet.chairman@gmail.com` → `Members_Read_All`, `Members_Status_Approve` roles → chairman permissions

**Technical Note**: H-DCN roles are implemented as AWS Cognito Groups. Each user can be assigned to multiple groups, and the combination of groups determines their effective permissions.

## MVP Implementation (Phase 1)

### MVP-1: Cognito Passwordless Setup

**Priority**: Critical
**Estimated Effort**: 3-4 days

#### Tasks:

1. **Create IaC for Cognito User Pool configuration**

   - [x] Review existing `backend/template.yaml` SAM template structure
   - [x] Add Cognito User Pool resource to SAM template:
     ```yaml
     # Implementation checklist:
     # [ x] Define CognitoUserPool resource with passwordless configuration
     # [ x] Set EmailConfiguration for SES integration
     # [ x] Configure Policies for passwordless authentication
     # [ x] Set UserPoolDomain for hosted UI (if needed)
     # [ x] Define appropriate DeletionPolicy
     ```
   - [x] Configure User Pool for passwordless authentication in IaC:
     - [x] Set `UsernameAttributes: [email]` for email as username
     - [x] Configure `EmailVerificationMessage` and `EmailVerificationSubject`
     - [x] Set `MfaConfiguration: "OFF"` for regular users
     - [x] Enable `EnabledMfas: ["SOFTWARE_TOKEN_MFA"]` for admin roles
     - [x] Configure `PasswordPolicy` to allow passwordless (minimum requirements)
   - [x] Add User Pool Client resource:
     - [x] Configure `AuthFlows: ["ALLOW_USER_AUTH"]` for choice-based auth
     - [x] Set `ExplicitAuthFlows` for WebAuthn support
     - [x] Configure token validity periods
     - [x] Set appropriate `ReadAttributes` and `WriteAttributes`
   - [x] Add outputs for User Pool ID and Client ID for application use

2. **Configure Cognito for native passwordless features**

   - [x] Navigate to AWS Console to verify IaC deployment
   - [x] Enable "Email message one-time password" option (manual verification)
   - [x] Enable "WebAuthn passkey" authentication option (manual verification)
   - [x] Configure email templates for verification emails (add to IaC if possible)
   - [x] Set up custom email templates for account recovery (add to IaC if possible)
   - [x] Test email delivery configuration with SES
   - [x] Configure email sender settings and domain verification

3. **Deploy and test passwordless authentication flow**
   - [x] Deploy SAM template with new Cognito configuration:
     - [x] Run `sam build` to build the template
     - [x] Run `sam deploy` to deploy infrastructure changes
     - [x] Verify Cognito User Pool is created with correct settings
     - [x] Verify User Pool Client has correct configuration
   - [x] Test infrastructure deployment:
     - [x] Create test user account with email-only registration
     - [x] Verify email verification process works end-to-end
     - [x] Test passkey registration on desktop browser (Chrome/Edge)
     - [x] Test passkey registration on mobile device (iOS/Android)
     - [x] Test passkey authentication across different devices
     - [x] Test email-based account recovery flow
     - [x] Verify no password prompts appear in any flow
     - [x] Document any browser compatibility issues

#### Acceptance Criteria:

- [x] **IaC template includes Cognito User Pool configuration**
  - [x] SAM template defines CognitoUserPool resource
  - [x] User Pool is configured for passwordless authentication
  - [x] User Pool Client supports choice-based authentication
  - [x] Email configuration is properly set up
  - [x] Template can be deployed successfully
- [x] **Cognito User Pool configured for passwordless authentication**
  - [x] Pool is on Essentials tier (verified post-deployment)
  - [x] Email is configured as username
  - [x] Password requirements are minimal/optional
  - [x] WebAuthn/FIDO2 is enabled
- [x] **Email-only registration working without password requirements**
  - [x] Users can register with email only
  - [x] No password fields appear in registration
  - [x] Email verification is mandatory
- [x] **Passkey registration and authentication functional across devices**
  - [x] Passkey registration works on desktop browsers
  - [x] Passkey registration works on mobile devices
  - [x] Cross-device authentication is functional
- [x] **Email-based account recovery working without password fallback**
  - [x] Recovery emails are sent successfully
  - [x] Recovery flow leads to new passkey setup
  - [x] No password reset options are available
- [x] **WebAuthn support verified on mobile and desktop browsers**
  - [x] Chrome/Edge desktop support confirmed
  - [x] Safari desktop support confirmed
  - [x] Mobile browser support confirmed
  - [x] Compatibility matrix documented

---

### MVP-2: Update Existing Module Authentication

**Priority**: Critical
**Estimated Effort**: 3-4 days

#### Tasks:

1. **Review and update existing parameter-based module access system**

   - [x] Audit current parameter-based module visibility implementation
   - [x] Document existing `frontend/src/utils/parameterService.tsx` functionality
   - [x] Map current membership type restrictions and module access rules
   - [x] Identify integration points with Cognito authentication
   - [x] Create compatibility matrix for existing vs new permissions
   - [x] Plan migration strategy to preserve existing functionality

2. **Update existing FunctionPermissionManager for role-based system**

   - [x] Review current `frontend/src/utils/functionPermissions.ts` implementation
   - [x] Add `getUserRoles()` utility function to extract Cognito groups
   - [x] Add `calculatePermissions()` function for role-based permissions
   - [x] Extend `FunctionPermissionManager.create()` method with role logic
   - [x] Implement role permission mapping constants
   - [x] Add backward compatibility for existing permission checks
   - [x] Test permission calculation with multiple roles

   ```typescript
   // Implementation checklist:
   // [x] getUserRoles() extracts cognito:groups from user token
   // [x] calculatePermissions() combines permissions from all roles
   // [x] ROLE_PERMISSIONS constant defines role-to-permission mapping
   // [x] Existing membership permissions are preserved
   // [x] New role permissions are additive to existing permissions
   ```

3. **Update existing module access control**

   - [x] **Members module** (`frontend/src/modules/members/`):
     - [x] Add role-based permission checks to member list views
     - [x] Update member detail views with role-based field access
     - [x] Preserve existing membership type restrictions
   - [x] **Events module** (`frontend/src/modules/events/`):
     - [x] Add role-based event management permissions
     - [x] Update event creation/editing based on roles
   - [x] **Products module** (`frontend/src/modules/products/`):
     - [x] Add role-based product management access
     - [x] Update webshop access controls
   - [x] **Parameters module** (`frontend/src/pages/ParameterManagement.tsx`):
     - [x] Restrict access to administrative roles only
     - [x] Add role validation before page load
   - [x] **Memberships module** (`frontend/src/pages/MembershipManagement.tsx`):
     - [x] Restrict to Members_CRUD_All role
     - [x] Add granular permission checks

4. **Update existing FunctionGuard component**

   - [ ] Review current `frontend/src/components/common/FunctionGuard.tsx` logic
   - [ ] Add `requiredRoles` prop to component interface
   - [ ] Implement role-based access validation
   - [ ] Preserve existing function-based access control
   - [ ] Add combined permission checking (membership AND roles)
   - [ ] Update all existing FunctionGuard usages
   - [ ] Test component with various role combinations

#### Acceptance Criteria:

- [ ] **Existing parameter-based module access is preserved and enhanced with role logic**
  - [ ] Current membership type restrictions still work
  - [ ] Parameter-based module visibility is maintained
  - [ ] Role-based enhancements are additive, not replacing
- [ ] **Existing FunctionPermissionManager is enhanced to handle role-based permissions**
  - [ ] getUserRoles() function extracts Cognito groups correctly
  - [ ] calculatePermissions() combines role permissions properly
  - [ ] Existing permission checks continue to work
  - [ ] New role-based permissions are calculated correctly
- [ ] **All existing modules respect role-based system**
  - [ ] Members module shows/hides features based on roles
  - [ ] Events module respects role-based permissions
  - [ ] Products module access is role-controlled
  - [ ] Parameters module is restricted to admin roles
  - [ ] Memberships module requires Members_CRUD_All role
- [ ] **FunctionGuard component supports role checks while preserving existing functionality**
  - [ ] requiredRoles prop works correctly
  - [ ] Existing function-based guards still work
  - [ ] Combined permission checking functions properly
- [ ] **Regular members see limited functionality (only basic member features)**
  - [ ] hdcnLeden role shows appropriate limited interface
  - [ ] Administrative features are hidden from regular members
- [ ] **Administrative roles see enhanced functionality based on their assigned roles**
  - [ ] Members_CRUD_All role sees full member management
  - [ ] Other admin roles see appropriate functionality
- [ ] **Parameters module is restricted to administrative roles only**
  - [ ] Regular members cannot access parameter management
  - [ ] Only users with admin roles can modify parameters
- [ ] **Membership management is restricted to Members_CRUD_All role**
  - [ ] Only authorized users can access membership management
  - [ ] Role validation prevents unauthorized access
- [ ] **Existing membership-based permissions are preserved and work alongside new role permissions**
  - [ ] No existing functionality is broken
  - [ ] New permissions are additive to existing ones
- [ ] **Backward compatibility maintained with existing parameter configurations**
  - [ ] Existing parameter data continues to work
  - [ ] No migration of existing parameter configurations required

---

### MVP-3: Basic Role Setup

**Priority**: Critical
**Estimated Effort**: 2-3 days

#### Tasks:

1. **Create IaC for Cognito Groups (Roles)**

   - [ ] Add Cognito User Pool Groups to SAM template:
     ```yaml
     # Implementation checklist:
     # [ ] Define CognitoUserPoolGroup resources for each role
     # [ ] Set appropriate GroupName, Description, and Precedence
     # [ ] Reference the User Pool from MVP-1 configuration
     # [ ] Use consistent naming convention for all groups
     ```
   - [ ] Define all H-DCN roles as Cognito Groups in IaC:
     - [ ] **Basic member role**: `hdcnLeden` (precedence: 100)
     - [ ] **Member management roles**:
       - [ ] `Members_CRUD_All` (precedence: 10)
       - [ ] `Members_Read_All` (precedence: 20)
       - [ ] `Members_Status_Approve` (precedence: 15)
     - [ ] **Event management roles**:
       - [ ] `Events_Read_All` (precedence: 30)
       - [ ] `Events_CRUD_All` (precedence: 25)
     - [ ] **Product management roles**:
       - [ ] `Products_Read_All` (precedence: 40)
       - [ ] `Products_CRUD_All` (precedence: 35)
     - [ ] **Communication roles**:
       - [ ] `Communication_Read_All` (precedence: 50)
       - [ ] `Communication_Export_All` (precedence: 45)
     - [ ] **System administration roles**:
       - [ ] `System_User_Management` (precedence: 5)
       - [ ] `System_Logs_Read` (precedence: 55)

2. **Document role hierarchy and permissions matrix**

   - [ ] Create role definition spreadsheet with permissions mapping
   - [ ] Document role precedence and inheritance rules
   - [ ] Define permission combinations for common organizational functions:
     - [ ] **Member Administration**: [`Members_CRUD_All`, `Events_Read_All`, `Products_Read_All`, `Communication_Read_All`, `System_User_Management`]
     - [ ] **National Chairman**: [`Members_Read_All`, `Members_Status_Approve`, `Events_Read_All`, `Products_Read_All`, `Communication_Read_All`, `System_Logs_Read`]
     - [ ] **Webmaster**: [`Members_Read_All`, `Events_CRUD_All`, `Products_CRUD_All`, `Communication_CRUD_All`, `System_CRUD_All`]
     - [ ] **Regular Members**: [`hdcnLeden`]

3. **Deploy IaC and verify group creation**

   - [ ] Deploy SAM template with Cognito Groups:
     - [ ] Run `sam build` to build updated template
     - [ ] Run `sam deploy` to deploy group resources
     - [ ] Verify all groups are created in Cognito User Pool
     - [ ] Verify group precedence is set correctly
   - [ ] Document group IDs and settings for reference
   - [ ] Verify groups appear in AWS Console with correct descriptions

4. **Set up initial role assignments (manual)**

   - [ ] **Identify and assign Member Administration users**:
     - [ ] Add users to `Members_CRUD_All` group
     - [ ] Add users to `Events_Read_All` group
     - [ ] Add users to `Products_Read_All` group
     - [ ] Add users to `Communication_Read_All` group
     - [ ] Add users to `System_User_Management` group
   - [ ] **Identify and assign National Chairman users**:
     - [ ] Add users to `Members_Read_All` group
     - [ ] Add users to `Members_Status_Approve` group
     - [ ] Add users to `Events_Read_All` group
     - [ ] Add users to `Products_Read_All` group
     - [ ] Add users to `Communication_Read_All` group
     - [ ] Add users to `System_Logs_Read` group
   - [ ] **Identify and assign Webmaster users**:
     - [ ] Add users to `Members_Read_All` group
     - [ ] Add users to `Events_CRUD_All` group
     - [ ] Add users to `Products_CRUD_All` group
     - [ ] Add users to `Communication_CRUD_All` group (create if needed)
     - [ ] Add users to `System_CRUD_All` group (create if needed)
   - [ ] **Configure default role for regular members**:
     - [ ] Set up Lambda trigger for automatic `hdcnLeden` assignment (add to IaC)
     - [ ] Test automatic role assignment for new users

5. **Test role-based authentication flow**
   - [ ] Create test users for each role type
   - [ ] Test login with Member Administration role user
   - [ ] Test login with National Chairman role user
   - [ ] Test login with Webmaster role user
   - [ ] Test login with regular member (hdcnLeden) role user
   - [ ] Verify Cognito groups appear in JWT tokens
   - [ ] Test role assignment changes take effect immediately
   - [ ] Verify role-based UI rendering works correctly

#### Acceptance Criteria:

- [ ] **IaC template includes all Cognito Groups with proper configuration**
  - [ ] SAM template defines all required CognitoUserPoolGroup resources
  - [ ] Groups have appropriate names, descriptions, and precedence
  - [ ] Template can be deployed successfully
  - [ ] Groups are created in the correct User Pool
- [ ] **Permission-based roles are created as Cognito groups**
  - [ ] All 12+ defined roles exist as Cognito groups
  - [ ] Group descriptions are clear and accurate
  - [ ] Group precedence is set correctly
- [ ] **Initial role assignments are configured for key organizational functions**
  - [ ] Member Administration users have appropriate role combinations
  - [ ] National Chairman users have correct permissions
  - [ ] Webmaster users have full system access
  - [ ] Test users exist for each role type
- [ ] **Regular member accounts automatically get `hdcnLeden` role**
  - [ ] Lambda trigger for automatic role assignment is deployed via IaC
  - [ ] New user registration assigns hdcnLeden role automatically
  - [ ] Existing members have hdcnLeden role assigned
  - [ ] Default role assignment is documented and tested
- [ ] **Role assignments can be changed dynamically through admin interface**
  - [ ] AWS Console allows role assignment changes
  - [ ] Changes take effect immediately or within 5 minutes
  - [ ] Role changes are reflected in user sessions
- [ ] **Role-based permissions are enforced in authentication flow**
  - [ ] JWT tokens contain correct cognito:groups claim
  - [ ] Frontend can extract roles from user tokens
  - [ ] Role-based UI rendering works correctly
  - [ ] Permission validation functions properly

---

### MVP-4: Role-Based Permission System

**Priority**: Critical
**Estimated Effort**: 3-4 days

#### Tasks:

1. **Extend existing Lambda handler** (`backend/handler/hdcn_cognito_admin/app.py`)

   - [ ] Review current Lambda handler structure and existing endpoints
   - [ ] Add new authentication endpoints:
     - [ ] Create `GET /auth/login` endpoint for user authentication
     - [ ] Create `GET /auth/permissions` endpoint for user permissions
     - [ ] Create `GET /auth/users/{user_id}/roles` endpoint to get user roles
     - [ ] Create `POST /auth/users/{user_id}/roles` endpoint to assign roles
     - [ ] Create `DELETE /auth/users/{user_id}/roles/{role}` endpoint to remove roles
   - [ ] Implement role-based permission calculation logic
   - [ ] Add role assignment validation (ensure user has permission to assign roles)
   - [ ] Add error handling for invalid role assignments
   - [ ] Update Lambda function permissions for Cognito group management

2. **Implement role-based permission system**

   - [ ] Create role permission mapping constants:
     ```python
     # Implementation checklist:
     # [ ] Define DEFAULT_ROLE_PERMISSIONS dictionary
     # [ ] Map hdcnLeden to basic member permissions
     # [ ] Map Members_CRUD_All to full member management permissions
     # [ ] Map administrative roles to appropriate permissions
     # [ ] Include regional permission templates
     ```
   - [ ] Implement `calculate_user_permissions()` function:
     - [ ] Extract cognito:groups from user JWT token
     - [ ] Combine permissions from all assigned roles
     - [ ] Handle role inheritance and conflicts
     - [ ] Return deduplicated permission list
   - [ ] Add role validation functions:
     - [ ] Validate role exists in Cognito
     - [ ] Check user has permission to assign specific roles
     - [ ] Validate role combinations are allowed
   - [ ] Implement permission caching for performance
   - [ ] Add comprehensive logging for role operations

3. **Implement session management and role identification**
   - [ ] **Modify existing header component** (`frontend/src/components/NavigationHeader.tsx`):
     - [ ] Replace current name display with email address
     - [ ] Make email address clickable
     - [ ] Add popup/dropdown component for account details
   - [ ] **Create account details popup component**:
     - [ ] Show user email address
     - [ ] Display assigned roles with descriptions
     - [ ] Show current permissions summary
     - [ ] Add logout button
     - [ ] Add role indicator badge for admin users
   - [ ] **Update user session management**:
     - [ ] Extract roles from Cognito JWT token on login
     - [ ] Calculate and cache user permissions
     - [ ] Update session when roles change
     - [ ] Handle role-based UI rendering
   - [ ] **Implement automatic role assignment for new members**:
     - [ ] Add hdcnLeden role to new user registration flow
     - [ ] Create Lambda trigger for post-confirmation role assignment
     - [ ] Test automatic role assignment works correctly

#### Acceptance Criteria:

- [ ] **Users get appropriate role collections based on their assigned Cognito groups**
  - [ ] JWT tokens are correctly parsed for cognito:groups
  - [ ] Role permissions are calculated accurately
  - [ ] Multiple roles combine permissions correctly
  - [ ] Permission calculation is performant (<500ms)
- [ ] **Existing header modified to display email address instead of current name**
  - [ ] Header shows user email address clearly
  - [ ] Email display is visually consistent with existing design
  - [ ] Email is truncated appropriately for long addresses
- [ ] **Email is clickable and opens popup window with roles, permissions, and logout option**
  - [ ] Click on email opens account details popup
  - [ ] Popup shows user email, roles, and permissions
  - [ ] Logout button functions correctly
  - [ ] Popup closes when clicking outside or on close button
- [ ] **UI clearly indicates assigned roles and current permissions**
  - [ ] Role badges/indicators are visible for admin users
  - [ ] Permission summary is clear and understandable
  - [ ] Visual distinction between regular and admin users
- [ ] **Permission system correctly calculates combined permissions from multiple roles**
  - [ ] Users with multiple roles get union of all permissions
  - [ ] No permission conflicts or duplicates
  - [ ] Role hierarchy is respected
  - [ ] Permission changes reflect immediately in UI

---

### MVP-5: Field-Level Permissions Implementation

**Priority**: High
**Estimated Effort**: 2-3 days

#### Tasks:

1. **Update Members table handlers**

   - [ ] Review current `backend/handler/update_member/app.py` implementation
   - [ ] Add role-based permission validation to update operations:
     - [ ] Extract user roles from JWT token in request headers
     - [ ] Validate user has permission to modify requested fields
     - [ ] Return appropriate error messages for unauthorized field updates
   - [ ] Implement field-level permission checks:
     - [ ] Create field validation function based on user roles
     - [ ] Add logging for field-level permission denials
     - [ ] Test permission validation with different role combinations

2. **Define field categories based on DynamoDB Members table**

   - [ ] Document current Members table schema and field types
   - [ ] Create field category constants:
     ```python
     # Implementation checklist:
     # [ ] Define PERSONAL_FIELDS list with all personal data fields
     # [ ] Define MOTORCYCLE_FIELDS list with motorcycle-related fields
     # [ ] Define ADMINISTRATIVE_FIELDS list with admin-only fields
     # [ ] Validate field lists against actual DynamoDB table schema
     ```
   - [ ] **Personal fields** (editable by members for own record):
     - [ ] `voornaam`, `achternaam`, `tussenvoegsel`, `initialen`
     - [ ] `telefoon`, `straat`, `postcode`, `woonplaats`, `land`
     - [ ] `email`, `nieuwsbrief`, `geboortedatum`, `geslacht`
   - [ ] **Motorcycle fields** (editable by members for own record):
     - [ ] `bouwjaar`, `motormerk`, `motortype`, `kenteken`, `wiewatwaar`
   - [ ] **Administrative fields** (admin-only):
     - [ ] `member_id`, `lidnummer`, `lidmaatschap`, `status`, `tijdstempel`
     - [ ] `aanmeldingsjaar`, `regio`, `clubblad`, `bankrekeningnummer`
     - [ ] `datum_ondertekening`, `created_at`, `updated_at`

3. **Implement validation logic**

   - [ ] **hdcnLeden role validation**:
     - [ ] Can only edit personal + motorcycle fields for own record
     - [ ] Cannot edit other members' records
     - [ ] Cannot modify administrative fields
     - [ ] Add validation for record ownership (user can only edit own data)
   - [ ] **Members_CRUD_All role validation**:
     - [ ] Can edit all fields including administrative data
     - [ ] Can edit any member's record
     - [ ] Can modify status field
     - [ ] Add audit logging for administrative field changes
   - [ ] **Status field special handling**:
     - [ ] Only Members_CRUD_All role can modify status field
     - [ ] Add specific validation and logging for status changes
     - [ ] Test status change permissions thoroughly

4. **Add membership type-specific field restrictions**
   - [ ] **Review existing system behavior**:
     - [ ] Audit current field restrictions by membership type
     - [ ] Document discovered membership type variations
     - [ ] Interview stakeholders about membership type differences
   - [ ] **Implement discovered restrictions**:
     - [ ] Add membership type checks to field validation
     - [ ] Create membership type-specific field permission matrix
     - [ ] Test restrictions with different membership types
   - [ ] **Document variations for future reference**:
     - [ ] Create field permission matrix by membership type
     - [ ] Document business rules for each membership type
     - [ ] Add comments in code explaining membership type logic

#### Acceptance Criteria:

- [ ] **Regular members can edit their personal and motorcycle information only**
  - [ ] hdcnLeden role users can edit personal fields for own record
  - [ ] hdcnLeden role users can edit motorcycle fields for own record
  - [ ] hdcnLeden role users cannot edit other members' records
  - [ ] Field validation prevents unauthorized edits
- [ ] **Regular members cannot edit administrative data**
  - [ ] Administrative fields are read-only for hdcnLeden role
  - [ ] Attempts to edit admin fields return appropriate error messages
  - [ ] UI shows administrative fields as disabled/read-only
- [ ] **Status changes are restricted to Members_CRUD_All role only**
  - [ ] Only Members_CRUD_All role can modify status field
  - [ ] Status change attempts by other roles are blocked
  - [ ] Status changes are logged with user and timestamp
- [ ] **Field permissions are enforced at API level with proper error messages**
  - [ ] Backend validates field permissions before database updates
  - [ ] Clear error messages explain permission denials
  - [ ] HTTP status codes are appropriate (403 for forbidden)
- [ ] **Membership type variations are documented and implemented as discovered**
  - [ ] Field permission matrix exists for different membership types
  - [ ] Business rules are documented and implemented
  - [ ] Code includes comments explaining membership type logic
  - [ ] Stakeholder feedback is incorporated into field restrictions

---

### MVP-6: Frontend Integration for Passwordless Authentication

**Priority**: High
**Estimated Effort**: 4-5 days

#### Tasks:

1. **Update authentication flow for passwordless**

   - [ ] **Review and update Amplify configuration**:
     - [ ] Update `frontend/src/aws-exports.js` with new Cognito User Pool settings
     - [ ] Configure Amplify for passwordless authentication support
     - [ ] Update authentication flow to use `ALLOW_USER_AUTH` flow type
     - [ ] Test Amplify configuration with new User Pool settings
   - [ ] **Implement passkey registration flow**:
     - [ ] Create `PasskeySetup` component for guiding users through WebAuthn setup
     - [ ] Add passkey registration to user onboarding flow
     - [ ] Implement device capability detection for WebAuthn support
     - [ ] Add fallback messaging for unsupported browsers/devices
   - [ ] **Update login components for passwordless**:
     - [ ] Modify existing login component to support passkey authentication
     - [ ] Remove password input fields from login forms
     - [ ] Add passkey authentication button/interface
     - [ ] Implement email-based fallback authentication
   - [ ] **Handle email recovery flow**:
     - [ ] Create email recovery component for account recovery
     - [ ] Implement email verification flow without passwords
     - [ ] Guide users to new passkey setup after email recovery
     - [ ] Test complete email recovery to passkey setup flow

   ```typescript
   // Implementation checklist:
   // [ ] authenticateWithPasskey() function uses ALLOW_USER_AUTH flow
   // [ ] setupPasskey() function guides WebAuthn registration
   // [ ] emailRecovery() function handles passwordless recovery
   // [ ] Device capability detection for WebAuthn support
   ```

2. **Enhance existing user data handling**

   - [ ] **Extend existing user object with role detection**:
     - [ ] Add `getUserRoles()` utility function to extract Cognito groups
     - [ ] Add `calculatePermissions()` function for role-based permissions
     - [ ] Update existing user context/state to include roles and permissions
     - [ ] Test role extraction from JWT tokens
   - [ ] **Enhance existing FunctionPermissionManager**:
     - [ ] Review current `frontend/src/utils/functionPermissions.ts`
     - [ ] Extend `FunctionPermissionManager.create()` with role logic
     - [ ] Add role permission mapping constants (ROLE_PERMISSIONS)
     - [ ] Preserve existing membership-based permission logic
     - [ ] Test permission calculation with multiple roles
   - [ ] **Role-based permission calculation utilities**:
     ```typescript
     // Implementation checklist:
     // [ ] getUserRoles() extracts cognito:groups from user token
     // [ ] calculatePermissions() combines permissions from all roles
     // [ ] ROLE_PERMISSIONS constant maps roles to permissions
     // [ ] Existing membership permissions are preserved
     // [ ] New role permissions are additive to existing permissions
     ```

3. **Enhance existing member profile components**

   - [ ] **Update member profile forms**:
     - [ ] Review existing member profile components
     - [ ] Add role-based field visibility logic
     - [ ] Preserve existing membership type-based restrictions
     - [ ] Update form validation to include role-based rules
   - [ ] **Extend existing FunctionGuard component**:
     - [ ] Review current `frontend/src/components/common/FunctionGuard.tsx`
     - [ ] Add `requiredRoles` prop to component interface
     - [ ] Implement role-based access validation
     - [ ] Preserve existing function-based access control
     - [ ] Test component with various role combinations
   - [ ] **Visual indicators for field permissions**:
     - [ ] Add visual indicators for read-only fields (administrative data)
     - [ ] Update form styling to show disabled/read-only states
     - [ ] Add tooltips explaining why fields are read-only
     - [ ] Test visual indicators across different roles

4. **Update header and UI components for role identification**
   - [ ] **Modify NavigationHeader component**:
     - [ ] Update `frontend/src/components/NavigationHeader.tsx` (or equivalent)
     - [ ] Replace current name display with email address
     - [ ] Make email address clickable
     - [ ] Ensure email display is responsive and truncates properly
   - [ ] **Create account details popup component**:
     - [ ] Create new `AccountDetailsPopup` component
     - [ ] Show user email address clearly
     - [ ] Display assigned roles with descriptions
     - [ ] Show current permissions summary
     - [ ] Add logout button functionality
     - [ ] Add role indicator badge for administrative roles
   - [ ] **Implement popup behavior**:
     - [ ] Click on email opens account details popup
     - [ ] Click outside popup closes it
     - [ ] ESC key closes popup
     - [ ] Popup positioning works on mobile and desktop
   - [ ] **Test UI components**:
     - [ ] Test header display with long email addresses
     - [ ] Test popup functionality across different screen sizes
     - [ ] Test role badges for different user types
     - [ ] Verify logout functionality works correctly

#### Acceptance Criteria:

- [ ] **Existing Amplify authentication flow is updated for passwordless authentication**
  - [ ] Amplify configuration supports passwordless authentication
  - [ ] ALLOW_USER_AUTH flow is properly configured
  - [ ] Authentication works without password requirements
  - [ ] Email verification flow is functional
- [ ] **Existing user object is enhanced with role detection and permission calculation**
  - [ ] getUserRoles() function extracts Cognito groups correctly
  - [ ] calculatePermissions() combines role permissions properly
  - [ ] User context includes roles and permissions
  - [ ] Role changes are reflected in user session
- [ ] **Current FunctionPermissionManager is extended to handle role-based permissions**
  - [ ] Role-based permission logic is integrated
  - [ ] Existing permission checks continue to work
  - [ ] New role-based permissions are calculated correctly
  - [ ] Multiple roles combine permissions properly
- [ ] **Header displays current email address as clickable element**
  - [ ] Email address is clearly visible in header
  - [ ] Email is clickable and responsive
  - [ ] Long email addresses are handled gracefully
- [ ] **Clicking email opens popup window with roles, permissions, and logout option**
  - [ ] Popup opens when email is clicked
  - [ ] Popup shows user email, roles, and permissions
  - [ ] Logout button functions correctly
  - [ ] Popup closes appropriately (click outside, ESC key)
- [ ] **Subtle visual indicator (badge) distinguishes administrative roles**
  - [ ] Administrative users have visible role indicators
  - [ ] Regular members don't have admin indicators
  - [ ] Role badges are clear but not intrusive
- [ ] **Form fields are enabled/disabled based on BOTH role permissions AND existing membership type restrictions**
  - [ ] Role-based field restrictions work correctly
  - [ ] Existing membership restrictions are preserved
  - [ ] Combined permission logic functions properly
  - [ ] Visual indicators show field permission status
- [ ] **Passkey registration and authentication work across devices**
  - [ ] Passkey setup works on desktop browsers
  - [ ] Passkey setup works on mobile devices
  - [ ] Cross-device authentication is functional
  - [ ] Fallback options work when WebAuthn is unavailable

---

### MVP-7: Existing Member Migration Strategy

**Priority**: High
**Estimated Effort**: 3-4 days

#### Tasks:

1. **Create IaC for migration Lambda functions**

   - [ ] Add migration Lambda function to SAM template:
     ```yaml
     # Implementation checklist:
     # [ ] Define MigrationFunction resource in SAM template
     # [ ] Configure DynamoDB permissions for Members table access
     # [ ] Configure Cognito permissions for user creation
     # [ ] Set up SES permissions for email sending
     # [ ] Add environment variables for configuration
     ```
   - [ ] Create Lambda function for bulk member migration:
     - [ ] Create `backend/handler/migrate_members/app.py`
     - [ ] Implement bulk Cognito user creation without passwords
     - [ ] Add error handling and retry logic
     - [ ] Create migration progress tracking
   - [ ] Deploy migration infrastructure:
     - [ ] Add migration function to SAM template
     - [ ] Deploy with `sam build && sam deploy`
     - [ ] Verify Lambda function is created with correct permissions

2. **Implement passwordless migration workflow**

   - [ ] **Create bulk migration script**:
     - [ ] Query all members from DynamoDB Members table
     - [ ] Create Cognito accounts for each member using email as username
     - [ ] Set accounts to "email verification required" state (no passwords)
     - [ ] Handle rate limiting and batch processing
     - [ ] Log migration progress and results
   - [ ] **Configure email verification state**:
     - [ ] Set migrated accounts to require email verification
     - [ ] Configure custom email templates for migration
     - [ ] Test email verification flow for migrated accounts
   - [ ] **Create welcome email campaign**:
     - [ ] Design migration instruction email template
     - [ ] Include step-by-step passkey setup instructions
     - [ ] Add support contact information
     - [ ] Test email delivery and formatting
   - [ ] **Implement migration tracking**:
     - [ ] Create migration status tracking in DynamoDB
     - [ ] Generate migration progress reports
     - [ ] Track successful vs failed migrations
     - [ ] Create dashboard for monitoring migration progress

3. **Handle migration edge cases**

   - [ ] **Duplicate email addresses**:
     - [ ] Identify duplicate email addresses in Members table
     - [ ] Create unique identifiers for duplicate emails
     - [ ] Generate exception reports for manual resolution
     - [ ] Implement fallback email assignment strategy
   - [ ] **Invalid email addresses**:
     - [ ] Validate email addresses before migration
     - [ ] Generate reports for invalid emails
     - [ ] Create manual cleanup process
     - [ ] Notify administrators of invalid email issues
   - [ ] **Bounced emails**:
     - [ ] Set up SES bounce and complaint handling
     - [ ] Track failed email deliveries
     - [ ] Implement retry logic for failed emails
     - [ ] Create reports for bounced emails
   - [ ] **Member support process**:
     - [ ] Create migration FAQ document
     - [ ] Set up support email for migration questions
     - [ ] Train support staff on migration process
     - [ ] Create troubleshooting guide

4. **Implement guided migration flow**

   - [ ] **Email verification flow**:
     - [ ] Direct migrated members to email verification page
     - [ ] Create custom verification page for migrated users
     - [ ] Handle verification success and failure cases
     - [ ] Track verification completion rates
   - [ ] **Passkey setup guidance**:
     - [ ] Guide verified members through mandatory passkey registration
     - [ ] Create step-by-step passkey setup tutorial
     - [ ] Handle passkey setup failures gracefully
     - [ ] Provide fallback options for unsupported devices
   - [ ] **Automatic role assignment**:
     - [ ] Analyze existing member data to determine appropriate roles
     - [ ] Automatically assign roles based on membership type and history
     - [ ] Create role assignment rules and logic
     - [ ] Test role assignment accuracy
   - [ ] **Migration completion tracking**:
     - [ ] Confirm successful migration for each member
     - [ ] Send completion confirmation emails
     - [ ] Provide next steps and system access instructions
     - [ ] Generate migration completion reports

#### Acceptance Criteria:

- [ ] **IaC template includes migration Lambda function with proper permissions**
  - [ ] Migration Lambda function is defined in SAM template
  - [ ] Function has DynamoDB, Cognito, and SES permissions
  - [ ] Template deploys successfully
  - [ ] Function can be invoked for migration
- [ ] **Bulk migration creates Cognito accounts for all existing members without passwords**
  - [ ] All members in DynamoDB have corresponding Cognito accounts
  - [ ] Accounts are created without passwords
  - [ ] Email verification is required for all migrated accounts
  - [ ] Migration process handles large member datasets
- [ ] **Migrated members receive clear instructions for email verification and passkey setup**
  - [ ] Welcome emails are sent to all migrated members
  - [ ] Email instructions are clear and actionable
  - [ ] Support contact information is provided
  - [ ] Email delivery is tracked and monitored
- [ ] **Migration process handles duplicate and invalid email addresses gracefully**
  - [ ] Duplicate emails are identified and handled
  - [ ] Invalid emails are reported for manual resolution
  - [ ] Exception reports are generated for administrators
  - [ ] Fallback processes are in place
- [ ] **Migrated members are guided through email verification and passkey setup**
  - [ ] Email verification flow works for migrated users
  - [ ] Passkey setup is mandatory after verification
  - [ ] Guidance is provided throughout the process
  - [ ] Completion rates are tracked and monitored
- [ ] **Role assignments are automatically applied based on existing member data**
  - [ ] Roles are assigned based on membership type and history
  - [ ] Assignment logic is accurate and tested
  - [ ] Role assignments are verified post-migration
- [ ] **Migration progress is tracked and exceptions are reported for manual resolution**
  - [ ] Migration progress is monitored in real-time
  - [ ] Exception reports are generated for failed migrations
  - [ ] Manual resolution processes are documented
  - [ ] Migration completion is verified and reported

---

### MVP-8: New Member Application Process

**Priority**: High
**Estimated Effort**: 2-3 days

#### Tasks:

1. **Implement routing logic for authenticated users without membership records**

   - [ ] **Extend existing authentication flow**:
     - [ ] Review current authentication routing logic
     - [ ] Add membership record check after Cognito authentication
     - [ ] Create routing decision function based on user status
     - [ ] Test routing logic with different user scenarios
   - [ ] **Create routing decision logic**:
     - [ ] **Cognito authenticated + Member record exists** → Route to existing member profile/dashboard
     - [ ] **Cognito authenticated + No member record** → Route to new member application form
     - [ ] **Cognito authenticated + Application pending** → Route to application status page
     - [ ] **Not authenticated** → Route to login/registration page
   - [ ] **Implement routing components**:
     - [ ] Create `AuthenticationRouter` component for routing decisions
     - [ ] Add loading states during membership record lookup
     - [ ] Handle routing errors gracefully
     - [ ] Test routing with various user states

2. **Implement new member application workflow**

   - [ ] **Extend existing MembershipForm component**:
     - [ ] Review current `MembershipForm` component structure
     - [ ] Add `mode` prop: `"new_application" | "existing_member"`
     - [ ] Modify form fields and validation for new applications
     - [ ] Update form title and instructions for new applicants
     - [ ] Test form behavior in both modes
   - [ ] **Implement application submission**:
     - [ ] Store application as Member record with `status: 'new_applicant'`
     - [ ] Validate all required fields before submission
     - [ ] Generate unique application ID for tracking
     - [ ] Add timestamp and applicant information
     - [ ] Test application storage and retrieval
   - [ ] **Create confirmation and notification system**:
     - [ ] Display confirmation message: "We will contact you within one week regarding your application"
     - [ ] Send confirmation email to applicant with application details
     - [ ] Send notification emails to H-DCN administrators with applicant details
     - [ ] Include application data and next steps in admin notifications
     - [ ] Test email delivery and formatting
   - [ ] **Implement duplicate application prevention**:
     - [ ] Check if user already has pending application
     - [ ] Display appropriate message for users with existing applications
     - [ ] Allow application updates if needed
     - [ ] Handle edge cases (withdrawn applications, etc.)

3. **Integration with passwordless authentication**

   - [ ] **Email-only registration flow**:
     - [ ] Ensure new users can register with email only
     - [ ] Remove password requirements from registration
     - [ ] Test registration flow without passwords
     - [ ] Verify email verification is mandatory
   - [ ] **Passkey setup integration**:
     - [ ] Guide new users through passkey registration after email verification
     - [ ] Make passkey setup mandatory before application access
     - [ ] Provide clear instructions for passkey setup
     - [ ] Handle passkey setup failures gracefully
   - [ ] **Application flow integration**:
     - [ ] Ensure authenticated users without membership records access application
     - [ ] Verify application is only accessible to authenticated users
     - [ ] Test complete flow: registration → verification → passkey → application
   - [ ] **Role assignment for new applicants**:
     - [ ] Automatically assign basic roles to new applicants
     - [ ] Ensure applicants have minimal required permissions
     - [ ] Update roles after application approval
     - [ ] Test role assignment and permission validation

4. **Create application status and management**
   - [ ] **Application status page**:
     - [ ] Create page showing application status for pending applicants
     - [ ] Display application submission date and current status
     - [ ] Show expected timeline and next steps
     - [ ] Provide contact information for questions
   - [ ] **Admin application management** (basic):
     - [ ] Create simple interface for administrators to view applications
     - [ ] Allow status updates (pending, approved, rejected)
     - [ ] Send status update notifications to applicants
     - [ ] Track application processing timeline

#### Acceptance Criteria:

- [ ] **Authenticated users without membership records are routed to new member application**
  - [ ] Routing logic correctly identifies users without membership records
  - [ ] Users are directed to appropriate application form
  - [ ] Routing handles edge cases and errors gracefully
  - [ ] Loading states are shown during membership record lookup
- [ ] **New applications are stored with `status: 'new_applicant'`**
  - [ ] Applications are saved to DynamoDB Members table
  - [ ] Status field is correctly set to 'new_applicant'
  - [ ] All required application data is captured
  - [ ] Application IDs are unique and trackable
- [ ] **Applicants receive confirmation message after submission**
  - [ ] Confirmation message is displayed immediately after submission
  - [ ] Message includes expected timeline and next steps
  - [ ] Confirmation email is sent to applicant
  - [ ] Email includes application details and reference number
- [ ] **Administrators receive email notifications for new applications**
  - [ ] Admin notification emails are sent automatically
  - [ ] Emails include complete applicant details and application data
  - [ ] Multiple administrators can receive notifications
  - [ ] Email delivery is reliable and tracked
- [ ] **Users cannot submit multiple applications (duplicate prevention)**
  - [ ] System checks for existing applications before allowing submission
  - [ ] Users with pending applications see appropriate status message
  - [ ] Duplicate submission attempts are blocked
  - [ ] Edge cases (withdrawn applications) are handled
- [ ] **New users complete passwordless registration before application**
  - [ ] Registration requires email only (no passwords)
  - [ ] Email verification is mandatory
  - [ ] Passkey setup is required after verification
  - [ ] Complete authentication flow works before application access

---

## Full Implementation (Phase 2)

### FULL-1: Enhanced Security and MFA

**Priority**: High
**Estimated Effort**: 3-4 days

#### Tasks:

1. **Implement MFA for administrative roles (users with @h-dcn.nl email addresses)**

   - [ ] **Configure Cognito MFA for administrative users**:
     - [ ] Set up MFA configuration in Cognito User Pool
     - [ ] Configure MFA to be required for users with @h-dcn.nl email addresses
     - [ ] Set up adaptive MFA triggers based on suspicious activity
     - [ ] Test MFA configuration with test administrative accounts
   - [ ] **Implement role-based MFA policy**:
     - [ ] Administrative roles require MFA when suspicious activity is detected
     - [ ] Regular members (non-@h-dcn.nl) do not require MFA for streamlined experience
     - [ ] Create MFA policy logic based on email domain and roles
     - [ ] Test MFA policy with different user types
   - [ ] **Configure MFA methods**:
     - [ ] Support SMS MFA for administrative users
     - [ ] Support email MFA as fallback option
     - [ ] Support authenticator app (TOTP) for enhanced security
     - [ ] Test all MFA methods with administrative accounts

2. **Implement suspicious activity detection**

   - **Login pattern analysis**: Detect unusual login locations, times, devices
   - **Failed attempt monitoring**: Track and respond to multiple faittempts
   - **Progressive security measures**: Temporary lockout, email notificationalerts
   - **Security event logging**: Comprehensive logging of all security-related events

3. **Enhanced audit and compliance**
   - **Authentication attempt logging**: Log all login attempts with timestamps and user identification
   - **Passkey usage tracking**: Monitor passkey authentication events
   - **Email recovery logging**: Track email-based account recovery events
   - **Administrative action auditing**: Log all administrative actions with user and role context

#### Acceptance Criteria:

- MFA is mandatory for administrative roles when suspicious activity is detected
- Regular members do not require MFA for streamlined experience
- Suspicious activity detection triggers appropriate security measures
- All authentication and security events are comprehensively logged
- Progressive account protection measures are implemented

---

### FULL-2: Performance and Monitoring

**Priority**: Medium
**Estimated Effort**: 3-4 days

#### Tasks:

1. **Create Member Index Table for fast filtering and exports**

   - **Design denormalized table**: Create `MemberIndex` table with key searchable fields
   - **Key fields to include**:
     - `member_id` (UUID - primary key)
     - `email` (for quick user lookup)
     - `voornaam`, `achternaam` (name searching)
     - `lidnummer` (membership number)
     - `regio` (region filtering)
     - `lidmaatschap` (membership type)
     - `status` (active, inactive, new_applicant)
     - `created_at`, `updated_at` (date filtering)
     - `motormerk` (motorcycle brand filtering)
   - **Sync mechanism**: Keep index table updated when main Members table changes
   - **Use for exports**: Fast filtering without scanning full Members table

2. **Add performance monitoring**

   - **Authentication response time tracking**: Monitor login performance
   - **Permission calculation optimization**: Optimize role-based permission calculations
   - **Database query optimization**: Use Member Index table for fast queries
   - **Passkey authentication monitoring**: Track WebAuthn performance

3. **Implement caching strategies**

   - **Permission result caching**: Cache calculated permissions for user sessions
   - **Parameter data caching**: Cache parameter system data
   - **Session optimization**: Optimize user session management
   - **Member Index query caching**: Cache frequently accessed member data

4. **Add comprehensive logging and monitoring**
   - **Authentication attempts**: Log all authentication events
   - **Permission checks**: Monitor permission validation performance
   - **Administrative actions**: Log all admin actions with context
   - **Export operations**: Log export activities with filters and performance metrics

#### Acceptance Criteria:

- **Member Index table enables fast filtering** for exports and reports
- **Export performance improved** using denormalized index table
- **Quick user lookup** from email or membership number
- System meets performance requirements (<2s login)
- Comprehensive monitoring is in place
- All security and administrative events are logged
- Caching strategies improve system performance

---

### FULL-3: Advanced Export System

**Priority**: Medium
**Estimated Effort**: 4-5 days

#### Tasks:

1. **Implement comprehensive export functionality**

   - **Multiple format support**: CSV, XLSX, PDF, TXT formats
   - **Custom field selection**: Allow administrators to choose specific data fields
   - **Advanced filtering**: Region, membership type, payment status, roles, date ranges
   - **Export templates**: Predefined templates for common use cases

2. **Add export templates and use cases**

   - **Mailing lists**: Email-only exports for communications
   - **Address labels**: Physical address formatting for postal services
   - **Membership statistics**: Aggregated data and analytics reports
   - **Anniversary recognition**: Members by years of membership (5, 10, 25 years)
   - **Administrative reports**: Comprehensive member data for admin use

3. **Implement role-based export permissions**

   - **Export access control**: Role-based restrictions on export functionality
   - **Regional export restrictions**: Regional roles can only export their region data
   - **Audit logging**: Log all export activities with user, timestamp, filters, and format
   - **Privacy controls**: Ensure only authorized users can export member data

4. **Performance optimization for large exports**
   - **Streaming exports**: Handle large datasets without memory issues
   - **Progress indicators**: Show export progress for large datasets
   - **Background processing**: Process large exports asynchronously
   - **Export scheduling**: Support for recurring administrative exports

#### Acceptance Criteria:

- Users can export data in multiple formats (CSV, XLSX, PDF, TXT)
- Export access is properly restricted by role and region
- All exports are logged for audit purposes
- Export performance is optimized for large datasets
- Predefined templates are available for common use cases
- Privacy controls ensure data protection compliance

---

### FULL-4: Integration and API Features

**Priority**: Low
**Estimated Effort**: 3-4 days

#### Tasks:

1. **Implement API endpoints for external integration**

   - **RESTful authentication API**: Provide API access to authentication functions
   - **Role management API**: API endpoints for role queries and assignments
   - **Export API with OAuth2**: Secure API access for data exports
   - **Member data API**: Controlled access to member information

2. **Add webhook support for real-time notifications**

   - **Member data change notifications**: Notify external systems of member updates
   - **Role assignment notifications**: Alert external systems of role changes
   - **Authentication event webhooks**: Real-time authentication event notifications
   - **System event webhooks**: General system event notifications

3. **External system integration**
   - **Google Workspace integration**: Connect with Google email and drive systems
   - **Email marketing platform integration**: Sync member data with marketing tools
   - **Payment system integration**: Connect with payment processing systems
   - **Reporting tool integration**: Export data to external reporting platforms

#### Acceptance Criteria:

- APIs are available for external integration with proper authentication
- Webhooks notify external systems of relevant changes
- Integration with key external systems works (Google, email marketing, payments)
- API rate limiting and security measures are implemented
- External integrations are properly documented and tested

---

### FULL-5: GDPR Compliance and Data Privacy

**Priority**: Medium
**Estimated Effort**: 2-3 days

#### Tasks:

1. **Implement GDPR compliance features**

   - **Right to be Forgotten**: Allow members to request complete data deletion
   - **Data portability**: Enable members to download their complete personal data
   - **Consent management**: Granular opt-in/opt-out controls for communications
   - **Data retention policies**: Automatic removal of inactive member data after 7 years

2. **Privacy controls and audit trails**
   - **Personal data access logging**: Log all administrator access to personal data
   - **Purpose justification**: Require justification for personal data access
   - **Automatic audit trail generation**: Generate compliance reports automatically
   - **Data processing transparency**: Clear documentation of data processing activities

#### Acceptance Criteria:

- Members can request and receive complete data deletion within 30 days
- Members can download their complete personal data in machine-readable formats
- Granular consent management is available for different communication types
- Data retention policies automatically remove old data as required
- All personal data access is logged with purpose justification
- System meets GDPR compliance requirements and passes audit readiness checks

---

## Implementation Strategy

### MVP First Approach

1. **Start with MVP-1 through MVP-8** (estimated 20-26 days)
2. **Test thoroughly** with real users and passwordless authentication
3. **Gather feedback** on passwordless experience and role-based permissions
4. **Deploy MVP** to production for immediate value

### Full Implementation

1. **Implement FULL-1 through FULL-5** (estimated 15-20 days)
2. **Comprehensive testing** including security and performance testing
3. **Security audit** focusing on passwordless authentication and role-based access
4. **Production deployment** with full monitoring and compliance features

### Risk Mitigation

- **MVP provides immediate value** with passwordless authentication and basic roles
- **Incremental deployment** reduces risk of major authentication changes
- **Rollback capability** at each phase with fallback authentication methods
- **User feedback integration** throughout passwordless adoption process
- **Gradual migration** allows users to adapt to passwordless authentication
