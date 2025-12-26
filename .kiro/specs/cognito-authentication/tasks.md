# H-DCN Cognito Authentication - Implementation Tasks

## Overview

This document outlines the implementation tasks for the H-DCN Cognito Authentication system, divided into MVP (Minimum Viable Product) and Full Implementation phases.

**MVP Goal**: Basic passwordless authentication with essential role-based permissions
**Full Goal**: Complete system with all advanced features and optimizations

## Current Implementation Status

Based on code analysis, significant progress has been made:

### ✅ **COMPLETED INFRASTRUCTURE**

- **Cognito User Pool**: Fully configured for passwordless authentication
- **Cognito Groups**: All H-DCN roles created as Cognito groups
- **Lambda Functions**: Custom message and post-confirmation triggers deployed
- **Authentication API**: Comprehensive auth endpoints implemented
- **Role Management**: Full role assignment and validation system

### ✅ **COMPLETED BACKEND**

- **Passwordless Auth**: Complete signup, passkey, and recovery flows
- **Role-Based Permissions**: Full permission calculation system
- **API Endpoints**: All auth and role management endpoints
- **Field-Level Security**: Role validation and business rules

### ✅ **COMPLETED FRONTEND**

- **Auth Components**: Passkey setup, email recovery, cross-device auth
- **Permission System**: Role extraction and permission calculation
- **Function Guards**: Enhanced with role-based access control
- **User Management**: Role detection and session handling

## Remaining Tasks (MVP Completion)

### MVP-4: UI Integration for Role Display

**Priority**: High
**Estimated Effort**: 1-2 days

#### Tasks:

1. **Update Navigation Header for Role Display**
   - [x] **Modify existing header component**:
     - [x] Replace current name display with email address
     - [x] Make email address clickable
     - [x] Add responsive email truncation for long addresses
   - [x] **Create account details popup component**:
     - [x] Show user email address
     - [x] Display assigned roles with descriptions
     - [x] Show current permissions summary
     - [x] Add logout button
     - [x] Add role indicator badge for admin users
   - [x] **Implement popup behavior**:
     - [x] Click on email opens account details popup
     - [x] Click outside popup closes it
     - [x] ESC key closes popup
     - [x] Popup positioning works on mobile and desktop

#### Acceptance Criteria:

- [x] **Header displays current email address as clickable element**
- [x] **Clicking email opens popup window with roles, permissions, and logout option**
- [x] **UI clearly indicates assigned roles and current permissions**
- [x] **Subtle visual indicator (badge) distinguishes administrative roles**

---

### MVP-5: Field-Level Permissions Implementation

**Priority**: High
**Estimated Effort**: 2-3 days

#### Tasks:

1. **Update Members table handlers**

   - [x] Review current `backend/handler/update_member/app.py` implementation
   - [x] Add role-based permission validation to update operations:
     - [x] Extract user roles from JWT token in request headers
     - [x] Validate user has permission to modify requested fields
     - [x] Return appropriate error messages for unauthorized field updates
   - [x] Implement field-level permission checks:
     - [x] Create field validation function based on user roles
     - [x] Add logging for field-level permission denials
     - [x] Test permission validation with different role combinations

2. **Define field categories based on DynamoDB Members table**

   - [x] Document current Members table schema and field types
   - [x] Create field category constants:
     ```python
     # Implementation completed - see backend/handler/hdcn_cognito_admin/role_permissions.py
     # [x] Define PERSONAL_FIELDS list with all personal data fields
     # [x] Define MOTORCYCLE_FIELDS list with motorcycle-related fields
     # [x] Define ADMINISTRATIVE_FIELDS list with admin-only fields
     # [x] Validate field lists against actual DynamoDB table schema
     ```
   - [x] **Personal fields** (editable by members for own record):
     - [x] `voornaam`, `achternaam`, `tussenvoegsel`, `initialen`
     - [x] `telefoon`, `straat`, `postcode`, `woonplaats`, `land`
     - [x] `email`, `nieuwsbrief`, `geboortedatum`, `geslacht`, `wiewatwaar`
   - [x] **Motorcycle fields** (editable by members for own record):
     - [x] `bouwjaar`, `motormerk`, `motortype`, `kenteken`
   - [x] **Administrative fields** (admin-only):
     - [x] `member_id`, `lidnummer`, `lidmaatschap`, `status`, `tijdstempel`
     - [x] `aanmeldingsjaar`, `regio`, `clubblad`, `bankrekeningnummer`
     - [x] `datum_ondertekening`, `created_at`, `updated_at`

3. **Implement validation logic**
   - [x] **hdcnLeden role validation**:
     - [x] Can only edit personal + motorcycle fields for own record
     - [x] Cannot edit other members' records
     - [x] Cannot modify administrative fields
     - [x] Add validation for record ownership (user can only edit own data)
   - [x] **Members_CRUD_All role validation**:
     - [x] Can edit all fields including administrative data
     - [x] Can edit any member's record
     - [x] Can modify status field
     - [x] Add audit logging for administrative field changes
   - [x] **Status field special handling**:
     - [x] Only Members_CRUD_All role can modify status field
     - [x] Add specific validation and logging for status changes
     - [x] Test status change permissions thoroughly

#### Acceptance Criteria:

- [x] **Regular members can edit their personal and motorcycle information only**
- [x] **Regular members cannot edit administrative data**
- [x] **Status changes are restricted to Members_CRUD_All role only**
- [x] **Field permissions are enforced at API level with proper error messages**

---

### MVP-6: Webshop API Security Implementation

**Priority**: CRITICAL - Security Vulnerability
**Estimated Effort**: 2-3 days

#### Tasks:

1. **Add JWT authentication to webshop API endpoints**

   - [x] **Update cart handlers with authentication**:
     - [x] Add JWT token extraction to `backend/handler/create_cart/app.py`
     - [x] Add JWT token extraction to `backend/handler/get_cart/app.py`
     - [x] Add JWT token extraction to `backend/handler/update_cart_items/app.py`
     - [x] Add JWT token extraction to `backend/handler/clear_cart/app.py`
     - [x] Import and use `extract_user_roles_from_jwt` function from update_member handler
   - [x] **Update order handlers with authentication**:
     - [x] Add JWT token extraction to `backend/handler/create_order/app.py`
     - [x] Add JWT token extraction to `backend/handler/get_orders/app.py`
     - [x] Add JWT token extraction to `backend/handler/get_order_byid/app.py`
     - [x] Add JWT token extraction to `backend/handler/get_customer_orders/app.py`
   - [x] **Update payment handlers with authentication**:
     - [x] Add JWT token extraction to `backend/handler/create_payment/app.py`
     - [x] Add JWT token extraction to `backend/handler/get_payments/app.py`
     - [x] Add JWT token extraction to `backend/handler/get_payment_byid/app.py`
     - [x] Add JWT token extraction to `backend/handler/get_member_payments/app.py`

2. **Implement role-based permission validation**

   - [x] **Add webshop access validation**:
     - [x] Validate `webshop:access` permission for all webshop endpoints
     - [x] Return 403 Forbidden for users without hdcnLeden role
     - [x] Add proper error messages for unauthorized access
     - [x] Log unauthorized access attempts for security monitoring
   - [x] **Add cart ownership validation**:
     - [x] Link carts to user email/member_id during creation
     - [x] Validate cart ownership before get/update/clear operations
     - [x] Prevent users from accessing other users' carts
     - [x] Add audit logging for cart access attempts

3. **Implement order and payment security**
   - [x] **Order creation security**:
     - [x] Validate user identity before creating orders
     - [x] Link orders to authenticated user's member_id
     - [x] Validate cart ownership before order creation
     - [x] Add order creation audit logging
   - [x] **Payment security**:
     - [x] Validate user identity before processing payments
     - [x] Link payments to authenticated user and verified orders
     - [x] Add payment processing audit logging
     - [x] Validate payment amounts against order totals

#### Acceptance Criteria:

- [x] **All webshop API endpoints require valid JWT authentication**
- [x] **Only users with hdcnLeden role can access webshop functionality**
- [x] **Users can only access and modify their own carts and orders**
- [x] **All webshop operations are properly audited and logged**
- [x] **Unauthorized access attempts are blocked and logged**

#### Security Impact:

**CRITICAL**: This addresses a major security vulnerability where webshop APIs are currently unprotected and can be accessed by anyone without authentication. This creates risks for:

- Unauthorized cart/order creation
- Data manipulation and privacy breaches
- Financial fraud through unvalidated orders/payments
- System abuse and resource consumption

---

### MVP-7: Frontend Integration for Passwordless Authentication

**Priority**: High
**Estimated Effort**: 2-3 days

#### Tasks:

1. **Update authentication flow for passwordless**

   - [x] **Review and update Amplify configuration**:
     - [x] Update `frontend/src/aws-exports.js` with new Cognito User Pool settings
     - [x] Configure Amplify for passwordless authentication support
     - [x] Update authentication flow to use `ALLOW_USER_AUTH` flow type
     - [x] Test Amplify configuration with new User Pool settings
   - [x] **Integrate existing passwordless components**:
     - [x] Connect `PasskeySetup` component to main auth flow
     - [x] Integrate `EmailRecovery` component for account recovery
     - [x] Connect `CrossDeviceAuth` for cross-device authentication
     - [x] Test complete passwordless authentication flow

2. **Update login/signup flow**
   - [x] **Replace existing login with passwordless**:
     - [x] Remove password-based login components
     - [x] Integrate passwordless signup component
     - [x] Add passkey authentication as primary method
     - [x] Implement email recovery as fallback
   - [x] **Test authentication integration**:
     - [x] Test complete signup → verification → passkey setup flow
     - [x] Test passkey authentication flow
     - [x] Test email recovery → new passkey setup flow
     - [x] Verify role assignment after authentication and approval of membership status change to Actief/Active

#### Acceptance Criteria:

- [x] **Existing Amplify authentication flow is updated for passwordless authentication**
- [x] **Passkey registration and authentication work across devices**
- [x] **Email-based account recovery working without password fallback**

3  days of testing cognito implementation but it still does not work. all tests passes succesfully 

---

### MVP-8: Existing Member Migration Strategy

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

#### Acceptance Criteria:

- [ ] **IaC template includes migration Lambda function with proper permissions**
- [ ] **Bulk migration creates Cognito accounts for all existing members without passwords**
- [ ] **Migrated members receive clear instructions for email verification and passkey setup**
- [ ] **Migration process handles duplicate and invalid email addresses gracefully**

---

### MVP-9: New Member Application Process

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

3. **Create application status and management**
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
- [ ] **New applications are stored with `status: 'new_applicant'`**
- [ ] **Applicants receive confirmation message after submission**
- [ ] **Administrators receive email notifications for new applications**

---

## Full Implementation (Phase 2)

### FULL-1: Enhanced Security and MFA

**Priority**: High
**Estimated Effort**: 3-4 days

#### Tasks:

1. **Implement MFA for administrative roles**

   - [ ] **Configure Cognito MFA for administrative users**:
     - [ ] Set up MFA configuration in Cognito User Pool
     - [ ] Configure MFA to be required for users with administrative roles
     - [ ] Set up adaptive MFA triggers based on suspicious activity
     - [ ] Test MFA configuration with test administrative accounts
   - [ ] **Implement role-based MFA policy**:
     - [ ] Administrative roles require MFA when suspicious activity is detected
     - [ ] Regular members (hdcnLeden) do not require MFA for streamlined experience
     - [ ] Create MFA policy logic based on roles
     - [ ] Test MFA policy with different user types

2. **Implement suspicious activity detection**
   - [ ] **Login pattern analysis**: Detect unusual login locations, times, devices
   - [ ] **Failed attempt monitoring**: Track and respond to multiple failed attempts
   - [ ] **Progressive security measures**: Temporary lockout, email notification, admin alerts
   - [ ] **Security event logging**: Comprehensive logging of all security-related events

#### Acceptance Criteria:

- [ ] **MFA is mandatory for administrative roles when suspicious activity is detected**
- [ ] **Regular members do not require MFA for streamlined experience**
- [ ] **Suspicious activity detection triggers appropriate security measures**
- [ ] **All authentication and security events are comprehensively logged**

---

### FULL-2: Advanced Export System

**Priority**: Medium
**Estimated Effort**: 4-5 days

#### Tasks:

1. **Implement comprehensive export functionality**

   - [ ] **Multiple format support**: CSV, XLSX, PDF, TXT formats
   - [ ] **Custom field selection**: Allow administrators to choose specific data fields
   - [ ] **Advanced filtering**: Region, membership type, payment status, roles, date ranges
   - [ ] **Export templates**: Predefined templates for common use cases

2. **Add export templates and use cases**
   - [ ] **Mailing lists**: Email-only exports for communications
   - [ ] **Address labels**: Physical address formatting for postal services
   - [ ] **Membership statistics**: Aggregated data and analytics reports
   - [ ] **Anniversary recognition**: Members by years of membership (5, 10, 25 years)
   - [ ] **Administrative reports**: Comprehensive member data for admin use

#### Acceptance Criteria:

- [ ] **Users can export data in multiple formats (CSV, XLSX, PDF, TXT)**
- [ ] **Export access is properly restricted by role and region**
- [ ] **All exports are logged for audit purposes**
- [ ] **Export performance is optimized for large datasets**

---

### FULL-3: Integration and API Features

**Priority**: Low
**Estimated Effort**: 3-4 days

#### Tasks:

1. **Implement API endpoints for external integration**

   - [ ] **RESTful authentication API**: Provide API access to authentication functions
   - [ ] **Role management API**: API endpoints for role queries and assignments
   - [ ] **Export API with OAuth2**: Secure API access for data exports
   - [ ] **Member data API**: Controlled access to member information

2. **Add webhook support for real-time notifications**
   - [ ] **Member data change notifications**: Notify external systems of member updates
   - [ ] **Role assignment notifications**: Alert external systems of role changes
   - [ ] **Authentication event webhooks**: Real-time authentication event notifications

#### Acceptance Criteria:

- [ ] **APIs are available for external integration with proper authentication**
- [ ] **Webhooks notify external systems of relevant changes**
- [ ] **Integration with key external systems works (Google, email marketing, payments)**

---

## Implementation Strategy

### MVP First Approach

1. **Complete remaining MVP tasks** (estimated 10-15 days)
2. **Test thoroughly** with real users and passwordless authentication
3. **Gather feedback** on passwordless experience and role-based permissions
4. **Deploy MVP** to production for immediate value

### Full Implementation

1. **Implement FULL-1 through FULL-3** (estimated 10-15 days)
2. **Comprehensive testing** including security and performance testing
3. **Security audit** focusing on passwordless authentication and role-based access
4. **Production deployment** with full monitoring and compliance features

### Risk Mitigation

- **MVP provides immediate value** with passwordless authentication and basic roles
- **Incremental deployment** reduces risk of major authentication changes
- **Rollback capability** at each phase with fallback authentication methods
- **User feedback integration** throughout passwordless adoption process
- **Gradual migration** allows users to adapt to passwordless authentication
