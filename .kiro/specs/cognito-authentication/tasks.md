# Implementation Plan: Cognito Authentication Integration

## Overview

This implementation plan builds upon the existing Cognito admin infrastructure to add user-facing authentication flows, member portal access, and intelligent routing. The approach focuses on implementing the missing authentication components while leveraging the current admin API and member database structure.

## Tasks

- [ ] 1. Set up authentication infrastructure and extend existing services

  - Extend existing CognitoService and CognitoApiService with user-facing authentication methods
  - Add AWS Amplify configuration to existing React frontend
  - Configure Gmail API integration in existing Lambda infrastructure
  - Update existing SAM template and environment variables for new authentication flows
  - _Requirements: 1.1, 3.1, 6.4_

- [ ] 2. Implement core authentication hook (useAuth)

  - [ ] 2.1 Create useAuth hook with Amplify integration

    - Implement login, logout, signup, and password reset functions
    - Add session state management and token refresh
    - Include role and permission checking utilities
    - _Requirements: 2.1, 2.2, 2.5_

  - [ ]\* 2.2 Write property test for authentication hook

    - **Property 1: Account Registration Round Trip**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [ ]\* 2.3 Write property test for password complexity
    - **Property 2: Password Complexity Enforcement**
    - **Validates: Requirements 1.4, 3.2**

- [ ] 3. Extend existing authentication service and add routing logic

  - [ ] 3.1 Extend existing hdcn_cognito_admin Lambda with user authentication endpoints

    - Add user validation and routing endpoints to existing Cognito admin function
    - Extend existing member database lookup functionality
    - Add user route determination based on membership status
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]\* 3.2 Write property test for authentication routing

    - **Property 3: Authentication Routing Consistency**
    - **Validates: Requirements 2.1, 5.1, 5.2**

  - [ ] 3.3 Implement error handling and logging

    - Add comprehensive error handling for authentication failures
    - Implement security event logging
    - Create user-friendly error messages
    - _Requirements: 2.2, 2.3, 10.3_

  - [ ]\* 3.4 Write property test for error handling
    - **Property 4: Authentication Error Handling**
    - **Validates: Requirements 2.2, 2.3, 1.5**

- [ ] 4. Checkpoint - Ensure authentication flow works

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement member migration service

  - [ ] 5.1 Create Migration Service for bulk member import

    - Build service to create Cognito accounts without passwords
    - Implement duplicate email handling and conflict resolution
    - Add migration reporting and error tracking
    - _Requirements: 4.1, 4.2, 4.5_

  - [ ]\* 5.2 Write property test for migration process

    - **Property 6: Migration Account Creation**
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [ ]\* 5.3 Write property test for conflict resolution
    - **Property 7: Migration Conflict Resolution**
    - **Validates: Requirements 4.5**

- [ ] 6. Build email service integration

  - [ ] 6.1 Implement Google Gmail API service

    - Create email service class with Gmail API integration
    - Build email templates for welcome, notification, and approval emails
    - Add email sending functionality for migration and applications
    - _Requirements: 4.3, 6.4_

  - [ ]\* 6.2 Write unit tests for email service
    - Test email template generation
    - Test Gmail API integration
    - Test error handling for email failures
    - _Requirements: 4.3, 6.4_

- [ ] 7. Create member registration flow using existing components

  - [ ] 7.1 Build Registration Form component extending existing member management UI

    - Create React component based on existing member form patterns in MemberAdminPage
    - Reuse existing form validation and error handling from member components
    - Extend existing member API endpoints to handle 'new_applicant' status creation
    - _Requirements: 6.1, 6.2, 6.5_

  - [ ]\* 7.2 Write property test for application processing

    - **Property 8: Member Application Processing**
    - **Validates: Requirements 6.1, 6.2, 6.4**

  - [ ]\* 7.3 Write property test for application validation
    - **Property 9: Application Validation**
    - **Validates: Requirements 6.5**

- [ ] 8. Implement member portal extending existing member management UI

  - [ ] 8.1 Create Member Portal component based on existing CognitoAdminPage structure

    - Build authenticated member dashboard using existing Chakra UI patterns from CognitoAdminPage
    - Extend existing member display components for read-only and editable field distinction
    - Reuse existing member update functionality from admin interface
    - _Requirements: 7.1, 7.2, 7.3, 7.5_

  - [ ]\* 8.2 Write property test for portal data display

    - **Property 10: Member Portal Data Display**
    - **Validates: Requirements 7.1, 7.2, 7.5**

  - [ ]\* 8.3 Write property test for information updates
    - **Property 11: Member Information Updates**
    - **Validates: Requirements 7.3**

- [ ] 9. Add webshop access and extend existing parameter system

  - [ ] 9.1 Implement webshop access control using existing module patterns

    - Extend existing webshop module with authentication checks
    - Reuse existing access control patterns from other modules
    - _Requirements: 7.4_

  - [ ]\* 9.2 Write property test for webshop access

    - **Property 12: Webshop Access Control**
    - **Validates: Requirements 7.4**

  - [ ] 9.3 Extend existing parameter system for module visibility

    - Build on existing Parameter Store functionality in utils/parameterService.tsx
    - Extend existing parameter evaluation logic for module access control
    - Reuse existing parameter loading and caching mechanisms
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ]\* 9.4 Write property test for module access control
    - **Property 13: Parameter-Based Module Access**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**

- [ ] 10. Checkpoint - Ensure member portal functionality works

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement data synchronization with admin controls

  - [ ] 11.1 Create admin-triggered synchronization service

    - Build service to sync member data changes with Cognito in real-time
    - Implement email address and account status synchronization
    - Add administrator-triggered sync functionality with reporting dashboard
    - _Requirements: 9.1, 9.2, 9.4_

  - [ ]\* 11.2 Write property test for data synchronization

    - **Property 15: Data Synchronization Consistency**
    - **Validates: Requirements 9.1, 9.2, 9.4**

  - [ ] 11.3 Add synchronization controls to existing CognitoAdminPage

    - Add "Sync with Member Database" button to admin interface
    - Display sync status, reports, and inconsistency resolution options
    - Integrate with existing admin UI patterns and error handling
    - _Requirements: 9.3, 9.5_

  - [ ] 11.4 Add synchronization error handling and retry logic

    - Implement error detection and logging for data inconsistencies
    - Add retry logic with exponential backoff for failed operations
    - Create detailed reconciliation reports and admin notifications
    - _Requirements: 9.3, 9.5_

  - [ ]\* 11.4 Write property test for sync error handling
    - **Property 16: Synchronization Error Handling**
    - **Validates: Requirements 9.3, 9.5**

- [ ] 12. Implement security, MFA policies, and administrative access control

  - [ ] 12.1 Add administrative access control for membership status changes

    - Restrict membershipStatus field updates to hdcnAdmins group only
    - Add validation in both frontend and backend for status change requests
    - Implement audit logging for all status change attempts and successes
    - _Requirements: 11.1, 11.2, 11.3_

  - [ ]\* 12.2 Write property test for administrative access control

    - **Property 20: Administrative Status Control**
    - **Validates: Requirements 11.1, 11.2, 11.3**

  - [ ] 12.3 Configure MFA policies and group-based enforcement

    - Set up mandatory MFA for hdcnAdmins group
    - Configure optional MFA for regular members
    - Implement progressive security measures
    - _Requirements: 10.1, 10.2_

  - [ ]\* 12.2 Write property test for MFA enforcement

    - **Property 17: MFA Policy Enforcement**
    - **Validates: Requirements 10.1, 10.2**

  - [ ] 12.3 Add security monitoring and protection measures

    - Implement suspicious activity detection
    - Add progressive account protection measures
    - Create security event logging and admin notifications
    - _Requirements: 10.3, 10.4_

  - [ ]\* 12.4 Write property test for security measures

    - **Property 18: Security Event Logging**
    - **Validates: Requirements 10.3, 5.4**

  - [ ]\* 12.5 Write property test for protection measures
    - **Property 19: Security Protection Measures**
    - **Validates: Requirements 10.4**

- [ ] 13. Integration and final wiring

  - [ ] 13.1 Wire authentication components together

    - Connect useAuth hook with Authentication Service
    - Integrate routing logic with UI components
    - Connect member portal with parameter service
    - _Requirements: All authentication and routing requirements_

  - [ ]\* 13.2 Write integration tests
    - Test complete authentication flows end-to-end
    - Test member registration and approval workflow
    - Test parameter changes and module visibility updates
    - _Requirements: All requirements_

- [ ] 14. Update member database schema and migration

  - [ ] 14.1 Update Member table schema for new status field

    - Add 'new_applicant' and 'ended' status values
    - Make membership fields optional for applicants
    - Add application tracking fields (applicationDate, approvedBy, etc.)
    - _Requirements: 6.2, 7.1_

  - [ ] 14.2 Create database migration script
    - Update existing member records to use new status values
    - Set default values for new optional fields
    - Validate data integrity after migration
    - _Requirements: 4.1, 9.1_

- [ ] 15. Final checkpoint - Ensure complete system integration
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- **Reuse Existing Infrastructure**: Build on existing CognitoService, member components, and Lambda functions
- **Extend Current UI**: Use existing Chakra UI patterns and component structure from CognitoAdminPage
- **Leverage Parameter System**: Build on existing parameterService.tsx and parameter management
- Gmail API integration leverages Google Workspace for Nonprofits account
