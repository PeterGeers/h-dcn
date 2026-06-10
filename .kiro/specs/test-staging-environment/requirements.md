# Requirements Document

## Introduction

This feature establishes a complete test/staging environment for the H-DCN project. It provides an isolated backend stack (`h-dcn-test`) deployed to the same AWS nonprofit account, parameterized SAM templates to support both production and test stages, CI pipeline updates with explicit test execution gates, a local test runner script, and test data seeding for the isolated DynamoDB tables. The existing `testportal.h-dcn.nl` frontend connects to the new test backend API Gateway.

## Glossary

- **SAM_Template**: The AWS Serverless Application Model template at `backend/template.yaml` defining all Lambda functions, API Gateway, and related resources
- **Test_Stack**: The CloudFormation stack named `h-dcn-test` deployed to account 506221081911 (eu-west-1) with isolated table references
- **Production_Stack**: The existing CloudFormation stack named `h-dcn` serving `portal.h-dcn.nl`
- **CI_Pipeline**: The GitHub Actions workflows (`deploy-backend.yml`, `deploy-frontend.yml`) that build and deploy on push to main
- **Test_Tables**: DynamoDB tables suffixed with `-Test` (e.g., `Orders-Test`, `Counters-Test`, `Producten-Test`) managed externally, used exclusively by the Test_Stack
- **Local_Test_Runner**: A PowerShell script that executes both backend (pytest) and frontend (Jest) tests in a single command
- **Seed_Script**: A Python script that populates Test_Tables with representative test data
- **Test_API_Gateway**: The API Gateway stage deployed by the Test_Stack, serving as backend for `testportal.h-dcn.nl`
- **CORS_Origin**: The `Access-Control-Allow-Origin` header value controlling which frontends may call the API

## Requirements

### Requirement 1: SAM Template Parameterization for Multi-Stage Deployment

**User Story:** As a developer, I want the SAM template to support both production and test stages via parameter overrides, so that I can deploy isolated stacks without modifying the template itself.

#### Acceptance Criteria

1. THE SAM_Template SHALL accept a `Stage` parameter with allowed values `prod` and `test`, defaulting to `prod`
2. WHEN the Stage parameter is set to `test`, THE SAM_Template SHALL default all DynamoDB table name parameters (`Table`, `MembersTable`, `PaymentsTable`, `EventsTable`, `MembershipsTable`, `CartsTable`, `OrdersTable`, `CountersTable`, `StockMovementsTableName`) to their `-Test` suffixed variants (e.g., `Producten-Test`, `Members-Test`, `Payments-Test`, `Events-Test`, `Memberships-Test`, `Carts-Test`, `Orders-Test`, `Counters-Test`, `StockMovements-Test`)
3. WHEN the Stage parameter is set to `test`, THE SAM_Template SHALL set the CORS AllowOrigin to `https://testportal.h-dcn.nl`
4. WHEN the Stage parameter is set to `prod`, THE SAM_Template SHALL set the CORS AllowOrigin to `https://portal.h-dcn.nl`
5. WHEN the Stage parameter is set to `test`, THE SAM_Template SHALL set the `OrganizationWebsite` parameter default to `https://testportal.h-dcn.nl`
6. THE SAM_Template SHALL use the same `ExistingUserPoolId` (`eu-west-1_fcUkvwjH5`) and `ExistingUserPoolClientId` (`6jhvk853b0lfg9q1m861qs0cug`) for both stages because the Cognito pool is shared; dedicated test users (prefixed `test-`) in the shared pool have data only in Test_Tables
7. WHEN the Stage parameter is set to `test`, THE SAM_Template SHALL be deployable as a separate CloudFormation stack (e.g., `h-dcn-test`) so that test resources are isolated from the production stack `h-dcn`
8. IF the Stage parameter is set to `prod`, THEN THE SAM_Template SHALL retain the current default values for all DynamoDB table name parameters (without the `-Test` suffix)

### Requirement 2: Test Stack Deployment

**User Story:** As a developer, I want a separate CloudFormation stack `h-dcn-test` deployed to the nonprofit account, so that I can test backend changes without affecting production.

#### Acceptance Criteria

1. THE Test_Stack SHALL deploy to AWS account 506221081911 in region eu-west-1 with stack name `h-dcn-test`
2. THE Test_Stack SHALL reference only Test_Tables and not Production_Stack table names
3. THE Test_Stack SHALL create its own API Gateway REST API resource independent from the Production_Stack API Gateway
4. THE Test_Stack SHALL share the existing Cognito User Pool (`eu-west-1_fcUkvwjH5`) with the Production_Stack
5. THE Test_Stack SHALL use the same IAM deploy role (`NonprofitDeployRole`) as the Production_Stack for deployment
6. A deployment script or documented command SHALL exist that deploys the Test_Stack with `--stack-name h-dcn-test --parameter-overrides Stage=test`

### Requirement 3: CI Pipeline Test Execution Gate

**User Story:** As a developer, I want the CI pipeline to run automated tests before deploying, so that broken code is not deployed to production or test environments.

#### Acceptance Criteria

1. WHEN a push to main or a workflow_dispatch event triggers the backend workflow, THE CI_Pipeline SHALL install dependencies from `backend/requirements.txt`, and execute `pytest tests/ --tb=short` in the `backend/` working directory after the Python setup step and before the SAM build step
2. IF backend tests fail (pytest exits with a non-zero exit code), THEN THE CI_Pipeline SHALL terminate the workflow run with a failure status and not proceed to the SAM build or deploy steps
3. WHEN a push to main or a workflow_dispatch event triggers the frontend workflow, THE CI_Pipeline SHALL execute `npm test -- --watchAll=false --ci` in the `frontend/` working directory after dependency installation and before the build step
4. IF frontend tests fail (the test command exits with a non-zero exit code), THEN THE CI_Pipeline SHALL terminate the workflow run with a failure status and not proceed to the build or deploy steps
5. WHEN tests complete in either workflow, THE CI_Pipeline SHALL output a test summary to the GitHub Actions job summary containing the total number of tests run, the number passed, and the number failed
6. THE CI_Pipeline SHALL enforce a maximum timeout of 10 minutes for the test execution step in both backend and frontend workflows

### Requirement 4: Local Test Runner Script

**User Story:** As a developer, I want a single PowerShell script that runs both backend and frontend tests locally, so that I can verify all tests pass before pushing.

#### Acceptance Criteria

1. THE Local_Test_Runner SHALL execute backend tests using `pytest tests/ --tb=short` from the `backend/` directory
2. THE Local_Test_Runner SHALL execute frontend tests using `npm test -- --watchAll=false` from the `frontend/` directory
3. THE Local_Test_Runner SHALL always execute both test suites regardless of whether the first suite fails, so that the developer sees all failures in a single run
4. WHEN both test suites have completed, THE Local_Test_Runner SHALL print a summary listing each suite name (backend, frontend) with its result (passed or failed) and the exit code returned by each test command
5. IF either test suite fails, THEN THE Local_Test_Runner SHALL exit with a non-zero exit code
6. IF both test suites pass, THEN THE Local_Test_Runner SHALL exit with exit code 0
7. THE Local_Test_Runner SHALL accept an optional `-Coverage` switch that adds `--cov=handler --cov-report=term-missing` to the backend run and `--coverage` to the frontend run
8. THE Local_Test_Runner SHALL be located at the project root as `run-tests.ps1`

### Requirement 5: Test API Gateway Connection to Test Frontend

**User Story:** As a developer, I want the test backend API Gateway to serve requests from `testportal.h-dcn.nl`, so that the existing test frontend can call the test backend.

#### Acceptance Criteria

1. THE Test_API_Gateway SHALL return CORS headers (`Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`) allowing origin `https://testportal.h-dcn.nl` on all responses including OPTIONS preflight
2. THE Test_API_Gateway SHALL accept Bearer JWT access tokens issued by the shared Cognito pool (`eu-west-1_fcUkvwjH5`) in the `Authorization` header, identical to the Production_Stack API Gateway
3. WHEN the Test_Stack is deployed, THE Test_Stack CloudFormation outputs SHALL include an `ApiUrl` output containing the Test_API_Gateway invoke URL that can be configured as `REACT_APP_API_BASE_URL` for the test frontend build
4. THE Test_API_Gateway SHALL support the same HTTP methods (GET, POST, PUT, DELETE, PATCH, OPTIONS) as the Production_Stack API Gateway
5. WHEN a request arrives with an `Origin` header other than `https://testportal.h-dcn.nl`, THE Test_API_Gateway Lambda handlers SHALL return CORS headers with `Access-Control-Allow-Origin` set to `https://testportal.h-dcn.nl` (not echoing the request origin)

### Requirement 7: Dedicated Test Users in Shared Cognito Pool

**User Story:** As a developer, I want dedicated test user accounts in the shared Cognito pool that only have corresponding data in Test_Tables, so that I can test authentication flows without affecting real members.

#### Acceptance Criteria

1. THE Seed_Script SHALL create the following Cognito users in the shared pool (`eu-west-1_fcUkvwjH5`) with `+test` alias email addresses to avoid collisions with existing production users:
   - `test-admin` (email: `webmaster+testadmin@h-dcn.nl`) — groups: `Products_CRUD`, `Products_Export`, `Products_Read`, `Webshop_Management`, `Members_Read`, `Members_CRUD`, `Members_Export`, `Members_Status_Approve`, `System_CRUD`, `System_Logs_Read`, `System_User_Management`, `Communication_CRUD`, `Communication_Read`, `Communication_Export`, `Events_CRUD`, `Events_Read`, `Events_Export`, `Regio_All`, `Regio_Pressmeet`, `hdcnLeden`
   - `test-lid` (email: `peter+testlid@pgeers.nl`) — groups: `hdcnLeden`, `Regio_Pressmeet`, `club_test_presmeet`
   - `test-treasurer` (email: `peter+testtreasurer@jabaki.nl`) — groups: `National_Treasurer`, `hdcnLeden`
   - `test-presmeet` (email: `pjageers+testpresmeet@gmail.com`) — groups: `Regio_Pressmeet`, `hdcnLeden`
   - `test-readonly` (email: `pjageers+testreadonly@gmail.com`) — groups: `Products_Read`, `hdcnLeden`
2. EACH test user SHALL have a corresponding Member record in the `Members-Test` table with matching `email` and `member_id` fields
3. THE test user passwords SHALL be set via the `--admin-set-password` flag to avoid email verification flow during seeding
4. THE test user email addresses SHALL be hard-coded in the seed script configuration (not generated from a pattern) since each maps to a real deliverable mailbox
5. IF a test user already exists in the Cognito pool, THEN THE Seed_Script SHALL skip creation for that user and log a message indicating it was skipped
6. THE Seed_Script SHALL NOT accept a `--base-email` parameter — email addresses are fixed per user in the script configuration
7. THE test users SHALL NOT have corresponding records in the production DynamoDB tables (Members, Orders, etc.) — their data exists only in Test_Tables
8. THE admin Cognito management UI (ledenadministratie) SHALL exclude users with a `test-` username prefix from the default user listing, so that test accounts do not clutter the production admin view

### Requirement 6: Test Data Seeding

**User Story:** As a developer, I want a script that seeds representative test data into the Test_Tables, so that I can test features against realistic data without using production data.

#### Acceptance Criteria

1. THE Seed_Script SHALL populate each Test_Table (Members-Test, Producten-Test, Orders-Test, Payments-Test, Events-Test, Memberships-Test, Carts-Test, Counters-Test, StockMovements-Test) with at least 5 items per table, covering at minimum 2 distinct status values per table where the table schema includes a status field
2. THE Seed_Script SHALL use the `nonprofit-deploy` AWS profile to write to the Test_Tables
3. THE Seed_Script SHALL use deterministic, hard-coded partition key values for each seeded item so that running the script multiple times overwrites existing items rather than creating duplicates
4. THE Seed_Script SHALL generate synthetic data that includes all mandatory attributes defined in the production schema for each table but uses fictional names, email addresses, and identifiers containing a `test-` or `SEED-` prefix
5. IF a Test_Table does not exist, THEN THE Seed_Script SHALL print an error message to stderr that includes the missing table name, skip that table, and continue seeding remaining tables
6. WHEN the `--clear` flag is provided, THE Seed_Script SHALL delete all existing items from each accessible Test_Table before seeding new data
7. THE Seed_Script SHALL be located at `scripts/seed-test-data.py`
8. WHEN seeding completes, THE Seed_Script SHALL print a summary to stdout listing each table name and the number of items written or skipped
9. IF the `--clear` flag is provided and a Test_Table does not exist, THEN THE Seed_Script SHALL log a warning for that table and continue processing the remaining tables
