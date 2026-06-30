# Design Document: Merge to Main

## Overview

This document describes the step-by-step operational workflow for merging the `feature/generic-event-booking` branch into `main`. The process involves creating a PR, running a DynamoDB data migration, squash-merging, and verifying automatic production deployment.

This is a procedural workflow — no new application code is written. The "design" is the sequencing and decision logic of CLI commands.

## Workflow Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ 1. Create PR    │────▶│ 2. Wait for CI   │────▶│ 3. Run Migration  │
│    gh pr create │     │    (GitGuardian)  │     │    --dry-run      │
└─────────────────┘     └──────────────────┘     └───────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ 6. Verify       │◀────│ 5. Auto Deploy   │◀────│ 4. Squash-Merge   │
│    Deployments  │     │    (GH Actions)  │     │    + delete branch│
└─────────────────┘     └──────────────────┘     └───────────────────┘
```

Each step has a gate condition. If a gate fails, the process halts for manual resolution.

## Step-by-Step Procedure

### Step 1: Create Pull Request

**Gate:** Working directory is clean, feature branch is up-to-date with main.

```bash
# Ensure on correct branch
git checkout feature/generic-event-booking

# Create the PR targeting main
gh pr create \
  --base main \
  --title "feat: generic event booking with price field migration" \
  --body "## Changes
- Generic event booking system (replaces hardcoded event types)
- Price fields enforced as DynamoDB Number type (backend validation)
- Migration script for existing string-typed price data

## Migration
Run before merge:
\`\`\`
python scripts/migrate_price_fields_to_number.py --dry-run --profile nonprofit-deploy
python scripts/migrate_price_fields_to_number.py --profile nonprofit-deploy
\`\`\`

## Deployment
Automatic on merge to main (path-filtered GitHub Actions):
- backend/ changes → deploy-backend.yml (SAM build + deploy to h-dcn stack)
- frontend/ changes → deploy-frontend.yml (npm build + S3 sync + CloudFront invalidation)"
```

**Expected output:** URL of the created PR.

### Step 2: Wait for CI Checks

**Gate:** PR is created successfully (Step 1 returns PR URL).

The following checks run automatically when the PR is created:

- GitGuardian secret scan (commit range)
- Any other branch protection rules configured on the repository

```bash
# Monitor PR check status
gh pr checks --watch
```

**Decision point:**

- All checks pass → proceed to Step 3
- Any check fails → HALT, investigate and fix manually

### Step 3: Run Data Migration

**Gate:** All CI checks pass (Step 2).

The migration converts string-typed price fields to DynamoDB Number type in two tables:

- `Producten` table: `prijs` field
- `Orders` table: `items[].price` and `items[].unit_price` fields

#### Step 3a: Dry-run

```bash
# From repository root
python scripts/migrate_price_fields_to_number.py --dry-run --profile nonprofit-deploy
```

**Expected output:** Summary showing scanned/converted/skipped/errors counts for both tables. Exit code 0 if no parse errors.

**Decision point:**

- Exit code 0 and output looks correct → proceed to Step 3b
- Exit code 1 (parse errors) → HALT, investigate unparseable values
- Unexpected output → HALT, investigate

#### Step 3b: Apply migration

```bash
# From repository root (no --dry-run flag)
python scripts/migrate_price_fields_to_number.py --profile nonprofit-deploy
```

**Expected output:** Same summary as dry-run but with `[APPLIED]` mode. All DynamoDB writes executed.

**Decision point:**

- Exit code 0 → proceed to Step 4
- Exit code 1 or error → HALT, investigate (partial writes may have occurred — the script is idempotent so re-running is safe)

### Step 4: Squash-Merge the PR

**Gate:** Migration completed successfully (Step 3b exit code 0).

```bash
gh pr merge --squash --delete-branch
```

This command:

1. Squash-merges all feature branch commits into a single commit on `main`
2. Deletes `feature/generic-event-booking` from the remote

**Expected output:** Confirmation that PR was merged and branch deleted.

### Step 5: Automatic Deployment

**Gate:** Merge commit lands on `main` (Step 4).

No manual action required. GitHub Actions triggers automatically based on path filters:

| Changed path  | Workflow triggered    | What it does                                    |
| ------------- | --------------------- | ----------------------------------------------- |
| `backend/**`  | `deploy-backend.yml`  | SAM build → deploy to `h-dcn` stack (eu-west-1) |
| `frontend/**` | `deploy-frontend.yml` | npm build → S3 sync → CloudFront invalidation   |

Both workflows have concurrency groups (`backend-deploy`, `frontend-deploy`) that prevent overlapping runs.

### Step 6: Verify Deployments

**Gate:** Both deployment workflows are triggered (Step 5).

```bash
# List recent workflow runs
gh run list --limit 5

# Watch specific runs (use run IDs from above)
gh run watch <backend-run-id>
gh run watch <frontend-run-id>
```

**Verification checklist:**

- [ ] `deploy-backend` workflow succeeded
- [ ] `deploy-frontend` workflow succeeded
- [ ] Branch `feature/generic-event-booking` no longer exists on remote

```bash
# Confirm branch deletion
git ls-remote --heads origin feature/generic-event-booking
# Expected: empty output (no matching refs)
```

**Decision point:**

- Both workflows green and branch gone → DONE
- Any workflow failed → investigate via `gh run view <id> --log-failed`

## Error Handling

| Failure point                     | Impact                  | Recovery                                                     |
| --------------------------------- | ----------------------- | ------------------------------------------------------------ |
| CI check fails (Step 2)           | PR cannot merge         | Fix code, push, re-run checks                                |
| Migration dry-run fails (Step 3a) | No data modified        | Investigate unparseable values, fix script or data           |
| Migration apply fails (Step 3b)   | Partial writes possible | Script is idempotent — re-run is safe                        |
| Merge fails (Step 4)              | No changes to main      | Resolve merge conflicts, retry                               |
| Deployment fails (Step 5)         | Old code still live     | Check `gh run view --log-failed`, fix and re-deploy manually |

## Key Assumptions

1. The `nonprofit-deploy` AWS profile is configured locally and has permissions to read/write Producten and Orders tables
2. The `gh` CLI is authenticated and has permissions to create PRs, merge, and view workflow runs
3. The feature branch has no merge conflicts with `main`
4. Both `backend/` and `frontend/` directories have changes (both deploy workflows will trigger)

## Correctness Properties

_This is a procedural/operational workflow with no application code to write. All acceptance criteria are operational checks (SMOKE, INTEGRATION, or EXAMPLE type). There are no universal properties suitable for property-based testing._

**Rationale:** Property-based testing requires code with input/output behavior that varies meaningfully across inputs. This spec describes a fixed sequence of CLI commands and infrastructure verifications — each step either succeeds or fails as a one-shot operation. The appropriate verification approach is:

- **Smoke checks**: Verify each CLI command exits successfully (exit code 0)
- **Integration checks**: Verify GitHub Actions workflows trigger and complete
- **Manual observation**: Confirm PR title/description quality, deployment health

No correctness properties are defined for this spec.
