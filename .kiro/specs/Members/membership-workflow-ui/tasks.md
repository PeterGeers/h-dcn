# Implementation Plan

## Overview

Wire the backend workflow engine end-to-end for the membership lifecycle: a new Lambda handler that invokes the engine, email templates sent via SES, welcome pack tracking, and a frontend UI with workflow action buttons (single + bulk) replacing the free status dropdown.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "2.1", "2.2", "2.3"] },
    { "id": 1, "tasks": ["3.1", "3.2", "3.3", "3.4", "4.1", "4.2"] },
    { "id": 2, "tasks": ["5.1", "5.2", "5.3", "5.4", "5.5", "5.6"] },
    { "id": 3, "tasks": ["6.1", "6.2", "6.3", "6.4"] },
    { "id": 4, "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5"] },
    { "id": 5, "tasks": ["8.1", "8.2", "8.3", "8.4"] },
    { "id": 6, "tasks": ["9.1", "9.2", "9.3"] },
    { "id": 7, "tasks": ["10.1", "10.2", "10.3"] }
  ]
}
```

## Tasks

- [x] 1. Backend — transition_member handler (single)
  - [x] 1.1 Create `backend/handler/transition_member/app.py` with: auth check (`Members_CRUD` or `Members_Status_Approve`), load member from DynamoDB, status-to-state mapping (`STATUS_TO_STATE` / `STATE_TO_STATUS` dicts), call `membership_engine.execute()`, call `dispatcher.execute_transition()`, persist new status + `status_history` append, return TransitionResult as JSON response
  - [x] 1.2 Register all dispatcher actions: `activate_member` (set status=Actief, set ingangsdatum, add hdcnLeden Cognito group), `deactivate_member` (set status=Opgezegd, remove hdcnLeden group), `suspend_member` (set status=Geschorst, store reason), `flag_welcome_pack` (set welcome_pack_status=pending, validate address), `audit_log` (call write_workflow_audit)
  - [x] 1.3 Add `TransitionMemberFunction` to SAM template (template.yaml) with API Gateway event `POST /members/{member_id}/transition`, Layers: AuthLayer, Policies: DynamoDB Members, SES, Cognito, S3 email templates bucket

- [x] 2. Backend — bulk transition handler
  - [x] 2.1 Create `backend/handler/bulk_transition_members/app.py` with: auth check (`Members_CRUD`), accept `{ event, member_ids, context }`, iterate members independently, collect per-member results, return summary `{ total, succeeded, failed, results }`
  - [x] 2.2 Add `BulkTransitionMembersFunction` to SAM template with API Gateway event `POST /members/bulk-transition`, max batch size validation (25)
  - [x] 2.3 Add guard for APPROVE transition: `has_region_assigned(ctx)` in `backend/layers/auth-layer/python/shared/workflows/guards.py` that checks `ctx.get('regio')` is not None/empty

- [x] 3. Backend — email side effect actions
  - [x] 3.1 Create email sending utility `backend/handler/transition_member/email_actions.py` with: `send_membership_email(template_name, recipient, variables, locale)` function using existing SES pattern (load template from S3, render with variables, send via `ses_client.send_email()`)
  - [x] 3.2 Register side effect actions in dispatcher: `send_application_email`, `send_payment_request`, `send_welcome_email`, `send_cancellation_email`, `send_suspension_notice`, `notify_admin` — each builds context variables from member data and calls `send_membership_email()`
  - [x] 3.3 Create Dutch (nl) email templates in `backend/email-templates/templates/nl/`: `membership-application-confirmation.html`, `membership-application-admin-notification.html`, `membership-approved-payment-request.html`, `membership-welcome.html`, `membership-cancellation-confirmation.html`, `membership-suspension-notice.html`
  - [x] 3.4 Create English (en) versions of all 6 templates in `backend/email-templates/templates/en/` (other 6 languages can follow later)

- [x] 4. Backend — tests
  - [x] 4.1 Create `backend/tests/unit/test_transition_member.py`: test valid transitions (APPROVE, PAYMENT_RECEIVED, CANCEL, SUSPEND), invalid transitions (wrong state), guard failures (missing regio, missing reason), status_history append, welcome_pack_status set on activation
  - [x] 4.2 Create `backend/tests/unit/test_bulk_transition_members.py`: test bulk success, partial failure (one member missing regio), batch size limit, all members must exist

- [x] 5. Frontend — workflow configuration and types
  - [x] 5.1 Create `frontend/src/config/workflows/types.ts` with: `MemberWorkflowState` type, `MemberWorkflowEvent` type, `TransitionConfig` interface (event, target, label, actors, requiredFields, confirmMessage, description), `WorkflowDefinition` interface
  - [x] 5.2 Create `frontend/src/config/workflows/membershipWorkflow.ts` with: `STATUS_TO_STATE` mapping, `STATE_TO_STATUS` mapping, `MEMBER_STATES` const array, `membershipWorkflow` object defining transitions per state with i18n label keys, actors, required fields
  - [x] 5.3 Create `frontend/src/config/workflows/index.ts` re-exporting all types and the membershipWorkflow
  - [x] 5.4 Create `frontend/src/locales/nl/workflows.json` with Dutch labels for all transitions, confirmations, descriptions, and error messages
  - [x] 5.5 Create `frontend/src/locales/en/workflows.json` with English translations
  - [x] 5.6 Add `workflows.json` to remaining 6 locales (de, fr, es, it, da, sv) — can copy English as starting point

- [x] 6. Frontend — MemberWorkflowPanel component
  - [x] 6.1 Create `frontend/src/modules/members/components/MemberWorkflowPanel.tsx`: shows current status badge, renders action buttons filtered by user role and available transitions, disables buttons when required fields missing (e.g., regio not set), triggers confirmation dialog
  - [x] 6.2 Create `frontend/src/modules/members/components/TransitionConfirmDialog.tsx`: confirmation modal with action description, consequence text, optional required input fields (reason textarea), Confirm/Cancel buttons, loading state during API call
  - [x] 6.3 Create `frontend/src/modules/members/hooks/useMemberTransition.ts`: hook that calls `POST /members/{id}/transition`, handles loading/error state, returns mutate function, refreshes member data on success
  - [x] 6.4 Modify `MemberEditView.tsx`: make the `status` field read-only (add `readOnly: true` override or change `canEditField` logic for status), embed `MemberWorkflowPanel` in the Lidmaatschap section

- [x] 7. Frontend — bulk processing
  - [x] 7.1 Add checkbox column to `MemberAdminTable.tsx`: show when user has `Members_CRUD` or `Members_Status_Approve`, track selected member IDs in state, "select all" header checkbox
  - [x] 7.2 Create `frontend/src/modules/members/components/BulkActionBar.tsx`: sticky bar showing selection count, action dropdown (computed from intersection of valid events for all selected members' statuses), Execute button, disabled state when mixed statuses selected
  - [x] 7.3 Create `frontend/src/modules/members/components/BulkResultSummary.tsx`: modal showing success/failure per member after bulk execution, with name + error for failures
  - [x] 7.4 Create `frontend/src/modules/members/hooks/useBulkTransition.ts`: hook that calls `POST /members/bulk-transition`, handles loading state, returns results
  - [x] 7.5 Wire BulkActionBar into MemberAdminTable: show bar when selection > 0, pass selected IDs to hook, show BulkResultSummary on completion

- [x] 8. Frontend — status history timeline and welcome packs
  - [x] 8.1 Create `frontend/src/modules/members/components/MemberWorkflowTimeline.tsx`: vertical timeline component reading `status_history` array from member, shows from→to, date, triggered by, most recent first
  - [x] 8.2 Add MemberWorkflowTimeline section to `MemberEditView.tsx` as a collapsible "History" accordion at the bottom
  - [x] 8.3 Create `frontend/src/modules/members/components/WelcomePackList.tsx`: tab component listing members with `welcome_pack_status=pending`, showing name/address/lidnummer/activation date, "Sent" button per row, bulk "Mark as sent"
  - [x] 8.4 Add "Welkomstpakketten" tab to MemberAdminPage (visible for Members_CRUD only)

- [x] 9. Integration testing and SAM deploy
  - [x] 9.1 Run `sam build --use-container` from backend/ to verify template changes compile
  - [x] 9.2 Upload email templates to S3 bucket: `aws s3 sync backend/email-templates/templates/ s3://h-dcn-email-templates/templates/ --profile nonprofit-deploy`
  - [x] 9.3 Run frontend type check (`npx tsc --noEmit`) and lint on all modified files

- [x] 10. Field registry and API config updates
  - [x] 10.1 Update `frontend/src/config/memberFields/fields/membershipFields.ts`: add `welcome_pack_status` field definition (enum: pending/sent/not_applicable, group: administrative, admin-only)
  - [x] 10.2 Add `transition` and `bulk-transition` endpoints to `frontend/src/config/api.ts` (API_URLS)
  - [x] 10.3 Update `frontend/src/config/memberFields/modalConfig.ts`: set `readOnly: true` on the status field in the memberView context, add MemberWorkflowPanel placeholder field

## Notes

- The `transition_member` handler reuses the existing `membership_engine` from the shared layer — no new engine code needed.
- Email templates are side effects. If SES is down, the status transition still succeeds and the admin sees a "side effect failed" note in the response, but the transition completes.
- The `welcome_pack_status` field doesn't exist on current member records. This is fine — DynamoDB is schemaless. New activations will get the field; existing active members won't have it (and won't appear in the welcome packs list).
- The bulk handler processes members sequentially (not parallel Lambda invocations) to stay simple. At 25 members max, this completes within Lambda timeout.
- The `Members_Status_Approve` role is currently not in the `getUserRole()` priority list in MemberAdminPage. Task 7.1 must also update this function to recognize it (returning it as a valid role that can see workflow buttons).
