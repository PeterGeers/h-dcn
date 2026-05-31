# Implementation Plan: Nonprofit Account Migration

## Overview

Migrate the h-dcn application from the personal AWS account (344561557829) to a nonprofit AWS account following a phased approach: IAM & Foundations → IaC Preparation → Deploy to Nonprofit → Data Migration → DNS Cutover → Verification → Decommission. Each phase gates the next with verification steps.

## Tasks

- [x] 1. IAM Cross-Account Setup and Foundations
  - [x] 1.1 Create IAM roles in the nonprofit account
    - Create NonprofitDevRole with trust policy allowing assumption from Personal_Account with MFA required
    - Attach permissions for DynamoDB, S3, Lambda, CloudWatch logs, API Gateway (read), Cognito (read)
    - Create NonprofitDeployRole with trust policy allowing assumption from Personal_Account and GitHub OIDC
    - Attach permissions for CloudFormation, Lambda, API Gateway, DynamoDB, S3, IAM, Cognito, CloudFront, SSM
    - Create NonprofitAdminRole with AdministratorAccess and MFA-required trust policy
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 1.2 Configure GitHub Actions OIDC Provider in nonprofit account
    - Create OIDC identity provider for `token.actions.githubusercontent.com`
    - Configure audience condition (`sts.amazonaws.com`)
    - Configure subject condition restricting to the specific GitHub repository
    - Add OIDC trust statement to NonprofitDeployRole
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 1.3 Configure Personal_Account IAM group and AssumeRole policies
    - Create or update "Developers" IAM group with policies allowing sts:AssumeRole on all three nonprofit roles
    - Verify "peter" user is in the "Developers" group
    - _Requirements: 2.3, 2.4_

  - [x] 1.4 Create AWS CLI profile configuration
    - Add `personal`, `nonprofit-dev`, `nonprofit-deploy`, `nonprofit-admin` profiles to `~/.aws/config`
    - Configure MFA serial for dev and admin profiles
    - Configure source_profile references
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 1.5 Create cross-account access verification script
    - Write a shell script that runs `aws sts get-caller-identity` for each profile
    - Verify correct account ID and role ARN are returned for each profile
    - _Requirements: 6.1, 6.2, 6.3, 5.5_

  - [x] 1.6 Set up budget alarms and cost controls
    - Create AWS Budget with €80/month threshold
    - Configure alert notifications at 50%, 80%, 100% thresholds
    - Configure zero-spend alarm for unexpected service charges
    - Set up SNS topic for budget alert notifications to administrator email
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 1.7 Enable CloudTrail audit logging
    - Enable CloudTrail in nonprofit account for all management events
    - Create dedicated S3 bucket for CloudTrail logs with retention policy
    - Verify cross-account role assumptions are logged
    - _Requirements: 20.1, 20.2, 20.3_

- [x] 2. Checkpoint - Verify IAM and Foundations
  - Ensure all cross-account access verification tests pass, ask the user if questions arise.
  - Verify budget alarms are configured and CloudTrail is logging.

- [x] 3. IaC Preparation - SAM Template Audit and Modifications
  - [x] 3.1 Audit SAM template against deployed resources
    - Compare template-defined resources against deployed resources in Personal_Account
    - Document gaps (resources deployed but not in template)
    - _Requirements: 12.1, 12.2_

  - [x] 3.2 Add DynamoDB table definitions to SAM template
    - Define all 7 tables (Producten, Members, Payments, Events, Memberships, Carts, Orders) with partition keys, sort keys, and GSIs
    - Enable PITR on all DynamoDB tables
    - Add capacity settings (on-demand or provisioned as appropriate)
    - _Requirements: 12.3, 10.1_

  - [x] 3.3 Add Cognito User Pool and Client to SAM template
    - Define Cognito User Pool with matching configuration to existing pool (eu-west-1_OAT3oPCIm)
    - Define App Client with OAuth flows and identity provider settings (Google Workspace SSO)
    - Add Migration Lambda Trigger configuration on the User Pool
    - _Requirements: 12.4, 16.1, 16.5_

  - [x] 3.4 Add S3 bucket definition to SAM template
    - Define S3 bucket with versioning enabled
    - Add lifecycle rules to expire non-current versions after 30 days
    - Configure appropriate access policies
    - _Requirements: 12.5, 10.2, 10.3_

  - [x] 3.5 Remove hardcoded account IDs and parameterize template
    - Replace all references to `344561557829` with `${AWS::AccountId}`
    - Replace hardcoded Cognito User Pool IDs with parameter references
    - Replace `my-hdcn-bucket` with `!Ref S3BucketName` parameter
    - Replace hardcoded Cognito domain with `!Sub` using `${AWS::AccountId}`
    - Use `!Sub` intrinsic functions for all ARNs referencing account ID
    - _Requirements: 17.1, 17.2, 17.3, 17.4_

  - [x] 3.6 Add resource tagging to SAM template Globals
    - Add Project, Environment, ManagedBy, Owner tags to Globals section
    - Ensure all resources inherit tags via Globals.Function.Tags
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 3.7 Configure monitoring and observability in SAM template
    - Enable X-Ray tracing on all Lambda functions via Globals
    - Set LOG_LEVEL=INFO and POWERTOOLS_SERVICE_NAME=h-dcn environment variables
    - Add CloudWatch Alarm resources for Lambda errors with SNS notification
    - Add CloudWatch Dashboard resource with key metrics
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 3.8 Migrate secrets to SSM Parameter Store references
    - Create SSM parameters following `/h-dcn/{environment}/{service}/{key-name}` convention
    - Create Secrets Manager entries for Google credentials
    - Update SAM template Lambda environment variables to reference SSM parameters
    - Remove plaintext secrets from samconfig.toml
    - Verify GitGuardian pre-commit hook is active
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 3.9 Add nonprofit config environment to samconfig.toml
    - Add `[nonprofit.deploy.parameters]` section with stack_name, region, profile, capabilities
    - Add parameter overrides for Environment variable
    - _Requirements: 13.1, 13.2, 13.3_

  - [x] 3.10 Validate SAM template
    - Run `sam validate` and fix any errors
    - Run `cfn-lint` and fix any errors
    - Verify all resources have required tags
    - Verify PITR enabled on all DynamoDB tables
    - Verify S3 versioning enabled with lifecycle rules

- [x] 4. Checkpoint - Verify IaC Preparation
  - Ensure SAM template validates successfully, ask the user if questions arise.
  - Verify no hardcoded account IDs remain (`grep -r "344561557829"` returns zero in source files).

- [x] 5. Deploy to Nonprofit Account
  - [x] 5.1 Deploy SAM stack to nonprofit account
    - Run `sam build` and `sam deploy --config-env nonprofit`
    - Verify CloudFormation stack creates successfully
    - Verify all resources are created with correct tags
    - _Requirements: 13.2_

  - [x] 5.2 Implement Cognito Migration Lambda Trigger
    - Write Lambda function that validates credentials against old pool via `AdminInitiateAuth`
    - Retrieve user attributes (email, name, custom attributes) from old pool
    - Retrieve group memberships (hdcnLeden, admin) via `AdminListGroupsForUser`
    - Return user data with `finalUserStatus: "CONFIRMED"` to skip verification
    - Implement post-confirmation trigger to add user to appropriate groups
    - Configure cross-account access for the Lambda to call the Personal_Account Cognito pool
    - _Requirements: 16.2, 16.3, 16.4_

  - [x] 5.3 Update frontend deployment workflow for OIDC
    - Update `deploy-frontend.yml` to use `aws-actions/configure-aws-credentials@v4` with OIDC
    - Configure `role-to-assume` to NonprofitDeployRole ARN
    - Add `id-token: write` and `contents: read` permissions
    - Update S3 sync target to nonprofit account bucket
    - Add CloudFront invalidation step with nonprofit distribution ID
    - _Requirements: 19.1, 19.2, 19.3, 19.4_

  - [x] 5.4 Update frontend hardcoded references
    - Replace hardcoded Cognito domain in `GoogleSignInButton.tsx` with environment variable
    - Replace hardcoded Cognito domain in `OAuthCallback.tsx` with environment variable
    - Replace hardcoded Cognito domain in `googleAuthService.ts` with environment variable
    - Update `scripts/config.sh` to use dynamic account ID via `aws sts get-caller-identity`
    - _Requirements: 17.1, 17.2_

  - [x] 5.5 Write deployment integration tests
    - Test API Gateway responds to health check from nonprofit deployment
    - Test Lambda functions can read/write DynamoDB tables in nonprofit account
    - Test Cognito authentication flow works with new pool
    - Test Migration Lambda Trigger migrates a test user successfully
    - Test frontend deploys via GitHub Actions OIDC without errors
    - _Requirements: 6.1, 6.2, 6.3, 16.3_

- [x] 6. Checkpoint - Verify Nonprofit Deployment
  - Ensure all deployment integration tests pass, ask the user if questions arise.
  - Verify CloudFront serves frontend assets correctly.

- [x] 7. Data Migration
  - [x] 7.1 Create DynamoDB data migration script
    - Write script to enable PITR on all source tables (if not already enabled)
    - Export each table using `aws dynamodb export-table-to-point-in-time` to S3
    - Copy exported data from Personal_Account S3 to Nonprofit_Account S3
    - Import data into nonprofit DynamoDB tables
    - _Requirements: 14.1, 14.2, 14.3_

  - [x] 7.2 Create data verification script
    - Write script to compare row counts for all 7 tables between source and destination
    - Implement halt-and-report logic if counts don't match
    - _Requirements: 14.4, 14.5_

  - [x] 7.3 Create S3 data migration script
    - Write script to run `aws s3 sync` from Personal_Account bucket to Nonprofit_Account bucket
    - Preserve object metadata and folder structure
    - Verify object counts match between source and destination
    - _Requirements: 15.1, 15.2, 15.3_

  - [x] 7.4 Execute data migration and verify
    - Run DynamoDB migration script for all 7 tables
    - Run S3 sync script
    - Run verification script to confirm all data migrated correctly
    - _Requirements: 14.4, 14.5, 15.3_

- [x] 8. Checkpoint - Verify Data Migration
  - Ensure all data verification scripts pass with matching row/object counts, ask the user if questions arise.

- [x] 9. DNS Cutover and Verification
  - [x] 9.1 Prepare DNS for cutover
    - Lower DNS TTL to 60 seconds in Squarespace (24h before cutover)
    - Document current DNS record values for rollback
    - _Requirements: 18.2, 18.3_

  - [x] 9.2 Create cutover verification script
    - Write script to verify end-to-end connectivity from frontend to nonprofit API
    - Include DNS resolution check pointing to nonprofit endpoints
    - Include user login flow test
    - Include data read/write test
    - _Requirements: 18.4_

  - [x] 9.3 Create rollback script
    - Write script to revert DNS records in Squarespace to Personal_Account endpoints
    - Ensure rollback can execute within 5 minutes
    - _Requirements: 18.5_

  - [x] 9.4 Execute DNS cutover
    - Update CNAME/A records in Squarespace to point to nonprofit CloudFront/API Gateway
    - Run cutover verification script
    - Monitor for 5 minutes for failures
    - If failures detected: execute rollback script
    - _Requirements: 18.1, 18.4, 18.5_

- [x] 10. Checkpoint - Verify DNS Cutover
  - Ensure end-to-end user flow works (login → view data → perform action), ask the user if questions arise.
  - Confirm DNS resolves to nonprofit endpoints.

- [x] 11. Decommissioning (after 7-day verification period)
  - [x] 11.1 Create decommissioning script
    - Write script to create final backup of all Personal_Account h-dcn data to S3 (90-day retention)
    - Include DynamoDB export for all 7 tables
    - Include S3 sync to backup bucket
    - _Requirements: 21.4_

  - [x] 11.2 Create resource cleanup script
    - Write script to delete h-dcn CloudFormation stack from Personal_Account
    - Include DynamoDB table deletion (after confirming data exists in nonprofit)
    - Include S3 bucket emptying and deletion
    - Include Cognito User Pool deletion (after confirming all users migrated)
    - Include orphaned resource cleanup (CloudWatch Log Groups, SSM Parameters, IAM roles, CloudWatch Alarms)
    - Explicitly exclude all myAdmin resources
    - _Requirements: 21.2, 21.3, 21.5_

  - [x] 11.3 Write decommissioning verification tests
    - Verify h-dcn CloudFormation stack is deleted from Personal_Account
    - Verify DynamoDB tables are removed from Personal_Account
    - Verify myAdmin resources remain unchanged in Personal_Account
    - Verify backup bucket exists with 90-day lifecycle
    - _Requirements: 21.1, 21.2, 21.3, 21.5_

- [x] 12. Final Checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - Confirm nonprofit account is sole host for h-dcn.
  - Confirm personal account retains only myAdmin and cross-account IAM configuration.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster execution
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation between phases
- DNS cutover includes 5-minute rollback capability via low-TTL records
- Decommissioning only begins after 7+ days of successful nonprofit operation
- Personal account myAdmin resources are never touched throughout this migration
- The Cognito Migration Lambda Trigger enables transparent user migration without password resets
- All scripts should use the `--profile` flag to target the correct account

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.6", "1.7"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4"] },
    { "id": 2, "tasks": ["1.5"] },
    { "id": 3, "tasks": ["3.1"] },
    { "id": 4, "tasks": ["3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8"] },
    { "id": 5, "tasks": ["3.9", "3.10"] },
    { "id": 6, "tasks": ["5.1"] },
    { "id": 7, "tasks": ["5.2", "5.3", "5.4"] },
    { "id": 8, "tasks": ["5.5"] },
    { "id": 9, "tasks": ["7.1", "7.3"] },
    { "id": 10, "tasks": ["7.2"] },
    { "id": 11, "tasks": ["7.4"] },
    { "id": 12, "tasks": ["9.1"] },
    { "id": 13, "tasks": ["9.2", "9.3"] },
    { "id": 14, "tasks": ["9.4"] },
    { "id": 15, "tasks": ["11.1"] },
    { "id": 16, "tasks": ["11.2"] },
    { "id": 17, "tasks": ["11.3"] }
  ]
}
```
