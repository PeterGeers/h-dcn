# Requirements Document

## Introduction

The H-DCN member portal needs a proper application submission flow that integrates with the existing workflow engine. Currently, the self-service form (`POST /members/me`) directly writes a record with status 'Aangemeld' to DynamoDB, bypassing the workflow engine entirely. This means no confirmation emails are sent, no admin notifications are triggered, and no proper lifecycle tracking happens via `status_history`.

This feature introduces a two-phase approach: applicants first save their personal details as a draft (no workflow status), and then explicitly submit their application via the workflow engine's SUBMIT event. This triggers the proper transition to 'Aangemeld', sends emails, and locks the form into read-only mode.

## Glossary

- **Self_Service_Endpoint**: The Lambda handler at `backend/handler/get_member_self/app.py` serving `GET`, `POST`, and `PUT` on `/members/me`
- **Workflow_Engine**: The state machine implementation at `backend/layers/auth-layer/python/shared/workflows/` that evaluates transitions, guards, actions, and side effects
- **Transition_Handler**: The Lambda handler at `backend/handler/transition_member/app.py` serving `POST /members/{id}/transition`
- **Member_Record**: A DynamoDB item in the Members table identified by `member_id`
- **Draft_State**: A Member_Record that has no `status` field, indicating the applicant has not yet submitted their application
- **Applicant**: A user with the `verzoek_lid` Cognito role who is filling in or has submitted a membership application
- **Admin**: A user with the `Members_Status_Approve` permission (ledenadministratie)
- **SUBMIT_Event**: The `MemberEvent.SUBMIT` workflow event that transitions a member from Draft_State to 'Aangemeld'
- **Application_Form**: The frontend React page where the Applicant fills in personal details for their membership application
- **Field_Registry**: The single source of truth for member field definitions at `frontend/src/config/memberFields/`

## Requirements

### Requirement 1: Draft Record Creation

**User Story:** As an Applicant, I want to save my personal details incrementally, so that I can log out and return later to continue filling in my application.

#### Acceptance Criteria

1. WHEN an Applicant with the `verzoek_lid` role calls `POST /members/me` with personal details, THE Self_Service_Endpoint SHALL create a Member_Record without a `status` field
2. WHEN an Applicant with an existing Draft_State record calls `PUT /members/me` with updated details, THE Self_Service_Endpoint SHALL update the Member_Record while preserving the absence of a `status` field
3. THE Self_Service_Endpoint SHALL store a `member_id` (UUID) in Cognito's `custom:member_id` attribute when creating a new Member_Record
4. THE Self_Service_Endpoint SHALL store a `created` timestamp and a `lastModified` timestamp on every write operation
5. WHEN an Applicant calls `GET /members/me` and no Member_Record exists, THE Self_Service_Endpoint SHALL return a response indicating no record exists along with the Applicant's email address

### Requirement 2: Application Submission via Workflow Engine

**User Story:** As an Applicant, I want to submit my completed application through the workflow engine, so that proper lifecycle tracking, emails, and admin notifications are triggered.

#### Acceptance Criteria

1. WHEN an Applicant calls `POST /members/{member_id}/transition` with event `SUBMIT`, THE Transition_Handler SHALL transition the Member_Record from Draft_State to 'Aangemeld' status
2. THE Workflow_Engine SHALL define a transition from a pre-application state to `MemberState.APPLIED` triggered by `MemberEvent.SUBMIT`
3. WHEN the SUBMIT transition executes, THE Workflow_Engine SHALL invoke the `send_application_email` side effect to send a confirmation email to the Applicant
4. WHEN the SUBMIT transition executes, THE Workflow_Engine SHALL invoke the `notify_admin` side effect to send a notification email to webmaster@h-dcn.nl
5. THE Transition_Handler SHALL allow users with the `verzoek_lid` role to execute the SUBMIT event on their own Member_Record
6. THE Transition_Handler SHALL append a `status_history` entry recording the transition from Draft_State to 'Aangemeld'
7. IF an Applicant attempts to SUBMIT without a Member_Record existing, THEN THE Transition_Handler SHALL return a 404 error
8. IF an Applicant attempts to SUBMIT a Member_Record that already has a `status` field, THEN THE Transition_Handler SHALL return a 400 error indicating the application was already submitted

### Requirement 3: Post-Submission Read-Only State

**User Story:** As an Applicant, I want to see my submitted application in read-only mode with a status indicator, so that I know my application is being processed and I cannot accidentally alter it.

#### Acceptance Criteria

1. WHEN an Applicant calls `PUT /members/me` on a Member_Record that has a `status` field, THE Self_Service_Endpoint SHALL reject the update with a 403 error and a message indicating the record is locked after submission
2. WHEN an Applicant calls `GET /members/me` on a submitted Member_Record, THE Self_Service_Endpoint SHALL return the member data including the current `status` field value
3. THE Application_Form SHALL display the member data in read-only mode when the Member_Record has a `status` field
4. THE Application_Form SHALL display a status indicator showing the current workflow status (e.g., 'Aangemeld', 'wachtRegio', 'wachtBetaling', 'Actief')
5. WHEN the Self_Service_Endpoint rejects an edit with a 403 locked-after-submission error, THE Application_Form SHALL display a message explaining that the application has been submitted and can no longer be edited

### Requirement 4: Frontend Application Form

**User Story:** As an Applicant, I want a clear form interface to fill in my details and submit my application, so that I understand what information is needed and when my application is complete.

#### Acceptance Criteria

1. THE Application_Form SHALL display input fields for personal details as defined in the Field_Registry with `selfService: true` permission
2. THE Application_Form SHALL validate required fields before enabling the submit button
3. WHEN the Applicant clicks a save button, THE Application_Form SHALL call `PUT /members/me` to persist the current data without triggering a workflow transition
4. WHEN the Applicant clicks a submit button, THE Application_Form SHALL first save the current data via `PUT /members/me`, then call `POST /members/{member_id}/transition` with event `SUBMIT`
5. WHEN the SUBMIT transition returns success, THE Application_Form SHALL switch to read-only mode and display the new status
6. IF the SUBMIT transition returns an error, THEN THE Application_Form SHALL display the error message and keep the form in editable mode
7. THE Application_Form SHALL display a confirmation dialog before executing the SUBMIT action, warning the Applicant that the application cannot be edited after submission

### Requirement 5: Authorization for Self-Service Submission

**User Story:** As the system administrator, I want the SUBMIT transition to be restricted to the record owner with `verzoek_lid` role, so that only legitimate applicants can submit their own applications.

#### Acceptance Criteria

1. THE Transition_Handler SHALL verify that the authenticated user's `member_id` matches the `member_id` in the transition request path when processing a SUBMIT event from a `verzoek_lid` user
2. IF a `verzoek_lid` user attempts to SUBMIT a transition for a Member_Record that does not belong to them, THEN THE Transition_Handler SHALL return a 403 error
3. THE Transition_Handler SHALL continue to allow users with `Members_Status_Approve` permission to execute transitions on any Member_Record regardless of ownership
