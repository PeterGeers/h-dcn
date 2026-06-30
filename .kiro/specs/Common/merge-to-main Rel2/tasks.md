# Implementation Plan: Merge to Main — Release 2

## Overview

Merge `feature/closed-community-booking` (148 commits) into `main` via squash-merge PR. This release includes:

- **Event system alignment** — unified pipeline, field registry compliance, sequential access checks
- **Closed community booking** — attendee-based flow with registry, delegates, constraints
- **i18n error messages** — error_key adoption across handlers
- **Webshop fix** — unified product pipeline via evt-webshop
- **Dashboard improvements** — admin card visibility, event card filtering
- **ggshield optimization** — local scanner for commits, API scan on push only
- **SAM template fixes** — missing env vars for WebshopSubmitOrderFunction

No DynamoDB data migrations needed for production (Events table migration is for test only; prod Events table uses legacy schema that will be migrated in a future release).

## Pre-merge checklist

- [ ] 0.1 All test findings verified in testportal
- [ ] 0.2 No known blocking bugs in the feature branch
- [ ] 0.3 Confirm prod Events table is unaffected (our changes only filter/read, don't write)
- [ ] 0.4 Confirm `evt-webshop` record exists in prod Events table (needed for webshop to work)
- [ ] 0.5 Confirm prod Members table has no dependency on new fields (`order_flow`, `allowed_membership_types`)

## Tasks

- [ ] 1. Verify production data readiness
  - [x] 1.1 Check if `evt-webshop` exists in prod Events table
    - Result: EXISTS but has 0 product_ids — needs population
  - [x] 1.2 Verify impact of `get_events` filter on prod data
    - Result: All 13 prod events have `status: 'active'` or null — filter would hide all for non-admins
    - Solution: Run migration script BEFORE merge (step 6)
  - [x] 1.3 Verify WebshopPage fallback behavior
    - Result: Code has fallback (shows all active products if no product_ids) — webshop won't break completely
    - But proper fix: populate evt-webshop product_ids

- [ ] 2. Checkpoint — Production readiness
  - Discuss findings from step 1 with user. Decide on migration strategy.

- [-] 3. Create Pull Request
  - [ ] 3.1 Ensure working directory is clean (commit or stash remaining changes)
  - [ ] 3.2 Create PR targeting `main`
    - `gh pr create --base main --head feature/closed-community-booking --title "feat: closed community booking + event system alignment (Rel2)" --body-file .kiro/specs/Common/merge-to-main\ Rel2/pr-description.md`
  - [ ] 3.3 Verify PR URL is returned

- [ ] 4. Pre-merge CI validation
  - [ ] 4.1 Wait for CI checks: `gh pr checks --watch`
  - [ ] 4.2 All checks pass (GitGuardian, branch protection)
  - [ ] 4.3 If any check fails, halt and report

- [ ] 5. Checkpoint — CI passed
  - Confirm all checks green. Ask user before proceeding.

- [ ] 6. Data migration (BEFORE merge)
  - [ ] 6.1 Migrate prod Events table to new schema
    - Dry-run: `python scripts/migrate_events_prod.py --profile nonprofit-deploy`
    - Review output: verify event_type derivation is correct for each event
    - Apply: `python scripts/migrate_events_prod.py --apply --profile nonprofit-deploy`
    - Adds: `name`, `status: 'published'`, `event_type`, `participation: 'open'`, `linked_regio`
  - [ ] 6.2 Populate `evt-webshop` product_ids in prod
    - Record exists but has 0 product_ids — webshop will show nothing without this
    - Script needed: scan Producten table for active parent products → set as product_ids on evt-webshop
    - Dry-run first, then apply
  - [ ] 6.3 Verify: re-run dry-run script → should show "0 would be updated, 13 skipped"

- [ ] 7. Squash-merge the PR
  - [ ] 7.1 Execute: `gh pr merge --squash --delete-branch`
  - [ ] 7.2 Verify PR merged and branch deleted

- [ ] 8. Verify deployments
  - [ ] 8.1 Monitor workflows: `gh run list --limit 5`
  - [ ] 8.2 Watch backend deploy: `gh run watch <run-id>`
  - [ ] 8.3 Watch frontend deploy: `gh run watch <run-id>`
  - [ ] 8.4 Both succeed

- [ ] 9. Post-merge verification
  - [ ] 9.1 Verify portal.h-dcn.nl loads correctly
  - [ ] 9.2 Verify webshop shows products
  - [ ] 9.3 Verify dashboard shows correct cards per role
  - [ ] 9.4 Confirm branch deleted: `git ls-remote --heads origin feature/closed-community-booking`

- [ ] 10. Final checkpoint — Release complete

## Key risks

| Risk                                                 | Mitigation                                                   |
| ---------------------------------------------------- | ------------------------------------------------------------ |
| Prod Events table uses `status: 'active'`            | Step 1.2: migrate or adjust filter                           |
| `evt-webshop` missing in prod                        | Step 1.1: create before merge                                |
| 148 commits = large diff                             | Squash-merge keeps main clean                                |
| WebshopPage change breaks prod webshop               | Fallback in code shows all active products if no evt-webshop |
| get_events filter hides all events for regular users | Only if prod events lack `status: 'published'`               |

## Notes

- This is a procedural/operational workflow — no application code is written
- All AWS operations use `--profile nonprofit-deploy` (account 506221081911)
- The `gh` CLI must be authenticated
- Both deploy workflows will trigger automatically on main push
- Step 1 is critical: production data must be compatible with the new code
