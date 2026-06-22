# Implementation Plan: Merge to Main

## Overview

Operational workflow to merge `feature/generic-event-booking` into `main` via squash-merge PR, including DynamoDB price field migration, and verification of automatic production deployments. All tasks are CLI commands executed from the repository root.

## Tasks

- [ ] 1. Create Pull Request
  - [-] 1.1 Ensure working directory is clean and create PR
    - Checkout `feature/generic-event-booking` and create a PR targeting `main` using `gh pr create`
    - Use title: `feat: generic event booking with price field migration`
    - Include description with changes summary, migration steps, and deployment notes
    - Verify the command outputs a PR URL
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. Pre-merge validation
  - [~] 2.1 Wait for CI checks to pass
    - Run `gh pr checks --watch` to monitor all required checks (GitGuardian, branch protection rules)
    - Confirm all checks show as passed
    - If any check fails, halt and report the failure
    - _Requirements: 2.1, 2.2, 2.3_

- [~] 3. Checkpoint - CI validation
  - Ensure CI checks pass. Ask the user if questions arise.

- [ ] 4. Run data migration
  - [~] 4.1 Execute migration dry-run
    - Run: `python scripts/migrate_price_fields_to_number.py --dry-run --profile nonprofit-deploy`
    - Verify exit code 0 and review scanned/converted/skipped/errors counts for Producten and Orders tables
    - If exit code is non-zero or output shows parse errors, halt and report
    - _Requirements: 3.1, 3.3, 3.5_

  - [~] 4.2 Execute migration (apply)
    - Run: `python scripts/migrate_price_fields_to_number.py --profile nonprofit-deploy`
    - Verify exit code 0 and confirm `[APPLIED]` mode in output
    - If any error occurs, halt and report (script is idempotent, safe to re-run)
    - _Requirements: 3.2, 3.4, 3.5_

- [~] 5. Checkpoint - Migration complete
  - Ensure migration applied successfully. Ask the user if questions arise.

- [ ] 6. Squash-merge the PR
  - [~] 6.1 Execute squash-merge with branch deletion
    - Run: `gh pr merge --squash --delete-branch`
    - Verify confirmation that PR was merged and branch deleted
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 7. Verify deployments
  - [~] 7.1 Monitor deployment workflow runs
    - Run: `gh run list --limit 5` to identify triggered workflow runs
    - Watch both deploy-backend and deploy-frontend runs using `gh run watch <run-id>`
    - Confirm both workflows complete successfully
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2_

  - [~] 7.2 Confirm branch deletion
    - Run: `git ls-remote --heads origin feature/generic-event-booking`
    - Verify empty output (no matching refs), confirming branch is removed from remote
    - _Requirements: 4.3, 6.3_

- [~] 8. Final checkpoint - Merge complete
  - Ensure all deployments succeeded and branch is deleted. Ask the user if questions arise.

## Notes

- This is a procedural/operational workflow — no application code is written
- All commands use `--profile nonprofit-deploy` for AWS operations (account 506221081911)
- The `gh` CLI must be authenticated with permissions to create PRs, merge, and view workflow runs
- The migration script is idempotent — safe to re-run if interrupted
- Both `backend/` and `frontend/` have changes, so both deploy workflows will trigger
- Deployment workflows use concurrency groups to prevent overlapping runs
- If any step fails, the process halts for manual resolution before continuing

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["4.1"] },
    { "id": 3, "tasks": ["4.2"] },
    { "id": 4, "tasks": ["6.1"] },
    { "id": 5, "tasks": ["7.1", "7.2"] }
  ]
}
```
