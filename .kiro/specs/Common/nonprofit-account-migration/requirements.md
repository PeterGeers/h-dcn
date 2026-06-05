# Requirements Document
_e1e4cb9033b9fe8a8bfe64f578c78d3d.portal.h-dcn.nl

## Introduction

This document defines the requirements for migrating the h-dcn application from a personal AWS account to a nonprofit AWS account with $1K/year in credits. The migration covers cross-account IAM setup, AWS management foundations (tagging, budgets, secrets, backups, monitoring), and the full migration of h-dcn infrastructure (Lambda, DynamoDB, API Gateway, Cognito, S3, CloudFront). The personal account retains myAdmin unchanged. The goal is to leverage nonprofit credits for cost-bearing services while maintaining zero downtime through parallel operation and DNS cutover.

## Glossary

- **Personal_Account**: The existing AWS account (ID: 344561557829) hosting both myAdmin and h-dcn today
- **Nonprofit_Account**: The new AWS nonprofit account with $1K/year credits where h-dcn will be migrated to
- **IAM_Role**: An AWS Identity and Access Management role that can be assumed by users or services to gain temporary permissions
- **Cross_Account_Access**: The ability for IAM users in the Personal_Account to assume roles in the Nonprofit_Account
- **SAM_Template**: The AWS Serverless Application Model template (template.yaml) that defines h-dcn infrastructure as code
- **NonprofitDevRole**: IAM role in the Nonprofit_Account for daily development tasks (read/write DynamoDB, S3, Lambda, logs)
- **NonprofitDeployRole**: IAM role in the Nonprofit_Account for CI/CD deployments (CloudFormation, SAM deploy, IAM)
- **NonprofitAdminRole**: IAM role in the Nonprofit_Account for account setup and emergency fixes (AdministratorAccess)
- **CLI_Profile**: A named AWS CLI configuration that specifies credentials, region, and role assumption settings
- **PITR**: Point-in-Time Recovery, a DynamoDB feature enabling continuous backups with 5-minute recovery granularity
- **OIDC_Provider**: OpenID Connect identity provider enabling GitHub Actions to assume roles without long-lived credentials
- **DNS_Cutover**: The process of updating DNS records to point from old account resources to new account resources
- **Migration_Lambda_Trigger**: A Cognito user migration Lambda that silently migrates users on first sign-in to the new user pool

## Requirements

### Requirement 1: Secure Root Accounts

**User Story:** As an account administrator, I want both AWS root accounts secured with MFA, so that unauthorized access to account-level settings is prevented.

#### Acceptance Criteria

1. THE Personal_Account SHALL have MFA enabled on the root user
2. THE Nonprofit_Account SHALL have MFA enabled on the root user
3. WHEN root credentials are stored, THE Administrator SHALL store root credentials in a password manager separate from the codebase

### Requirement 2: Personal Account Identity Source

**User Story:** As a developer, I want a dedicated IAM user in the personal account with MFA, so that I have a single identity source for accessing both accounts.

#### Acceptance Criteria

1. THE Personal_Account SHALL contain an IAM user named "peter" with console and programmatic access
2. THE Personal_Account SHALL enforce MFA on the "peter" IAM user
3. THE Personal_Account SHALL contain a "Developers" IAM group with policies allowing sts:AssumeRole on NonprofitDevRole, NonprofitDeployRole, and NonprofitAdminRole
4. WHEN the "peter" user is created, THE Personal_Account SHALL add the user to the "Developers" group

### Requirement 3: Nonprofit Account IAM Roles

**User Story:** As a developer, I want scoped IAM roles in the nonprofit account, so that I can perform daily development, deployments, and administration with least-privilege access.

#### Acceptance Criteria

1. THE Nonprofit_Account SHALL contain a NonprofitDevRole with read/write permissions for DynamoDB, S3, Lambda, CloudWatch logs, API Gateway (read), and Cognito (read)
2. THE Nonprofit_Account SHALL contain a NonprofitDeployRole with permissions for CloudFormation, Lambda, API Gateway, DynamoDB (create/update), S3, IAM role management, Cognito, CloudFront, and SSM Parameter Store
3. THE Nonprofit_Account SHALL contain a NonprofitAdminRole with AdministratorAccess permissions
4. THE NonprofitDevRole SHALL have a trust policy allowing assumption from the Personal_Account with MFA required
5. THE NonprofitDeployRole SHALL have a trust policy allowing assumption from the Personal_Account and from the GitHub Actions OIDC_Provider
6. THE NonprofitAdminRole SHALL have a trust policy allowing assumption from the Personal_Account with MFA required

### Requirement 4: GitHub Actions OIDC Integration

**User Story:** As a developer, I want GitHub Actions to authenticate with the nonprofit account via OIDC, so that CI/CD pipelines deploy without long-lived credentials.

#### Acceptance Criteria

1. THE Nonprofit_Account SHALL have an OIDC_Provider configured for token.actions.githubusercontent.com
2. THE OIDC_Provider SHALL restrict role assumption to the specific GitHub repository using a subject condition
3. WHEN a GitHub Actions workflow runs, THE NonprofitDeployRole SHALL be assumable via sts:AssumeRoleWithWebIdentity

### Requirement 5: AWS CLI Profile Configuration

**User Story:** As a developer, I want named CLI profiles for each role, so that I can switch between accounts and permission levels with a single --profile flag.

#### Acceptance Criteria

1. THE CLI configuration SHALL contain a "personal" profile pointing to the Personal_Account in eu-west-1
2. THE CLI configuration SHALL contain a "nonprofit-dev" profile that assumes NonprofitDevRole via the personal source profile with MFA
3. THE CLI configuration SHALL contain a "nonprofit-deploy" profile that assumes NonprofitDeployRole via the personal source profile
4. THE CLI configuration SHALL contain a "nonprofit-admin" profile that assumes NonprofitAdminRole via the personal source profile with MFA
5. WHEN a profile is used, THE AWS CLI SHALL return the correct account ID and role via sts:GetCallerIdentity

### Requirement 6: Cross-Account Access Verification

**User Story:** As a developer, I want to verify that all cross-account roles are assumable, so that I can confirm the IAM setup is correct before proceeding with migration.

#### Acceptance Criteria

1. WHEN the nonprofit-dev profile is used, THE AWS CLI SHALL successfully return the Nonprofit_Account ID and NonprofitDevRole ARN
2. WHEN the nonprofit-deploy profile is used, THE AWS CLI SHALL successfully return the Nonprofit_Account ID and NonprofitDeployRole ARN
3. WHEN the nonprofit-admin profile is used, THE AWS CLI SHALL successfully return the Nonprofit_Account ID and NonprofitAdminRole ARN

### Requirement 7: Resource Tagging Strategy

**User Story:** As an account administrator, I want consistent resource tags on all nonprofit account resources, so that costs can be tracked per project and environment.

#### Acceptance Criteria

1. THE SAM_Template SHALL apply the following tags to all resources: Project, Environment, ManagedBy, Owner
2. WHEN a resource is deployed to the Nonprofit_Account, THE resource SHALL have a "Project" tag with value "h-dcn"
3. WHEN a resource is deployed to the Nonprofit_Account, THE resource SHALL have an "Environment" tag matching the deployment environment parameter (dev, prod)
4. WHEN a resource is deployed to the Nonprofit_Account, THE resource SHALL have a "ManagedBy" tag with value "sam"

### Requirement 8: Budget Alarms and Cost Controls

**User Story:** As an account administrator, I want budget alarms in the nonprofit account, so that unexpected costs are detected before exceeding the $1K/year credit.

#### Acceptance Criteria

1. THE Nonprofit_Account SHALL have an AWS Budget configured with a monthly threshold of €80
2. THE Budget SHALL send alert notifications at 50%, 80%, and 100% of the monthly threshold
3. THE Budget SHALL send alerts to the administrator email address
4. WHEN any service incurs unexpected cost above $0, THE Budget SHALL trigger a zero-spend alarm notification

### Requirement 9: Secrets Management

**User Story:** As a developer, I want application secrets stored in AWS SSM Parameter Store and Secrets Manager, so that no secrets exist in the codebase or environment files.

**Existing Control:** GitGuardian is installed and active in this project (`.gitguardian.yaml` + `.cache_ggshield`), providing pre-commit and CI scanning for leaked secrets. This complements the migration to SSM/Secrets Manager by catching any accidental commits.

#### Acceptance Criteria

1. THE Nonprofit_Account SHALL store API keys (Mollie, etc.) in SSM Parameter Store as SecureString parameters
2. THE Nonprofit_Account SHALL store database credentials and Google credentials in AWS Secrets Manager
3. THE SAM_Template SHALL reference secrets via SSM parameter paths following the convention /h-dcn/{environment}/{service}/{key-name}
4. WHEN a Lambda function requires a secret, THE SAM_Template SHALL inject the secret via environment variable references to SSM parameters
5. IF a secret is found in the codebase or .secrets file, THEN THE Migration_Process SHALL move that secret to the appropriate parameter store before deployment
6. THE project SHALL retain GitGuardian pre-commit hooks as a defense-in-depth layer against accidental secret commits

### Requirement 10: Backup Strategy

**User Story:** As an account administrator, I want automated backups for all stateful resources, so that data can be recovered in case of accidental deletion or corruption.

#### Acceptance Criteria

1. THE SAM_Template SHALL enable Point-in-Time Recovery (PITR) on all DynamoDB tables in the Nonprofit_Account
2. THE SAM_Template SHALL enable versioning on all S3 buckets in the Nonprofit_Account
3. THE SAM_Template SHALL configure S3 lifecycle rules to expire non-current object versions after 30 days
4. WHEN Cognito users exist, THE Migration_Process SHALL export user data periodically as a backup mechanism

### Requirement 11: Monitoring and Observability Baseline

**User Story:** As a developer, I want structured logging, tracing, and error alerting from day one, so that issues in the nonprofit account are detected and diagnosable.

#### Acceptance Criteria

1. THE SAM_Template SHALL enable X-Ray tracing on all Lambda functions via the Globals section
2. THE SAM_Template SHALL set the LOG_LEVEL environment variable to INFO and POWERTOOLS_SERVICE_NAME to "h-dcn" on all Lambda functions
3. WHEN a Lambda function produces an error, THE Nonprofit_Account SHALL trigger a CloudWatch Alarm that sends a notification via SNS
4. THE Nonprofit_Account SHALL have a CloudWatch dashboard displaying key metrics for h-dcn (Lambda invocations, errors, DynamoDB consumed capacity, API Gateway 4xx/5xx)

### Requirement 12: SAM Template IaC Audit

**User Story:** As a developer, I want to verify that the SAM template fully describes all h-dcn resources, so that the nonprofit deployment is complete and no manual resources are missed.

#### Acceptance Criteria

1. WHEN the SAM_Template is audited, THE Audit SHALL compare template-defined resources against deployed resources in the Personal_Account
2. IF a deployed resource is not defined in the SAM_Template, THEN THE Audit SHALL document the gap and add the resource to the template
3. THE SAM_Template SHALL define all DynamoDB tables (Producten, Members, Payments, Events, Memberships, Carts, Orders) with their indexes and capacity settings
4. THE SAM_Template SHALL define the Cognito User Pool and Client configuration (currently referenced as existing resources)
5. THE SAM_Template SHALL define the S3 bucket (my-hdcn-bucket) with appropriate access policies

### Requirement 13: SAM Configuration for Nonprofit Deployment

**User Story:** As a developer, I want a SAM config environment for the nonprofit account, so that deployments target the correct account with a single command.

#### Acceptance Criteria

1. THE samconfig.toml SHALL contain a "nonprofit" config environment with stack_name "h-dcn", region "eu-west-1", profile "nonprofit-deploy", and capabilities "CAPABILITY_IAM CAPABILITY_NAMED_IAM"
2. WHEN "sam deploy --config-env nonprofit" is executed, THE SAM CLI SHALL deploy the stack to the Nonprofit_Account
3. THE samconfig.toml SHALL support parameter overrides for Environment (dev, prod) to enable environment separation within the Nonprofit_Account

### Requirement 14: DynamoDB Data Migration

**User Story:** As a developer, I want to migrate all DynamoDB table data from the personal account to the nonprofit account, so that existing application data is preserved.

#### Acceptance Criteria

1. WHEN data migration begins, THE Migration_Process SHALL export each DynamoDB table using PITR export to S3 (zero impact on table capacity)
2. THE Migration_Process SHALL copy exported data from the Personal_Account S3 to the Nonprofit_Account S3 using cross-account access
3. WHEN data is imported, THE Migration_Process SHALL import data into the corresponding Nonprofit_Account DynamoDB tables
4. THE Migration_Process SHALL verify row counts match between source and destination tables for all 7 tables (Producten, Members, Payments, Events, Memberships, Carts, Orders)
5. IF row counts do not match, THEN THE Migration_Process SHALL halt and report the discrepancy

### Requirement 15: S3 Data Migration

**User Story:** As a developer, I want to copy all S3 objects from the personal account bucket to the nonprofit account, so that uploaded files and analytics data are preserved.

#### Acceptance Criteria

1. THE Migration_Process SHALL copy all objects from s3://my-hdcn-bucket in the Personal_Account to the equivalent bucket in the Nonprofit_Account using aws s3 sync
2. THE Migration_Process SHALL preserve object metadata and folder structure during the copy
3. WHEN the copy completes, THE Migration_Process SHALL verify object counts match between source and destination

### Requirement 16: Cognito User Pool Migration

**User Story:** As a developer, I want to migrate Cognito users to the nonprofit account without forcing password resets, so that existing users experience no disruption.

#### Acceptance Criteria

1. THE Nonprofit_Account SHALL have a new Cognito User Pool with the same configuration as the existing pool (eu-west-1_OAT3oPCIm)
2. THE Nonprofit_Account SHALL configure a Migration_Lambda_Trigger on the new User Pool that authenticates users against the old pool on first sign-in
3. WHEN a user signs in to the new pool for the first time, THE Migration_Lambda_Trigger SHALL validate credentials against the Personal_Account pool and create the user in the new pool
4. WHEN a user is migrated, THE Migration_Lambda_Trigger SHALL preserve the user's group memberships (hdcnLeden, admin groups)
5. THE new Cognito User Pool SHALL have the same app client settings, OAuth flows, and identity provider configuration (Google Workspace SSO) as the existing pool

### Requirement 17: Hardcoded Account ID Removal

**User Story:** As a developer, I want all hardcoded account IDs removed from the codebase, so that the SAM template deploys correctly to any target account.

#### Acceptance Criteria

1. WHEN the codebase is searched, THE Migration_Process SHALL identify all references to the Personal_Account ID (344561557829)
2. THE SAM_Template SHALL replace hardcoded account IDs with dynamic references using ${AWS::AccountId}
3. THE SAM_Template SHALL replace hardcoded Cognito User Pool IDs with parameter references
4. IF a hardcoded ARN references the Personal_Account, THEN THE SAM_Template SHALL use Sub intrinsic functions with the AccountId pseudo-parameter

### Requirement 18: API Gateway and DNS Cutover

**User Story:** As a developer, I want to switch DNS from the personal account API to the nonprofit account API, so that the frontend seamlessly connects to the migrated backend.

**Context:** DNS is managed in Squarespace and remains there. No DNS provider migration is needed — only the record values change to point to nonprofit account endpoints.

#### Acceptance Criteria

1. WHEN the Nonprofit_Account deployment is verified, THE Migration_Process SHALL update DNS records in Squarespace to point to the new API Gateway endpoint
2. THE Migration_Process SHALL lower the DNS TTL to 60 seconds in Squarespace at least 24 hours before cutover
3. THE Migration_Process SHALL run both personal and nonprofit deployments in parallel during the migration window
4. WHEN DNS is updated, THE Migration_Process SHALL verify end-to-end connectivity from the frontend to the nonprofit API
5. IF end-to-end verification fails after DNS cutover, THEN THE Migration_Process SHALL revert DNS records in Squarespace to the Personal_Account API within 5 minutes

### Requirement 19: Frontend CI/CD Update

**User Story:** As a developer, I want the GitHub Actions frontend deployment workflow updated to use the nonprofit account, so that the frontend deploys to nonprofit-hosted CloudFront/S3.

#### Acceptance Criteria

1. THE GitHub Actions workflow (deploy-frontend.yml) SHALL use the NonprofitDeployRole via OIDC for authentication
2. THE GitHub Actions workflow SHALL deploy frontend assets to the Nonprofit_Account S3 bucket
3. THE GitHub Actions workflow SHALL invalidate the Nonprofit_Account CloudFront distribution after deployment
4. WHEN the workflow runs, THE deployment SHALL target the Nonprofit_Account without requiring long-lived AWS credentials in GitHub secrets

### Requirement 20: CloudTrail Audit Logging

**User Story:** As an account administrator, I want CloudTrail enabled in the nonprofit account, so that all API actions are auditable for security and compliance.

#### Acceptance Criteria

1. THE Nonprofit_Account SHALL have CloudTrail enabled to log all management events
2. THE CloudTrail logs SHALL be stored in a dedicated S3 bucket with appropriate retention policies
3. WHEN a cross-account role assumption occurs, THE CloudTrail SHALL record the source account, user, and assumed role

### Requirement 21: Personal Account Decommissioning

**User Story:** As a developer, I want h-dcn resources removed from the personal account after successful migration, so that costs stop accruing on the personal account.

#### Acceptance Criteria

1. WHEN end-to-end verification passes on the Nonprofit_Account for a minimum of 7 days, THE Migration_Process SHALL be eligible for decommissioning
2. WHEN decommissioning begins, THE Migration_Process SHALL delete the h-dcn CloudFormation stack from the Personal_Account
3. WHEN decommissioning begins, THE Migration_Process SHALL delete h-dcn DynamoDB tables from the Personal_Account after confirming data exists in the Nonprofit_Account
4. THE Migration_Process SHALL retain a final backup of all Personal_Account h-dcn data in S3 for 90 days before permanent deletion
5. THE Personal_Account SHALL retain all myAdmin resources unchanged throughout the migration and decommissioning process
