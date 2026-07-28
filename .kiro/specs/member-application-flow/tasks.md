# Implementation Tasks

## Task 1: Add draft state and SUBMIT transition to workflow engine

- [x] 1.1 Add `DRAFT = 'draft'` to `MemberState` enum in `backend/layers/auth-layer/python/shared/workflows/states.py`
- [x] 1.2 Add SUBMIT transition (`draft` → `applied`) to `MEMBERSHIP_TRANSITIONS` in `backend/layers/auth-layer/python/shared/workflows/membership.py` with side effects: `send_application_received`, `notify_admin`, `audit_log`
- [x] 1.3 Add unit test `test_draft_submit_goes_to_applied` in `backend/tests/unit/test_workflow_engine.py`
- [x] 1.4 Add unit test `test_draft_state_only_allows_submit` (other events from draft should fail)
- [x] 1.5 Run `pytest tests/unit/test_workflow_engine.py` — all tests pass

## Task 2: Allow verzoek_lid users to SUBMIT their own record

- [x] 2.1 Modify the auth check in `backend/handler/transition_member/app.py` to allow `verzoek_lid` users when `event == 'SUBMIT'` and the member_id matches their own Cognito `custom:member_id`
- [x] 2.2 Handle empty/missing status as `MemberState.DRAFT` in the status→state mapping (before the `STATUS_TO_STATE.get()` call)
- [x] 2.3 Add unit test in `backend/tests/unit/test_transition_member.py`: `test_submit_from_draft_by_verzoek_lid` — verifies SUBMIT succeeds for a record without status field
- [x] 2.4 Add unit test: `test_submit_blocked_for_wrong_member_id` — verifies 403 when verzoek_lid tries to submit someone else's record
- [x] 2.5 Add unit test: `test_submit_blocked_if_already_submitted` — verifies 400 when record already has a status
- [x] 2.6 Run `pytest tests/unit/test_transition_member.py` — all tests pass

## Task 3: Modify GetMemberSelf to support draft records

- [x] 3.1 In `backend/handler/get_member_self/app.py` → `create_own_member_data()`: remove the hardcoded `'status': 'Aangemeld'` line so the record is created without a status field
- [x] 3.2 In `update_own_member_data()`: add a guard that checks if the existing record has a `status` field. If yes, return 403 with message "Aanvraag is ingediend en kan niet meer worden gewijzigd"
- [x] 3.3 Verify existing tests still pass (if any exist for get_member_self)
- [x] 3.4 Run `pytest tests/unit/test_transition_member.py tests/unit/test_workflow_engine.py` — all pass

## Task 4: Update frontend — submit button and read-only mode

- [x] 4.1 In `frontend/src/pages/MyAccount.tsx`: detect when member record has no `status` (draft mode) vs has a `status` (read-only mode)
- [x] 4.2 In draft mode: show "Opslaan" button (saves via PUT) and "Aanvraag Indienen" button (saves + calls transition endpoint with SUBMIT)
- [x] 4.3 Before SUBMIT: show a confirmation dialog warning that the application cannot be edited after submission
- [x] 4.4 After successful SUBMIT: switch to read-only mode, show status badge ('Aangemeld')
- [x] 4.5 In read-only mode (status exists): show all fields as read-only with a status indicator, hide edit/submit buttons
- [x] 4.6 Handle transition errors: if SUBMIT fails, keep form editable and show error toast
- [x] 4.7 Run `npx tsc --noEmit` from frontend/ — no type errors

## Task 5: Update frontend workflow config

- [x] 5.1 Add `'draft'` to `MemberWorkflowState` type and `MEMBER_STATES` array in `frontend/src/config/workflows/membershipWorkflow.ts`
- [x] 5.2 Add `draftTransitions` with SUBMIT event config (actors: `['verzoek_lid']`, confirmMessage, description)
- [x] 5.3 Add `draft: { transitions: draftTransitions }` to `membershipWorkflow.states`
- [x] 5.4 Run `npx tsc --noEmit` from frontend/ — no type errors

## Task 6: Sync bulk handler and commit

- [x] 6.1 Copy updated `email_side_effects.py` (with webmaster@h-dcn.nl) to `backend/handler/bulk_transition_members/` if not already done
- [x] 6.2 Run `pytest tests/unit/test_workflow_engine.py tests/unit/test_transition_member.py` — all pass
- [x] 6.3 Run `npx tsc --noEmit` from frontend/ — no type errors
- [ ] 6.4 Commit all changes with message: `feat: member application submit flow via workflow engine`
- [ ] 6.5 Push and verify deploy succeeds
