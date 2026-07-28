# Membership Workflow UI — Requirements

## Context

The backend workflow engine (spec: `Workflow framework`) is built and tested. The engine validates transitions, executes actions, and writes audit trails. However, the following pieces are missing:

1. **No frontend integration** — admins have no way to execute workflow transitions from the UI
2. **No backend handler** — there is no `transition_member` Lambda that actually invokes the engine
3. **No email notifications** — the templates exist (empty) but are never sent
4. **No physical mail tracking** — upon activation a welcome pack (letter, stickers, badge) must be sent by post
5. **No bulk processing** — handling multiple applicants in the same step is not possible

This spec describes the full end-to-end integration: from button click in the frontend → backend transition → email/post → audit trail.

### Current Situation

Today, the `status` field renders as a free dropdown for `Members_CRUD` users. An admin can pick any value (e.g., jump from `Aangemeld` straight to `Actief`) without validation — no check that the transition makes sense, no required actions triggered (like "did they pay?"), and no audit trail.

The `Members_Status_Approve` Cognito role exists but is not wired into the `MemberEditView` modal — it only has effect in the older `MemberEditModal` and in `functionPermissions.ts`. The workflow UI will properly use this role as the authority for who can trigger status transitions.

The workflow UI replaces the free dropdown with guided action buttons. All other existing field editing (personal, address, motor, etc.) remains unchanged.

### References

- #[[file:.kiro/specs/Workflow framework/design.md]]
- #[[file:backend/layers/auth-layer/python/shared/workflows/membership.py]]
- #[[file:frontend/src/config/memberFields/fields/membershipFields.ts]]
- #[[file:backend/email-templates/config/variables.json]]

---

## Status Mapping

The existing `status` values in DynamoDB (Members table) must be mapped to workflow engine states:

| DynamoDB status | Workflow State | Description                              |
| --------------- | -------------- | ---------------------------------------- |
| `Aangemeld`     | `applied`      | New member, application submitted        |
| `wachtRegio`    | `pending`      | Waiting for region assignment / approval |
| `wachtBetaling` | `wait_payment` | Approved, waiting for payment            |
| `Actief`        | `active`       | Full member                              |
| `Opgezegd`      | `cancelled`    | Membership cancelled                     |
| `Geschorst`     | `suspended`    | Temporarily suspended                    |

> **Note**: `HdcnAccount`, `Club`, `Sponsor`, `Overig` fall outside the workflow — these are managed manually and are not part of the membership lifecycle.

---

## Traceability Matrix

| Requirement | Subject                          | Status |
| ----------- | -------------------------------- | ------ |
| 1.1         | Workflow action panel in modal   | ▶ TODO |
| 1.2         | Status becomes read-only         | ▶ TODO |
| 1.3         | Confirmation dialog              | ▶ TODO |
| 1.4         | Required fields per transition   | ▶ TODO |
| 1.5         | Error handling                   | ▶ TODO |
| 2.1         | Row selection in table           | ▶ TODO |
| 2.2         | Bulk action bar                  | ▶ TODO |
| 2.3         | Same-status requirement          | ▶ TODO |
| 2.4         | Result summary                   | ▶ TODO |
| 2.5         | Per-member error detail          | ▶ TODO |
| 3.1         | transition_member handler        | ▶ TODO |
| 3.2         | Bulk transition endpoint         | ▶ TODO |
| 3.3         | Dispatcher action registration   | ▶ TODO |
| 3.4         | Persist after success            | ▶ TODO |
| 3.5         | Guard error feedback             | ▶ TODO |
| 4.1         | Application confirmation email   | ▶ TODO |
| 4.2         | Admin notification email         | ▶ TODO |
| 4.3         | Approval + payment request email | ▶ TODO |
| 4.4         | Welcome email                    | ▶ TODO |
| 4.5         | Cancellation confirmation email  | ▶ TODO |
| 4.6         | Suspension notice email          | ▶ TODO |
| 5.1         | Welcome pack flagging            | ▶ TODO |
| 5.2         | Pack contents checklist          | ▶ TODO |
| 5.3         | Postal address validation        | ▶ TODO |
| 5.4         | Admin task: send pack            | ▶ TODO |
| 5.5         | Sent confirmation registration   | ▶ TODO |
| 6.1         | Frontend workflow config         | ▶ TODO |
| 6.2         | i18n labels                      | ▶ TODO |
| 6.3         | Permissions per transition       | ▶ TODO |
| 7.1         | Status history on entity         | ▶ TODO |
| 7.2         | Timeline component               | ▶ TODO |

---

## Requirements

### 1. Frontend — Single Member Workflow Panel

**1.1** The `MemberEditView` modal MUST include a "Workflow" section (in the Lidmaatschap card area) that:

- Displays the current status as a read-only colored badge
- Shows action buttons for all valid transitions from the current status
- Only shows buttons to users with the appropriate role (`Members_CRUD` or `Members_Status_Approve`)
- Disables buttons when required fields (e.g., `regio`) are missing on the member record

**1.2** The `status` field in the "Lidmaatschap" section MUST become read-only (currently it is a free dropdown for `Members_CRUD` users allowing arbitrary status changes). It MUST be replaced by a non-editable badge. Status changes go EXCLUSIVELY through the workflow action buttons. The existing `Members_Status_Approve` role becomes the permission gate for workflow transitions.

> All other fields in the modal (personal, address, lidmaatschap type, motor, financial, etc.) remain fully editable as they are today. Only the `status` field changes from dropdown to workflow-driven buttons.

**1.3** When clicking a workflow action button, a confirmation dialog MUST appear showing:

- The action being performed (e.g., "Approve member")
- What will happen as a consequence (e.g., "A payment request will be sent by email")
- A "Confirm" and "Cancel" button

**1.4** Some transitions require additional input from the admin:

| Transition | Required field | Validation                        |
| ---------- | -------------- | --------------------------------- |
| SUSPEND    | `reason`       | Minimum 10 characters             |
| APPROVE    | `regio`        | Must already be set on the member |
| CANCEL     | `reason`       | Minimum 10 characters (optional)  |

The confirmation dialog MUST show these fields when they are required.

**1.5** On error from the backend (guard failed, action failed):

- A clear error toast MUST appear
- The status MUST NOT change in the UI
- The modal MUST stay open so the admin can resolve the issue

---

### 2. Frontend — Bulk Processing

**2.1** The `MemberAdminTable` MUST show checkboxes per row when the user has `Members_CRUD` or `Members_Status_Approve` role.

**2.2** When one or more members are selected, a "Bulk Action" bar MUST appear above the table with:

- Count of selected members
- A dropdown showing available actions (only events valid for ALL selected members)
- An "Execute" button

**2.3** The bulk action dropdown MUST only show events valid for all selected members:

- All selected members must be in the same status
- If members in different statuses are selected: show "Select members with the same status" as a disabled option

**2.4** After executing a bulk action, a result summary MUST appear:

- "X of Y members successfully processed"
- Per failed member: name + error reason

**2.5** On partial failure, the summary MUST show per member:

- ✓ Successfully processed (with new status)
- ✗ Failed: [reason] (e.g., "regio missing", "payment not confirmed")

---

### 3. Backend — Transition Handler

**3.1** There MUST be a `transition_member` Lambda handler at `POST /members/{member_id}/transition` that:

- Checks authentication + authorization (`Members_CRUD` or `Members_Status_Approve`)
- Loads the member from DynamoDB
- Invokes the workflow engine with the event from the request body
- On success: executes dispatcher actions, persists status, returns response
- On failure: returns 400/500 with a clear error message

Request body:

```json
{
  "event": "APPROVE",
  "context": {
    "reason": "Meets all requirements"
  }
}
```

Response (success):

```json
{
  "success": true,
  "old_status": "Aangemeld",
  "new_status": "wachtBetaling",
  "actions_executed": ["send_payment_request"],
  "side_effects_executed": ["audit_log"]
}
```

Response (error):

```json
{
  "success": false,
  "error": "Guard 'requires_reason' not satisfied: reason is missing"
}
```

**3.2** There MUST be a `POST /members/bulk-transition` endpoint that:

- Accepts an array of `member_id` + `event`
- Processes each member independently (one failure does not stop the rest)
- Returns a summary result

Request body:

```json
{
  "event": "APPROVE",
  "member_ids": ["id-1", "id-2", "id-3"],
  "context": {}
}
```

Response:

```json
{
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "results": [
    { "member_id": "id-1", "success": true, "new_status": "wachtBetaling" },
    { "member_id": "id-2", "success": true, "new_status": "wachtBetaling" },
    { "member_id": "id-3", "success": false, "error": "regio missing" }
  ]
}
```

**3.3** The handler MUST create an `ActionDispatcher` instance with registered implementations for:

| Action name               | Implementation                                         |
| ------------------------- | ------------------------------------------------------ |
| `activate_member`         | Set status=Actief, ingangsdatum=now, add Cognito group |
| `deactivate_member`       | Set status=Opgezegd, remove Cognito group              |
| `suspend_member`          | Set status=Geschorst, store reason                     |
| `mark_invoice_paid`       | Update payment record in Payments table                |
| `send_application_email`  | SES: confirmation to applicant                         |
| `send_payment_request`    | SES: payment request to member                         |
| `send_welcome_email`      | SES: welcome to the club                               |
| `send_cancellation_email` | SES: cancellation confirmation                         |
| `send_suspension_notice`  | SES: suspension notice                                 |
| `notify_admin`            | SES: notification to ledenadministratie@h-dcn.nl       |
| `flag_welcome_pack`       | Mark welcome pack as "pending" for physical mail       |
| `audit_log`               | WORKFLOW_AUDIT to CloudWatch                           |

**3.4** The handler MUST only persist the DynamoDB status update AFTER all mandatory actions succeed.

**3.5** When a guard fails, the response MUST contain a clear, user-friendly error message that the frontend can display directly as a toast.

---

### 4. Email Notifications (SES Templates)

All emails use the existing template system: HTML templates in S3 bucket `h-dcn-email-templates`, rendered with `{{VARIABLE}}` placeholders, sent via SES. Sender: `noreply@h-dcn.nl`.

**4.1 Application confirmation** (when member submits application)

| Property  | Value                                                        |
| --------- | ------------------------------------------------------------ |
| Template  | `membership-application-confirmation`                        |
| Recipient | The new member (email from application form)                 |
| Trigger   | After successful application submission (status → Aangemeld) |
| Variables | `MEMBER_NAME`, `APPLICATION_DATE`, `MEMBERSHIP_TYPE`         |
| Content   | Thank you for your application, we'll get back to you        |

**4.2 Admin notification** (on new application)

| Property  | Value                                                                  |
| --------- | ---------------------------------------------------------------------- |
| Template  | `membership-application-admin-notification`                            |
| Recipient | `ledenadministratie@h-dcn.nl`                                          |
| Trigger   | After new application (status → Aangemeld)                             |
| Variables | `MEMBER_NAME`, `EMAIL`, `REGIO`, `MEMBERSHIP_TYPE`, `APPLICATION_DATE` |
| Content   | New application received, action required in portal                    |

**4.3 Approval + payment request** (admin approves)

| Property  | Value                                                                                                                               |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Template  | `membership-approved-payment-request`                                                                                               |
| Recipient | The member                                                                                                                          |
| Trigger   | Transition APPROVE (Aangemeld/wachtRegio → wachtBetaling)                                                                           |
| Variables | `MEMBER_NAME`, `MEMBERSHIP_TYPE`, `CONTRIBUTION_AMOUNT`, `PAYMENT_INSTRUCTIONS`, `PAYMENT_DEADLINE`, `IBAN`, `REFERENCE`            |
| Content   | Congratulations on your approval! Here are the payment instructions for your contribution. Reference number: X. Pay within 30 days. |

**4.4 Welcome email** (payment received, member activated)

| Property  | Value                                                                                                                                                              |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Template  | `membership-welcome`                                                                                                                                               |
| Recipient | The member                                                                                                                                                         |
| Trigger   | Transition PAYMENT_RECEIVED (wachtBetaling → Actief)                                                                                                               |
| Variables | `MEMBER_NAME`, `MEMBER_NUMBER`, `REGIO`, `REGIO_CONTACT_NAME`, `REGIO_CONTACT_EMAIL`, `PORTAL_URL`, `WELCOME_PACK_NOTE`                                            |
| Content   | Welcome to H-DCN! Your member number is X. You belong to region Y. Contact person: Z. Your welcome pack will be sent by post. Visit the portal at portal.h-dcn.nl. |

**4.5 Cancellation confirmation** (membership cancelled)

| Property  | Value                                                                                        |
| --------- | -------------------------------------------------------------------------------------------- |
| Template  | `membership-cancellation-confirmation`                                                       |
| Recipient | The member                                                                                   |
| Trigger   | Transition CANCEL (Actief → Opgezegd)                                                        |
| Variables | `MEMBER_NAME`, `CANCELLATION_DATE`, `MEMBERSHIP_END_DATE`, `MEMBER_SINCE`                    |
| Content   | Confirmation that your membership has been cancelled. Last day: X. We hope to see you again. |

**4.6 Suspension notice** (member suspended)

| Property  | Value                                                                                                         |
| --------- | ------------------------------------------------------------------------------------------------------------- |
| Template  | `membership-suspension-notice`                                                                                |
| Recipient | The member                                                                                                    |
| Trigger   | Transition SUSPEND (Actief → Geschorst)                                                                       |
| Variables | `MEMBER_NAME`, `SUSPENSION_DATE`, `REASON`, `CONTACT_EMAIL`                                                   |
| Content   | Your membership has been temporarily suspended. Reason: X. Contact ledenadministratie@h-dcn.nl for questions. |

### Email template rules

- All templates MUST be available in 8 languages (nl, en, de, fr, es, it, da, sv)
- Dutch (nl) is the primary language and gets created first
- Templates are stored in `s3://h-dcn-email-templates/templates/{locale}/`
- The existing `EmailTemplateService` is reused for rendering
- Emails are side effects — if SES fails, the transition is NOT blocked

---

### 5. Physical Mail — Welcome Pack

Upon activation of a new member (transition PAYMENT_RECEIVED → Actief), a physical welcome pack must be sent by post. This is a manual process performed by the admin, but the system MUST track it.

**5.1** Upon activation, the system MUST set a `welcome_pack_status` field on the member record with value `pending`.

Possible values: `pending` | `sent` | `not_applicable`

**5.2** The welcome pack contains:

- Personalized welcome letter (with name, member number, region)
- H-DCN sticker(s)
- H-DCN badge/pin
- Optional: region-specific information

**5.3** When setting `welcome_pack_status = pending`, the system MUST validate that the member has a complete postal address:

- `straat` OR `postadres` is filled
- `postcode` OR `postpostcode` is filled
- `woonplaats` OR `postwoonplaats` is filled

If the address is incomplete:

- Still set `welcome_pack_status = pending` (the pack must still be sent)
- Add a note: "Address incomplete — verify before sending"
- Show a warning in the UI

**5.4** In the admin UI there MUST be a "Welcome Packs" overview showing:

- All members with `welcome_pack_status = pending`
- Name, address, member number, activation date
- A "Sent" button per member (sets status to `sent` + date)
- A bulk "Mark as sent" option

**5.5** When an admin marks the pack as sent, the system MUST record:

- `welcome_pack_status`: `sent`
- `welcome_pack_sent_date`: ISO date
- `welcome_pack_sent_by`: admin's email

---

### 6. Frontend Workflow Configuration

**6.1** There MUST be a frontend configuration module at `frontend/src/config/workflows/membershipWorkflow.ts` that:

- Defines all states and events as TypeScript types
- Per state describes the available transitions with: event, target state, label, actors, required input fields
- Mirrors the backend transition definitions (the backend remains the authority)

**6.2** All labels in the workflow configuration MUST be i18n keys from the `workflows` namespace:

- `workflows.membership.approve` → "Approve" / "Goedkeuren"
- `workflows.membership.paymentReceived` → "Payment received" / "Betaling ontvangen"
- `workflows.membership.cancel` → "Cancel" / "Opzeggen"
- `workflows.membership.suspend` → "Suspend" / "Schorsen"
- `workflows.membership.reactivate` → "Reactivate" / "Heractiveren"

Translation files in all 8 languages.

**6.3** Per transition it MUST be configured which roles can execute it:

| Transition       | Allowed roles                                                    |
| ---------------- | ---------------------------------------------------------------- |
| APPROVE          | `Members_CRUD`, `Members_Status_Approve`                         |
| PAYMENT_RECEIVED | `Members_CRUD`, `Members_Status_Approve` (or system via webhook) |
| CANCEL           | `Members_CRUD`, `Members_Status_Approve`                         |
| SUSPEND          | `Members_CRUD`                                                   |
| REACTIVATE       | `Members_CRUD`                                                   |

---

### 7. Status History & Audit in UI

**7.1** On every status transition the handler MUST append to a `status_history` array on the member record:

```json
{
  "status_history": [
    {
      "from": "Aangemeld",
      "to": "wachtBetaling",
      "event": "APPROVE",
      "at": "2026-07-24T14:30:00Z",
      "by": "admin@h-dcn.nl"
    }
  ]
}
```

**7.2** The `MemberEditView` modal MUST include a "History" section with a visual timeline of all status transitions (similar to the order status_history in the webshop management module).

---

## Out of scope

- Automatic payment processing (Mollie/Stripe webhook for contributions) — separate spec
- Reminders for non-payment (scheduled Lambda) — separate spec
- Migration of existing members to the workflow model (separate migration script)
- Self-service cancellation by members — separate spec
- Reactivation after suspension (REACTIVATE event) — can be added later
- PDF generation of the welcome letter — manual process for now
