# Technical Design: Member Application Submission Flow

## Overview

This design introduces a two-phase member application flow: **draft** (save personal details without status) and **submit** (trigger workflow SUBMIT event → status becomes 'Aangemeld' + emails sent). The current `POST /members/me` endpoint hardcodes `status: 'Aangemeld'` immediately, bypassing the workflow engine entirely.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ Frontend (MyAccount / Application Form)                             │
│                                                                     │
│  1. Save draft → PUT /members/me (no status field)                  │
│  2. Submit    → POST /members/{id}/transition { event: "SUBMIT" }   │
│                                                                     │
└────────────┬────────────────────────────────────┬───────────────────┘
             │                                    │
             ▼                                    ▼
┌────────────────────────┐      ┌─────────────────────────────────────┐
│ GetMemberSelfFunction  │      │ TransitionMemberFunction            │
│ (handler/get_member_self)     │ (handler/transition_member)         │
│                        │      │                                     │
│ POST: create record    │      │ SUBMIT event:                       │
│   - NO status field    │      │   - Auth: verzoek_lid + own record  │
│   - Generates UUID     │      │   - Engine: draft → applied         │
│   - Syncs to Cognito   │      │   - SET status = 'Aangemeld'        │
│                        │      │   - Side effects:                   │
│ PUT: update draft only │      │     • send_application_email        │
│   - Rejects if status  │      │     • notify_admin                  │
│     already set        │      │     • audit_log                     │
│                        │      │                                     │
│ GET: return data +     │      │                                     │
│   status (if exists)   │      │                                     │
└────────────────────────┘      └─────────────────────────────────────┘
```

## Component Changes

### 1. Backend: Workflow Engine — Add `draft` state + SUBMIT transition

**File:** `backend/layers/auth-layer/python/shared/workflows/states.py`

Add `DRAFT = 'draft'` to `MemberState` enum.

**File:** `backend/layers/auth-layer/python/shared/workflows/membership.py`

Add transition:

```python
{
    'from_state': MemberState.DRAFT,
    'to_state': MemberState.APPLIED,
    'event': MemberEvent.SUBMIT,
    'actions': [],
    'side_effects': ['send_application_received', 'notify_admin', 'audit_log'],
}
```

### 2. Backend: Transition Handler — Allow `verzoek_lid` for SUBMIT

**File:** `backend/handler/transition_member/app.py`

Current auth check only allows `Members_CRUD` and `Members_Status_Approve`. Change:

```python
# For SUBMIT events from verzoek_lid users, allow self-transition
if transition_event == 'SUBMIT' and 'verzoek_lid' in user_roles:
    # Verify ownership: user's member_id must match the path parameter
    # Get member_id from Cognito custom:member_id attribute
    if member_id != user_member_id:
        return create_error_response(403, 'You can only submit your own application')
else:
    # Standard admin auth check
    is_authorized, perm_error, regional_info = validate_permissions_with_regions(...)
    if not is_authorized:
        return perm_error
```

### 3. Backend: Transition Handler — Map `draft` state

**File:** `backend/handler/transition_member/app.py`

Add to `STATUS_TO_STATE`:

```python
STATUS_TO_STATE: dict[str, str] = {
    ...existing entries...
}
```

For the draft state, the member has **no status field** in DynamoDB. Handle this case:

```python
current_status: str = member.get('status', '')

# Map status → state. Empty/missing status = draft state
if not current_status:
    current_state = MemberState.DRAFT
else:
    current_state = STATUS_TO_STATE.get(current_status)
```

### 4. Backend: GetMemberSelf — Remove hardcoded status, lock after submission

**File:** `backend/handler/get_member_self/app.py`

**POST (create):** Remove `'status': 'Aangemeld'` from `member_data`. The record is created without a status field (draft state).

**PUT (update):** Add a guard that rejects updates if the record already has a `status` field:

```python
existing = table.get_item(Key={'member_id': member_id})
if existing.get('Item', {}).get('status'):
    return create_error_response(403, 'Record is locked after submission. Contact ledenadministratie@h-dcn.nl for changes.')
```

### 5. Frontend: MyAccount / Application Form — Add submit button

**File:** `frontend/src/pages/MyAccount.tsx` + `frontend/src/components/MemberSelfServiceView.tsx`

When the user is `verzoek_lid` and the member record has no `status`:

- Show form in **editable mode** with "Opslaan" (save draft) and "Indienen" (submit) buttons
- "Opslaan" → `PUT /members/me` (persists data, stays editable)
- "Indienen" → confirmation dialog → `PUT /members/me` (save latest) → `POST /members/{member_id}/transition` with `{ "event": "SUBMIT" }` → switch to read-only

When the member record has a `status` field:

- Show form in **read-only mode** with status indicator badge
- No edit/submit buttons

### 6. Frontend: Workflow config — Add draft state

**File:** `frontend/src/config/workflows/membershipWorkflow.ts`

Add `draft` state to `STATUS_TO_STATE`:

```typescript
export const STATUS_TO_STATE: Record<string, MemberWorkflowState> = {
  ...existing entries...
  // Draft state has no DynamoDB status value — handled by absence of status field
};
```

Add `draft` to `MEMBER_STATES` and add a `draftTransitions` configuration for the SUBMIT button (visible only to `verzoek_lid`).

## Data Model

### Members Table — Draft Record (no status)

```json
{
  "member_id": "c4d36f77-...",
  "email": "applicant@example.com",
  "voornaam": "Jan",
  "achternaam": "Jansen",
  "regio": "Utrecht",
  "lidmaatschap": "Gewoon lid",
  "created": "2026-07-28T15:00:00Z",
  "lastModified": "2026-07-28T15:30:00Z"
}
```

Note: **No `status` field** — this indicates draft state.

### Members Table — After SUBMIT transition

```json
{
  "member_id": "c4d36f77-...",
  "email": "applicant@example.com",
  "voornaam": "Jan",
  "achternaam": "Jansen",
  "regio": "Utrecht",
  "lidmaatschap": "Gewoon lid",
  "status": "Aangemeld",
  "created": "2026-07-28T15:00:00Z",
  "lastModified": "2026-07-28T15:30:00Z",
  "status_history": [
    {
      "from": "",
      "to": "Aangemeld",
      "event": "SUBMIT",
      "at": "2026-07-28T15:35:00Z",
      "by": "applicant@example.com"
    }
  ]
}
```

## Email Side Effects on SUBMIT

| Side Effect                 | Template                                    | Recipient                 |
| --------------------------- | ------------------------------------------- | ------------------------- |
| `send_application_received` | `membership-application-confirmation`       | Applicant                 |
| `notify_admin`              | `membership-application-admin-notification` | webmaster@h-dcn.nl        |
| `audit_log`                 | —                                           | CloudWatch structured log |

## Authorization Summary

| Actor                     | Allowed Transitions             |
| ------------------------- | ------------------------------- |
| `verzoek_lid` (self only) | SUBMIT (own record, from draft) |
| `Members_Status_Approve`  | APPROVE (any record)            |
| `Members_CRUD`            | All transitions (any record)    |

## Existing Patterns Used

- **Workflow engine:** Same pattern as APPROVE/PAYMENT_RECEIVED — engine evaluates, dispatcher runs actions + side effects
- **Email side effects:** Reuses existing `send_membership_email()` with templates already deployed to S3
- **Number generator:** Not involved (lidnummer assigned only at PAYMENT_RECEIVED → Actief)
- **Status history:** Same append pattern as existing transitions

## Files Modified

| File                                                              | Change                                                      |
| ----------------------------------------------------------------- | ----------------------------------------------------------- |
| `backend/layers/auth-layer/python/shared/workflows/states.py`     | Add `DRAFT = 'draft'` to MemberState                        |
| `backend/layers/auth-layer/python/shared/workflows/membership.py` | Add SUBMIT transition (draft → applied)                     |
| `backend/handler/transition_member/app.py`                        | Allow verzoek_lid for SUBMIT + handle empty status as draft |
| `backend/handler/get_member_self/app.py`                          | Remove hardcoded status on POST; lock PUT after submission  |
| `frontend/src/pages/MyAccount.tsx`                                | Add submit button logic + read-only mode detection          |
| `frontend/src/config/workflows/membershipWorkflow.ts`             | Add draft state + SUBMIT transition                         |
| `backend/tests/unit/test_workflow_engine.py`                      | Add tests for draft→applied SUBMIT                          |
| `backend/tests/unit/test_transition_member.py`                    | Add test for verzoek_lid self-submit                        |

## Out of Scope

- Required field validation before SUBMIT (frontend-only, not enforced by backend guard)
- Editing after submission (admin function, not self-service)
- PresMeet module changes
- Changes to existing APPROVE/PAYMENT_RECEIVED transitions
