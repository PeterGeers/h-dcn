# Implementation Plan: Test Staging Environment

## Overview

This plan implements an isolated test/staging environment for the H-DCN member portal. The approach parameterizes the existing SAM template with a `Stage` parameter, updates CORS handling to use an environment variable, adds CI test gates, creates a local test runner, and provides a seed script for test data. All tasks build incrementally — infrastructure changes first, then CORS logic, then CI/tooling, then test data seeding.

## Tasks

- [x] 1. SAM template parameterization
  - [x] 1.1 Add Stage parameter, Mappings section, and CORS_ALLOWED_ORIGIN environment variable to `backend/template.yaml`
    - Add `Stage` parameter with AllowedValues `[prod, test]` and Default `prod`
    - Add `Mappings` section with `StageConfig` mapping for `prod` and `test` (CorsOrigin, OrganizationWebsite)
    - Add `CORS_ALLOWED_ORIGIN: !FindInMap [StageConfig, !Ref Stage, CorsOrigin]` to `Globals.Function.Environment.Variables`
    - Update `Globals.Api.Cors.AllowOrigin` to use `!FindInMap [StageConfig, !Ref Stage, CorsOrigin]`
    - Add CloudFormation Output `ApiUrl` exposing the API Gateway invoke URL
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.6, 5.3_

- [x] 2. CORS configuration update
  - [x] 2.1 Update `cors_headers()` in `backend/layers/auth-layer/python/shared/auth_utils.py` to read `CORS_ALLOWED_ORIGIN` from environment
    - Change `cors_headers()` to read `os.environ.get('CORS_ALLOWED_ORIGIN', '*')` for the `Access-Control-Allow-Origin` value
    - Preserve all other existing headers (Allow-Methods, Allow-Headers, Allow-Credentials)
    - Fallback to `*` when env var is not set (backward compatibility for local development)
    - _Requirements: 1.3, 1.4, 5.1, 5.5_

  - [x] 2.2 Write property test for CORS origin from environment variable
    - **Property 1: CORS origin from environment variable**
    - For any string value set in `CORS_ALLOWED_ORIGIN`, `cors_headers()` returns that exact value as `Access-Control-Allow-Origin`
    - Use Hypothesis `text()` strategy for env var values
    - Verify the function never reads or echoes a request-provided Origin header
    - **Validates: Requirements 1.3, 1.4, 5.1, 5.5**

  - [x] 2.3 Write unit tests for `cors_headers()` stage behavior
    - Test returns `https://testportal.h-dcn.nl` when env var is set to that value
    - Test returns `https://portal.h-dcn.nl` when env var is set to that value
    - Test returns `*` when env var is not set (default/backward compat)
    - _Requirements: 1.3, 1.4, 5.1, 5.5_

- [x] 3. Checkpoint - Verify CORS and template changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. CI pipeline test gates
  - [x] 4.1 Add test execution step to `.github/workflows/deploy-backend.yml`
    - After Python setup step, add step to install test dependencies (`pip install -r requirements.txt` if `tests/requirements.txt` exists)
    - Add `pytest tests/ --tb=short --junitxml=test-results.xml` step with 10-minute timeout
    - Place test step before SAM build step so failure blocks deployment
    - Output test summary to `$GITHUB_STEP_SUMMARY`
    - _Requirements: 3.1, 3.2, 3.5, 3.6_

  - [x] 4.2 Add test execution step to `.github/workflows/deploy-frontend.yml`
    - After `npm install`, add `npm test -- --watchAll=false --ci` step with 10-minute timeout
    - Place test step before the build step so failure blocks deployment
    - Output test summary to `$GITHUB_STEP_SUMMARY`
    - _Requirements: 3.3, 3.4, 3.5, 3.6_

- [x] 5. Local test runner script
  - [x] 5.1 Create `run-tests.ps1` at project root
    - Execute `pytest tests/ --tb=short` from `backend/` directory
    - Execute `npm test -- --watchAll=false` from `frontend/` directory
    - Always run both suites (capture exit codes, don't short-circuit on first failure)
    - Print summary table with suite name, result (passed/failed), and exit code
    - Exit 0 only if both suites pass
    - Support `-Coverage` switch: adds `--cov=handler --cov-report=term-missing` to backend, `--coverage` to frontend
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 5.2 Write property test for test runner exit code correctness
    - **Property 3: Local test runner exit code correctness**
    - For any pair of (backend_exit_code, frontend_exit_code) integers, the combined exit code is 0 iff both are 0
    - Extract the exit-code logic into a testable Python function and test with Hypothesis `integers()` strategy
    - **Validates: Requirements 4.5, 4.6**

- [x] 6. Checkpoint - Verify CI and local runner
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Test data seed script
  - [x] 7.1 Create `scripts/seed-test-data.py` with CLI structure and Cognito seeding logic
    - Implement argparse CLI with `--clear` flag and `--profile` option (default: `nonprofit-deploy`)
    - Implement `CognitoSeeder` class: create test users with admin-set-password, assign to groups, skip-if-exists
    - Hard-code all 5 test user configurations (username, email, groups) as defined in requirements
    - Use `boto3` with the specified AWS profile
    - Print summary of users created/skipped
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 7.2 Add DynamoDB seeding logic to `scripts/seed-test-data.py`
    - Implement `DynamoDBSeeder` class: put items to tables, support `--clear` (scan + batch delete)
    - Define deterministic seed data for all 9 Test_Tables with `SEED-{table}-{index}` partition keys
    - Each table gets ≥5 items with ≥2 distinct status values (where applicable)
    - All synthetic data uses `test-` or `SEED-` prefixes in identifiers
    - Handle missing tables gracefully (print error to stderr, skip, continue)
    - Handle `--clear` on non-existent tables (log warning, skip, continue)
    - Print summary listing each table name and items written/skipped
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [x] 7.3 Write property test for seed data determinism
    - **Property 2: Seed data determinism (idempotency)**
    - For any table's seed data config, calling the generation function multiple times produces identical item sets
    - **Validates: Requirements 6.3**

  - [x] 7.4 Write property test for seed data validity
    - **Property 4: Seed data validity**
    - For any generated seed item: all mandatory attributes present, IDs contain `SEED-` or `test-` prefix, ≥2 distinct statuses per table (where applicable)
    - **Validates: Requirements 6.1, 6.4**

  - [x] 7.5 Write property test for test user group configuration
    - **Property 5: Test user group configuration correctness**
    - For any test user in the seed config, group list matches exactly what requirements specify (no extra, no missing)
    - **Validates: Requirements 7.1**

- [x] 8. Update documentation
  - [x] 8.1 Update `docs/development/test-environment-setup.md` with test backend setup
    - Replace the outdated "Backend Configuration" section with the new Stage-parameterized approach (deploy command with `--parameter-overrides Stage=test`)
    - Add section documenting test stack deployment (`sam deploy --stack-name h-dcn-test ...`)
    - Add section documenting test data seeding (`python scripts/seed-test-data.py` with `--clear` flag)
    - Add section listing the 5 test user accounts and their roles
    - Document the local test runner (`run-tests.ps1`) usage and `-Coverage` switch
    - Document the `CORS_ALLOWED_ORIGIN` environment variable approach (replacing the hardcoded CORS example)
    - Update the "Daily Workflow" section to include backend test workflow (deploy test stack, seed data, verify)
    - Remove or update outdated `!If [IsProduction, ...]` CORS/WebAuthn examples that no longer match the implementation
    - _Requirements: 2.6_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- DynamoDB tables (`*-Test`) must be created manually before running seed script or deploying test stack
- The SAM template changes are minimal (Stage param, Mappings, one env var, one output) to keep the 2000+ line file manageable
- Deploy command for test stack uses explicit `--parameter-overrides` for all table names (not conditional defaults in template)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "5.1"] },
    { "id": 1, "tasks": ["2.1", "4.1", "4.2"] },
    { "id": 2, "tasks": ["2.2", "2.3", "5.2"] },
    { "id": 3, "tasks": ["7.1"] },
    { "id": 4, "tasks": ["7.2"] },
    { "id": 5, "tasks": ["7.3", "7.4", "7.5"] },
    { "id": 6, "tasks": ["8.1"] }
  ]
}
```
