# AWS Accounts Strategy

## Context & Decisions

- H-DCN has retrieved a non-profit account on AWS with a budget of $1K /yr
- There is reequirement for an improved pop-up webshop
- It would be nice if we can support a multi tenant structure for other motorclubs

### Questions & Answers

| Question                                      | Answer                                                                   |
| --------------------------------------------- | ------------------------------------------------------------------------ |
| Is this nonprofit version a separate product? | No — same features/branding                                              |
| Expected scale?                               | Still not clear                                                          |
| Stay with Flask + MySQL or go serverless?     | Already have Lambda/DynamoDB platform (h-dcn project). Not multi-tenant. |
| Applied for AWS nonprofit credits?            | Yes — $1K/year                                                           |

### Strategic Decision

**Three separate concerns, three separate paths:**

| #   | Concern                    | Action                                                    | Account   |
| --- | -------------------------- | --------------------------------------------------------- | --------- |
| 1   | h-dcn application          | Migrate from personal AWS account → nonprofit AWS account | Nonprofit |
| 2   | Webshop (product-approach) | Upgrade to new requirements + S3 support                  | Nonprofit |
| 3   | myAdmin                    | Leave as-is — no changes                                  | Personal  |

---

## Account Layout

```
┌─────────────────────────────────────┐
│  Personal AWS Account               │
│  ├── myAdmin (Flask + MySQL)        │
│  │   └── stays here, unchanged     │
│  └── h-dcn (Lambda + DynamoDB)      │
│       └── TO BE MIGRATED ──────────────┐
└─────────────────────────────────────┘   │
                                          ▼
┌─────────────────────────────────────┐
│  Nonprofit AWS Account ($1K/yr)     │
│  ├── h-dcn (migrated)              │
│  │   └── Lambda + DynamoDB         │
│  └── Webshop (upgraded)            │
│       └── Lambda + DynamoDB + S3   │
└─────────────────────────────────────┘
```

---

## IAM Users & Roles Structure

### Design Principles

- **No root account usage** — Root credentials locked away, MFA enabled, used only for billing/account-level changes
- **Human users in personal account only** — Single identity source, assume roles into nonprofit
- **Least privilege** — Scoped roles per concern (dev, deploy, admin)
- **Service roles separate from human roles** — Lambda/SAM get their own execution roles

### Personal Account (Identity Home)

```
Personal AWS Account (Identity Source)
│
├── IAM Users
│   ├── peter              ← Your daily driver (MFA enforced)
│   └── [future-dev]       ← If someone else joins
│
├── IAM Groups
│   ├── Developers
│   │   ├── Policy: AssumeNonprofitDevRole
│   │   ├── Policy: AssumeNonprofitAdminRole
│   │   └── Policy: PersonalAccountDev (myAdmin access)
│   └── Admins
│       └── Policy: AdministratorAccess (personal account only)
│
└── Service Roles (for myAdmin)
    ├── myAdmin-lambda-execution
    ├── myAdmin-cognito-role
    └── myAdmin-rds-access
```

### Nonprofit Account (Workload Account)

```
Nonprofit AWS Account (No human IAM users)
│
├── IAM Roles (assumed from personal account)
│   ├── NonprofitDevRole
│   │   ├── Trust: personal account
│   │   ├── Permissions: Read/write on DynamoDB, S3, Lambda, logs
│   │   └── Use: Daily development, debugging, testing
│   │
│   ├── NonprofitDeployRole
│   │   ├── Trust: personal account + GitHub Actions
│   │   ├── Permissions: CloudFormation, SAM deploy, IAM create roles
│   │   └── Use: CI/CD deployments
│   │
│   └── NonprofitAdminRole
│       ├── Trust: personal account (peter only)
│       ├── Permissions: AdministratorAccess
│       └── Use: Account setup, Cognito config, DNS, emergency fixes
│
└── Service Roles (created by SAM/IaC)
    ├── h-dcn-lambda-execution
    ├── h-dcn-cognito-triggers
    ├── h-dcn-api-gateway
    ├── webshop-lambda-execution
    ├── webshop-s3-access
    └── webshop-ses-sending
```

### Role Definitions

#### NonprofitDevRole (daily work)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:*",
        "s3:*",
        "lambda:Get*",
        "lambda:List*",
        "lambda:Invoke*",
        "logs:*",
        "cloudwatch:Get*",
        "cloudwatch:List*",
        "cloudwatch:Describe*",
        "apigateway:GET",
        "cognito-idp:List*",
        "cognito-idp:Describe*",
        "cognito-idp:AdminGet*"
      ],
      "Resource": "*"
    }
  ]
}
```

Trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<PERSONAL_ACCOUNT_ID>:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": { "aws:MultiFactorAuthPresent": "true" }
      }
    }
  ]
}
```

#### NonprofitDeployRole (CI/CD + manual deploys)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "lambda:*",
        "apigateway:*",
        "dynamodb:CreateTable",
        "dynamodb:UpdateTable",
        "dynamodb:DescribeTable",
        "s3:*",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:PassRole",
        "iam:GetRole",
        "iam:DeleteRole",
        "iam:DetachRolePolicy",
        "iam:DeleteRolePolicy",
        "cognito-idp:*",
        "cloudfront:*",
        "ssm:PutParameter",
        "ssm:GetParameter*",
        "ssm:DeleteParameter"
      ],
      "Resource": "*"
    }
  ]
}
```

Trust policy (allows both human and GitHub Actions):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<PERSONAL_ACCOUNT_ID>:root"
      },
      "Action": "sts:AssumeRole"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<NONPROFIT_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<GITHUB_ORG>/<REPO_NAME>:*"
        }
      }
    }
  ]
}
```

### AWS CLI Profiles

Add to `~/.aws/config`:

```ini
[profile personal]
region = eu-west-1
output = json

[profile nonprofit-dev]
role_arn = arn:aws:iam::<NONPROFIT_ACCOUNT_ID>:role/NonprofitDevRole
source_profile = personal
region = eu-west-1
mfa_serial = arn:aws:iam::<PERSONAL_ACCOUNT_ID>:mfa/peter

[profile nonprofit-deploy]
role_arn = arn:aws:iam::<NONPROFIT_ACCOUNT_ID>:role/NonprofitDeployRole
source_profile = personal
region = eu-west-1

[profile nonprofit-admin]
role_arn = arn:aws:iam::<NONPROFIT_ACCOUNT_ID>:role/NonprofitAdminRole
source_profile = personal
region = eu-west-1
mfa_serial = arn:aws:iam::<PERSONAL_ACCOUNT_ID>:mfa/peter
```

### Setup Order

1. **Personal account** — Enable MFA on root, create `peter` IAM user with MFA, create groups
2. **Nonprofit account** — Enable MFA on root, create the three roles (Admin, Deploy, Dev)
3. **Verify** — `aws sts get-caller-identity --profile nonprofit-dev`
4. **GitHub Actions** — Set up OIDC provider in nonprofit account for CI/CD
5. **Lock down** — Remove any existing access keys you don't need

---

## Phase 0: Connect Accounts (Implementation Steps)

This phase implements the IAM structure defined above. No AWS Organizations needed — nonprofit credits stay intact.

### Step 1: Secure Both Root Accounts

- [ ] Personal account: Enable MFA on root user
- [ ] Nonprofit account: Enable MFA on root user
- [ ] Store root credentials securely (password manager, not in code)

### Step 2: Set Up Personal Account (Identity Source)

- [ ] Create IAM user `peter` with console + programmatic access
- [ ] Enable MFA on `peter`
- [ ] Create `Developers` group with assume-role policies:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": [
        "arn:aws:iam::<NONPROFIT_ACCOUNT_ID>:role/NonprofitDevRole",
        "arn:aws:iam::<NONPROFIT_ACCOUNT_ID>:role/NonprofitDeployRole",
        "arn:aws:iam::<NONPROFIT_ACCOUNT_ID>:role/NonprofitAdminRole"
      ]
    }
  ]
}
```

- [ ] Add `peter` to `Developers` group

### Step 3: Set Up Nonprofit Account (Workload Account)

- [ ] Create `NonprofitAdminRole` (trust: personal account, MFA required)
- [ ] Create `NonprofitDeployRole` (trust: personal account + GitHub OIDC)
- [ ] Create `NonprofitDevRole` (trust: personal account, MFA required)
- [ ] Set up GitHub OIDC provider (for CI/CD later):

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  --profile nonprofit-admin
```

### Step 4: Configure Local AWS CLI

Update `~/.aws/config` with the profiles from the IAM structure section above (`personal`, `nonprofit-dev`, `nonprofit-deploy`, `nonprofit-admin`).

Update `~/.aws/credentials`:

```ini
[personal]
aws_access_key_id = <PETER_ACCESS_KEY>
aws_secret_access_key = <PETER_SECRET_KEY>
```

### Step 5: Verify All Profiles

```bash
# Should show personal account
aws sts get-caller-identity --profile personal

# Should show nonprofit account + NonprofitDevRole (will prompt for MFA)
aws sts get-caller-identity --profile nonprofit-dev

# Should show nonprofit account + NonprofitDeployRole
aws sts get-caller-identity --profile nonprofit-deploy

# Should show nonprofit account + NonprofitAdminRole (will prompt for MFA)
aws sts get-caller-identity --profile nonprofit-admin
```

### Step 6: Configure SAM for Nonprofit Deployments

Add a `nonprofit` config environment to `samconfig.toml`:

```toml
[nonprofit.deploy.parameters]
stack_name = "h-dcn"
region = "eu-west-1"
profile = "nonprofit-deploy"
confirm_changeset = true
capabilities = "CAPABILITY_IAM CAPABILITY_NAMED_IAM"
```

Deploy with:

```bash
sam deploy --config-env nonprofit
```

### Step 7: Enable CloudTrail

- [ ] Enable CloudTrail in nonprofit account (audit all cross-account actions)
- [ ] Set up billing alerts ($50/month threshold as early warning)

---

## Phase 1: Migrate h-dcn to Nonprofit Account

### What Needs to Move

| Resource Type            | Migration Approach                            |
| ------------------------ | --------------------------------------------- |
| Lambda functions         | Re-deploy via IaC (SAM/CDK/Terraform)         |
| DynamoDB tables          | Export → S3 → Import (or AWS Backup)          |
| API Gateway              | Re-create (not transferable between accounts) |
| Cognito user pool        | Re-create + migrate users (if any)            |
| S3 buckets               | Cross-account copy (`aws s3 sync`)            |
| IAM roles/policies       | Re-create in new account                      |
| CloudFront distributions | Re-create                                     |
| Route 53 / DNS           | Update to point to new resources              |
| Secrets / SSM parameters | Re-create in new account                      |
| CloudWatch logs/alarms   | Re-create                                     |

### Migration Steps

1. **Inventory** — Document all h-dcn resources in personal account (use AWS Resource Explorer or tag-based search)
2. **IaC audit** — Confirm h-dcn has complete IaC (SAM/CDK/Terraform). If not, reverse-engineer it first.
3. **Data export** — Export DynamoDB tables to S3, copy S3 assets cross-account
4. **Deploy to nonprofit** — Run IaC against the nonprofit account
5. **Data import** — Load DynamoDB data into new tables
6. **DNS cutover** — Point domain(s) to new account resources
7. **Verify** — End-to-end testing in new account
8. **Decommission** — Remove h-dcn resources from personal account

### Risks & Mitigations

| Risk                      | Mitigation                                                                           |
| ------------------------- | ------------------------------------------------------------------------------------ |
| Downtime during migration | Run both in parallel, DNS switch at the end                                          |
| Data loss                 | Export + verify row counts before decommission                                       |
| Hardcoded account IDs     | Search codebase for old account ID, replace                                          |
| Cross-account permissions | Use resource policies or assume-role during migration                                |
| Cognito user migration    | Export users, re-create with forced password reset (or use migration Lambda trigger) |

---

## Phase 2: Upgrade Webshop

### Current State

The webshop (documented in `product-approach.md`) defines:

- Product catalog with variants, rules, dependencies
- Order lifecycle (draft → submitted → paid → locked)
- Schema-driven forms
- Multi-tenancy via `tenant_id`

### Target State (on Nonprofit Account)

| Layer        | Technology                   | Notes                                   |
| ------------ | ---------------------------- | --------------------------------------- |
| Frontend     | React SPA on S3 + CloudFront | Same as product-approach design         |
| API          | API Gateway + Lambda         | Aligns with h-dcn pattern               |
| Database     | DynamoDB                     | Single-table design or table-per-entity |
| File storage | S3                           | Product media, order documents, uploads |
| Auth         | Cognito                      | Shared with h-dcn (same user pool)      |
| Email        | SES                          | Order confirmations, notifications      |

### Key Upgrades from product-approach.md

1. **S3 integration** — Product media, order attachments, pre-signed uploads (Section 4 of product-approach)
2. **DynamoDB data model** — Translate the relational schema to DynamoDB access patterns
3. **Serverless backend** — Lambda handlers instead of Flask routes
4. **CloudFront CDN** — For both frontend hosting and media delivery

### DynamoDB Considerations

The product-approach doc uses a relational model (products, orders, order_lines, variants). For DynamoDB:

| Relational Pattern | DynamoDB Approach                                                               |
| ------------------ | ------------------------------------------------------------------------------- |
| Products table     | PK: `TENANT#<id>`, SK: `PRODUCT#<id>`                                           |
| Order + lines      | PK: `TENANT#<id>`, SK: `ORDER#<id>` with lines as nested list or separate items |
| Variants           | PK: `TENANT#<id>`, SK: `VARIANT#<product_id>#<variant_id>`                      |
| Product rules      | PK: `TENANT#<id>`, SK: `RULE#<product_id>#<rule_id>`                            |
| Queries by status  | GSI: `tenant_id-status-index`                                                   |

### S3 Bucket Structure (from product-approach.md)

```
s3://webshop-assets-{env}/
├── {tenant_id}/
│   ├── products/{product_id}/
│   │   ├── hero.jpg
│   │   ├── gallery/
│   │   └── variants/{variant-sku}.jpg
│   ├── orders/{order_id}/
│   │   ├── confirmation.pdf
│   │   └── attachments/
│   └── tmp/
│       └── {upload_id}/
```

---

## Phase 3: myAdmin — No Changes

myAdmin stays on the personal AWS account with its current architecture:

- Flask + MySQL (Docker)
- AWS Cognito (personal account pool)
- Google Drive integration
- No migration, no changes

---

## Budget Estimate (Nonprofit Account)

### Monthly Costs at Low Scale

| Service      | Estimated Cost | Notes                                         |
| ------------ | -------------- | --------------------------------------------- |
| Lambda       | $0             | Free tier: 1M requests/month                  |
| DynamoDB     | $0             | Free tier: 25 GB + 25 WCU/RCU                 |
| S3 (storage) | $0–2           | First 5 GB free, then $0.023/GB               |
| CloudFront   | $0             | First 1 TB/month free                         |
| API Gateway  | $0–3           | First 1M calls free, then $3.50/M             |
| Cognito      | $0             | First 50K MAU free                            |
| SES          | $0–1           | First 62K emails/month free (from EC2/Lambda) |
| **Total**    | **$0–6/month** | Well within $1K/year budget                   |

### When Costs Increase

- DynamoDB: > 25 GB storage or > 25 RCU/WCU sustained
- Lambda: > 1M requests or > 400K GB-seconds/month
- S3: Significant media storage (> 50 GB)
- CloudFront: > 1 TB transfer/month

At nonprofit scale, you'll likely stay within free tier for a long time.

---

## Open Questions

| #   | Question                                                                | Status |
| --- | ----------------------------------------------------------------------- | ------ |
| 1   | Does h-dcn have complete IaC, or is it manually provisioned?            | TBD    |
| 2   | Are there existing users in h-dcn's Cognito pool that need migration?   | TBD    |
| 3   | Should the webshop share h-dcn's Cognito user pool or have its own?     | TBD    |
| 4   | What domain(s) will be used for the nonprofit services?                 | TBD    |
| 5   | Is there any data in h-dcn DynamoDB tables that needs to be preserved?  | TBD    |
| 6   | What's the timeline priority — migrate h-dcn first, then build webshop? | TBD    |

---

## Recommendations

### Pre-Migration: AWS Management Foundations

Set these up in the nonprofit account **before** migrating workloads:

#### 1. Tagging Strategy

Apply consistent tags to all resources for cost tracking, ownership, and automation:

| Tag Key       | Example Values        | Purpose                       |
| ------------- | --------------------- | ----------------------------- |
| `Project`     | `h-dcn`, `webshop`    | Cost allocation per project   |
| `Environment` | `prod`, `dev`, `test` | Environment separation        |
| `ManagedBy`   | `sam`, `manual`       | Track IaC vs manual resources |
| `Owner`       | `peter`               | Accountability                |
| `CostCenter`  | `nonprofit`           | Billing reports               |

Enforce via SAM template globals:

```yaml
Globals:
  Function:
    Tags:
      Project: h-dcn
      Environment: !Ref Environment
      ManagedBy: sam
```

#### 2. Budget Alarms & Cost Controls

Set up **before** deploying anything to nonprofit account:

- [ ] AWS Budgets: Monthly budget of €80 (leaves headroom within $1K/year)
- [ ] Alert thresholds: 50%, 80%, 100% of budget
- [ ] Alert recipients: your email + SNS topic for automation
- [ ] Zero-spend alarm: alert if any service exceeds $0 unexpectedly (catches misconfigurations early)

```bash
aws budgets create-budget --profile nonprofit-admin \
  --account-id <NONPROFIT_ACCOUNT_ID> \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

#### 3. Secrets Management

Current state: `.secrets` and `.awsCredentials.json` in the repo (gitignored but risky).

Target state:

| Secret Type             | Store In                           | Access Via                           |
| ----------------------- | ---------------------------------- | ------------------------------------ |
| API keys (Mollie, etc.) | SSM Parameter Store (SecureString) | Lambda environment variables via SAM |
| Database credentials    | Secrets Manager                    | SDK call at runtime                  |
| Cognito app secrets     | SSM Parameter Store                | SAM `!Sub` references                |
| Google credentials      | Secrets Manager                    | SDK call at runtime                  |

Benefits:

- No secrets in code or environment files
- Automatic rotation (Secrets Manager)
- Audit trail via CloudTrail
- Cross-environment support (dev/prod parameter paths)

SSM path convention:

```
/h-dcn/{environment}/mollie/api-key
/h-dcn/{environment}/cognito/client-secret
/webshop/{environment}/ses/configuration-set
```

#### 4. Backup Strategy

Enable from day one in nonprofit account:

| Resource | Backup Method                                | RPO       | Cost                 |
| -------- | -------------------------------------------- | --------- | -------------------- |
| DynamoDB | Point-in-Time Recovery (PITR)                | 5 minutes | ~20% of storage cost |
| S3       | Versioning + Lifecycle rules                 | Immediate | Minimal              |
| Cognito  | No native backup — export users periodically | Daily     | Free                 |

Add to SAM template:

```yaml
MembersTable:
  Type: AWS::DynamoDB::Table
  Properties:
    PointInTimeRecoverySpecification:
      PointInTimeRecoveryEnabled: true
```

S3 lifecycle rule (clean up old versions after 30 days):

```yaml
WebshopBucket:
  Type: AWS::S3::Bucket
  Properties:
    VersioningConfiguration:
      Status: Enabled
    LifecycleConfiguration:
      Rules:
        - Id: CleanupOldVersions
          NoncurrentVersionExpiration:
            NoncurrentDays: 30
          Status: Enabled
```

#### 5. DNS Ownership Decision

| Option | Approach                                                  | Pros                                       | Cons                                |
| ------ | --------------------------------------------------------- | ------------------------------------------ | ----------------------------------- |
| A      | Route 53 in nonprofit account                             | Clean separation, all h-dcn infra together | Need to transfer/re-delegate domain |
| B      | Route 53 in personal account, cross-account delegation    | No domain transfer needed                  | Split management                    |
| C      | External DNS (e.g., Cloudflare) pointing to both accounts | Flexible, free tier                        | Another system to manage            |

**Recommendation:** Option A if you own the domain in Route 53 already. Transfer the hosted zone to nonprofit. If domain is registered elsewhere, Option C is simplest.

#### 6. Logging & Monitoring Baseline

Set up structured observability from the start:

- [ ] **Structured logging** — Use JSON logging in all Lambdas (you likely already do via `aws_lambda_powertools`)
- [ ] **X-Ray tracing** — Enable in SAM globals (free tier: 100K traces/month)
- [ ] **CloudWatch dashboard** — One per project (h-dcn, webshop) with key metrics
- [ ] **Error alerting** — CloudWatch Alarm on Lambda errors → SNS → email

SAM globals:

```yaml
Globals:
  Function:
    Tracing: Active
    Environment:
      Variables:
        LOG_LEVEL: INFO
        POWERTOOLS_SERVICE_NAME: h-dcn
```

#### 7. Environment Separation

Even within the nonprofit account, separate environments:

| Approach              | How                                      | When to Use                                   |
| --------------------- | ---------------------------------------- | --------------------------------------------- |
| Stack naming          | `h-dcn-dev`, `h-dcn-prod`                | Simple, low cost, good for small teams        |
| Separate AWS accounts | dev-account, prod-account                | Overkill for now, consider later              |
| Parameter-driven      | Single template, `Environment` parameter | Best balance — one template, multiple deploys |

**Recommendation:** Parameter-driven with stack naming:

```bash
# Dev deployment
sam deploy --config-env nonprofit --parameter-overrides Environment=dev

# Prod deployment
sam deploy --config-env nonprofit --parameter-overrides Environment=prod
```

This gives you separate DynamoDB tables (`h-dcn-members-dev`, `h-dcn-members-prod`), separate API endpoints, but shared account infrastructure.

---

### Migration Approach Refinements

- **Cognito migration Lambda trigger** is the cleanest path for user migration — users sign in once and get silently migrated to the new pool. No forced password resets needed. The project already has `cognito_post_authentication` and `cognito_pre_signup` handlers, so the pattern is familiar.
- **DynamoDB export/import via S3** (PITR export) is free and doesn't consume table capacity. Much better than scan-based approaches that eat into RCU.
- **AWS Organizations** — Consider linking the nonprofit account under a management account. This gives consolidated billing visibility and easier cross-account access (assume-role) during the migration window.

### Webshop DynamoDB Model Considerations

The single-table design with `TENANT#<id>` prefix works for multi-tenancy, but consider:

- **Separate tables per bounded context** (products, orders) rather than one mega-table. Benefits:
  - Easier to reason about and debug
  - Independent capacity settings per table
  - Independent backup/restore without affecting other entities
  - Cleaner IAM policies (Lambda functions only get access to the tables they need)
- **GSI planning** — You'll likely need more than just `tenant_id-status-index`. Common access patterns to plan for:
  - Get all orders for a member → GSI on `member_id`
  - Get products by category → GSI on `category`
  - Get orders by date range → GSI with sort key on `created_at`
  - Get pending payments → GSI on `payment_status`

### Answerable Open Questions (from codebase)

Several open questions can be answered by auditing the existing codebase:

| #   | Question                                              | How to Answer                                          |
| --- | ----------------------------------------------------- | ------------------------------------------------------ |
| 1   | Does h-dcn have complete IaC?                         | Audit `template.yaml` (SAM) against deployed resources |
| 2   | Are there existing users in Cognito?                  | Run `check_cognito_users.py` or check Cognito console  |
| 5   | Is there data in DynamoDB that needs to be preserved? | Check table item counts via AWS CLI or console         |

---

## Next Steps

1. **Inventory h-dcn resources** — List all AWS resources in personal account
2. **Verify IaC completeness** — Can h-dcn be fully deployed from code? (Audit `template.yaml` against deployed resources)
3. **Set up nonprofit account** — Organizations, IAM, billing alerts
4. **Execute Phase 1** — Migrate h-dcn
5. **Design DynamoDB model** — Translate product-approach schema for webshop
6. **Execute Phase 2** — Build/upgrade webshop on nonprofit account
