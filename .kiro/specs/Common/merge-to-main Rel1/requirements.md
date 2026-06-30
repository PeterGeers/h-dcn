# Requirements Document

## Introduction

Plan to merge the `feature/generic-event-booking` branch into `main` using a squash-and-merge strategy via a GitHub Pull Request. The merge includes running a DynamoDB data migration (price fields to Number type) against production tables, followed by automatic production deployment via path-filtered GitHub Actions workflows. The feature branch is deleted after successful merge.

## Glossary

- **Merge_Process**: The end-to-end workflow of creating a PR, running migrations, merging the branch, and verifying deployment
- **PR**: A GitHub Pull Request created via `gh pr create` targeting the `main` branch
- **Migration_Script**: The Python script at `scripts/migrate_price_fields_to_number.py` that converts string-typed price fields to DynamoDB Number type
- **CI_Pipeline**: The GitHub Actions workflows (`deploy-backend.yml`, `deploy-frontend.yml`) triggered on push to `main`
- **GitGuardian**: Secret scanning tool that runs as part of CI to detect leaked credentials
- **Feature_Branch**: The Git branch `feature/generic-event-booking` containing the changes to be merged

## Requirements

### Requirement 1: Pull Request Creation

**User Story:** As a developer, I want to create a squash-merge PR from the feature branch to main, so that the commit history on main stays clean.

#### Acceptance Criteria

1. WHEN the Merge_Process starts, THE Merge_Process SHALL create a PR from `feature/generic-event-booking` targeting `main` using `gh pr create`
2. THE PR SHALL use the squash-and-merge strategy to combine all feature branch commits into a single commit on main
3. THE PR SHALL include a descriptive title summarizing the generic event booking feature
4. THE PR SHALL include a description listing the key changes, migration steps, and deployment notes

### Requirement 2: Pre-Merge Validation

**User Story:** As a developer, I want CI checks to pass before merging, so that broken code does not reach production.

#### Acceptance Criteria

1. WHEN the PR is created, THE CI_Pipeline SHALL run GitGuardian secret scanning on the commit range
2. WHILE the PR is open, THE Merge_Process SHALL wait for all required CI checks to pass before merging
3. IF a CI check fails, THEN THE Merge_Process SHALL halt and report the failure for manual resolution

### Requirement 3: Data Migration Execution

**User Story:** As a developer, I want to run the price field migration against production DynamoDB tables, so that financial fields are stored as the correct Number type.

#### Acceptance Criteria

1. WHEN CI checks pass and before the PR is merged, THE Merge_Process SHALL execute the Migration_Script with `--dry-run` flag and `--profile nonprofit-deploy` to preview changes
2. WHEN the dry-run completes without errors, THE Merge_Process SHALL execute the Migration_Script with `--profile nonprofit-deploy` (without `--dry-run`) to apply changes
3. IF the Migration_Script encounters an error during dry-run, THEN THE Merge_Process SHALL halt and report the error for manual resolution
4. IF the Migration_Script encounters an error during actual execution, THEN THE Merge_Process SHALL halt and report the error for manual resolution
5. THE Migration_Script SHALL be run from the repository root as `python scripts/migrate_price_fields_to_number.py`

### Requirement 4: Merge Execution

**User Story:** As a developer, I want the PR to be squash-merged after validations pass, so that the feature lands on main as a single clean commit.

#### Acceptance Criteria

1. WHEN the Migration_Script completes successfully, THE Merge_Process SHALL squash-merge the PR using `gh pr merge --squash`
2. THE Merge_Process SHALL use the `--delete-branch` flag to remove `feature/generic-event-booking` after merge
3. WHEN the merge is complete, THE Feature_Branch SHALL no longer exist on the remote

### Requirement 5: Production Deployment

**User Story:** As a developer, I want production deployment to trigger automatically after merge, so that the new code is live without manual intervention.

#### Acceptance Criteria

1. WHEN the squash-merge commit lands on `main` with changes under `backend/`, THE CI_Pipeline SHALL automatically trigger `deploy-backend.yml`
2. WHEN the squash-merge commit lands on `main` with changes under `frontend/`, THE CI_Pipeline SHALL automatically trigger `deploy-frontend.yml`
3. THE `deploy-backend.yml` workflow SHALL run SAM build and deploy to the `h-dcn` CloudFormation stack in `eu-west-1`
4. THE `deploy-frontend.yml` workflow SHALL run `npm run build`, sync to S3, and invalidate CloudFront
5. WHILE deployment is in progress, THE CI_Pipeline SHALL block concurrent deployments via the concurrency group setting

### Requirement 6: Post-Merge Verification

**User Story:** As a developer, I want to verify that deployments completed successfully, so that I can confirm the feature is live.

#### Acceptance Criteria

1. WHEN both deployment workflows complete, THE Merge_Process SHALL verify that both `deploy-backend` and `deploy-frontend` workflow runs succeeded
2. IF a deployment workflow fails, THEN THE Merge_Process SHALL report the failure for manual investigation
3. WHEN all deployments succeed, THE Merge_Process SHALL confirm that `feature/generic-event-booking` has been deleted from the remote
