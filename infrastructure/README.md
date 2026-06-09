# Infrastructure Templates

CloudFormation templates deployed independently from the main SAM application stack.

> **Note:** Most templates target the nonprofit account (506221081911), but `personal-account-iam.yaml` targets the personal account (344561557829). Pay attention to the `--profile` used in each deploy command.

## AWS CLI Profiles

The file `aws-cli-profiles.ini` contains the named profiles needed to interact with both accounts. These must be manually added to your `~/.aws/config` file.

### Setup Instructions

1. Open your existing AWS CLI config file:
   - **Windows:** `%USERPROFILE%\.aws\config`
   - **macOS/Linux:** `~/.aws/config`

2. Append the contents of `infrastructure/aws-cli-profiles.ini` to the end of the file. Do **not** overwrite existing profiles — only add the new sections.

3. Ensure your `~/.aws/credentials` file has credentials for the `personal` profile:

   ```ini
   [personal]
   aws_access_key_id = YOUR_ACCESS_KEY
   aws_secret_access_key = YOUR_SECRET_KEY
   ```

4. Verify the profiles work:

   ```bash
   # Should return the personal account (344561557829)
   aws sts get-caller-identity --profile personal

   # Should return nonprofit account (506221081911) with NonprofitDevRole (prompts for MFA)
   aws sts get-caller-identity --profile nonprofit-dev

   # Should return nonprofit account (506221081911) with NonprofitDeployRole
   aws sts get-caller-identity --profile nonprofit-deploy

   # Should return nonprofit account (506221081911) with NonprofitAdminRole (prompts for MFA)
   aws sts get-caller-identity --profile nonprofit-admin
   ```

### Profile Summary

| Profile          | Account      | Role                | MFA Required | Use Case                   |
| ---------------- | ------------ | ------------------- | ------------ | -------------------------- |
| personal         | 344561557829 | (direct)            | No           | Base identity profile      |
| nonprofit-dev    | 506221081911 | NonprofitDevRole    | Yes          | Daily development          |
| nonprofit-deploy | 506221081911 | NonprofitDeployRole | No           | SAM deploy, CI/CD          |
| nonprofit-admin  | 506221081911 | NonprofitAdminRole  | Yes          | Account setup, emergencies |

### Notes

- The `nonprofit-dev` and `nonprofit-admin` profiles require MFA. The AWS CLI will prompt for your MFA token code when you use these profiles.
- The `nonprofit-deploy` profile does not require MFA — it's designed for CI/CD use and manual deployments where MFA is impractical.
- All cross-account profiles use `source_profile = personal`, meaning they derive credentials from the personal profile's access keys.

## Templates

### iam-roles.yaml

Defines IAM roles for cross-account access and CI/CD, plus the GitHub Actions OIDC provider.

**What it creates:**

- **GitHubOIDCProvider** — OIDC identity provider for `token.actions.githubusercontent.com` with audience `sts.amazonaws.com`, enabling GitHub Actions to assume roles without long-lived credentials
- **NonprofitDevRole** — Daily development role (DynamoDB, S3, Lambda, CloudWatch, API Gateway read, Cognito read). Requires MFA from personal account.
- **NonprofitDeployRole** — CI/CD deployment role (CloudFormation, Lambda, API Gateway, DynamoDB, S3, IAM, Cognito, CloudFront, SSM, Logs, X-Ray). Assumable from personal account or via GitHub OIDC.
- **NonprofitAdminRole** — Emergency admin role with AdministratorAccess. Requires MFA from personal account.

**Parameters:**

| Parameter         | Default      | Description                                              |
| ----------------- | ------------ | -------------------------------------------------------- |
| PersonalAccountId | 344561557829 | AWS Account ID of the personal account (identity source) |
| GitHubOrg         | PeterGeers   | GitHub organization or user name                         |
| GitHubRepo        | h-dcn        | GitHub repository name                                   |

**Deploy:**

```bash
aws cloudformation deploy \
  --template-file infrastructure/iam-roles.yaml \
  --stack-name h-dcn-iam-roles \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile nonprofit-admin \
  --region eu-west-1
```

**Verify OIDC Provider (Requirements 4.1, 4.2, 4.3):**

After deploying, verify the OIDC provider is correctly configured:

```bash
# 1. Verify the OIDC provider exists for token.actions.githubusercontent.com
aws iam list-open-id-connect-providers --profile nonprofit-admin

# 2. Verify OIDC provider details (audience restricted to sts.amazonaws.com)
OIDC_ARN=$(aws cloudformation describe-stacks \
  --stack-name h-dcn-iam-roles \
  --query "Stacks[0].Outputs[?OutputKey=='GitHubOIDCProviderArn'].OutputValue" \
  --output text \
  --profile nonprofit-admin)

aws iam get-open-id-connect-provider \
  --open-id-connect-provider-arn "$OIDC_ARN" \
  --profile nonprofit-admin
```

Expected output should show:

- `Url`: `token.actions.githubusercontent.com`
- `ClientIDList`: `["sts.amazonaws.com"]`
- Thumbprints present

**Verify NonprofitDeployRole trust policy includes OIDC:**

```bash
# 3. Verify the DeployRole trust policy has the OIDC statement
aws iam get-role \
  --role-name NonprofitDeployRole \
  --query "Role.AssumeRolePolicyDocument" \
  --profile nonprofit-admin
```

Expected trust policy should contain:

- `Action`: `sts:AssumeRoleWithWebIdentity`
- `Principal.Federated`: OIDC provider ARN for `token.actions.githubusercontent.com`
- `Condition.StringEquals["token.actions.githubusercontent.com:aud"]` = `sts.amazonaws.com`
- `Condition.StringLike["token.actions.githubusercontent.com:sub"]` = `repo:PeterGeers/h-dcn:*`

**Verify GitHub Actions can assume the role (from a workflow):**

```yaml
# In a GitHub Actions workflow:
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::506221081911:role/NonprofitDeployRole
      aws-region: eu-west-1
  - run: aws sts get-caller-identity
```

---

### cloudtrail.yaml

Enables CloudTrail audit logging for all management events in the nonprofit account.

**What it creates:**

- S3 bucket for CloudTrail logs with encryption (SSE-S3), public access blocked, and lifecycle rules (90 days → IA, 365 days expiration)
- Bucket policy allowing CloudTrail service to write logs
- Multi-region CloudTrail trail logging all management events (read + write) with log file validation

**Deploy:**

```bash
aws cloudformation deploy \
  --template-file infrastructure/cloudtrail.yaml \
  --stack-name h-dcn-cloudtrail \
  --profile nonprofit-admin \
  --region eu-west-1
```

**Verify cross-account role assumptions are logged:**

After deploying, assume a role and then check CloudTrail for the event:

```bash
# Assume a role (this creates a log entry)
aws sts get-caller-identity --profile nonprofit-dev

# Check CloudTrail for AssumeRole events (may take up to 15 minutes to appear)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
  --profile nonprofit-admin \
  --region eu-west-1
```

### personal-account-iam.yaml

Creates the "Developers" IAM group in the personal account with a policy allowing `sts:AssumeRole` on all three nonprofit roles. Adds the "peter" user to the group.

**Target account:** Personal (344561557829) — NOT the nonprofit account!

**What it creates:**

- IAM Group named "Developers"
- IAM Policy "AssumeNonprofitRoles" attached to the group, allowing `sts:AssumeRole` on:
  - `arn:aws:iam::506221081911:role/NonprofitDevRole`
  - `arn:aws:iam::506221081911:role/NonprofitDeployRole`
  - `arn:aws:iam::506221081911:role/NonprofitAdminRole`
- UserToGroupAddition that adds "peter" to the "Developers" group

**Deploy:**

```bash
aws cloudformation deploy \
  --template-file infrastructure/personal-account-iam.yaml \
  --stack-name h-dcn-personal-iam \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile personal \
  --region eu-west-1
```

**Verify:**

```bash
# Confirm peter is in the Developers group
aws iam get-group --group-name Developers --profile personal

# Confirm the AssumeRole policy is attached
aws iam list-group-policies --group-name Developers --profile personal
```

---

## DynamoDB Global Secondary Indexes (Managed Outside CloudFormation)

DynamoDB tables are managed outside CloudFormation. GSIs are added via standalone boto3 scripts.

### Orders Table — `event-club-index`

| Property   | Value                                 |
| ---------- | ------------------------------------- |
| Table      | Orders                                |
| GSI Name   | event-club-index                      |
| PK         | `event_id` (S)                        |
| SK         | `club_id` (S)                         |
| Projection | ALL                                   |
| Billing    | PAY_PER_REQUEST (inherits from table) |

**Purpose:** Enables efficient queries for:

- Finding an order by club_id + event_id (used by `presmeet_get_order`)
- Listing all orders for a given event (used by submit validation and reports)

**Script:** `backend/scripts/create_event_club_gsi.py`

**Usage:**

```bash
# Preview what would be created (no changes)
python backend/scripts/create_event_club_gsi.py --dry-run

# Create the GSI
python backend/scripts/create_event_club_gsi.py --profile nonprofit-deploy

# Check GSI status
python backend/scripts/create_event_club_gsi.py --status

# Create and wait until ACTIVE
python backend/scripts/create_event_club_gsi.py --wait
```

**Query patterns supported by this GSI:**

```python
# Find a specific club's order for an event
table.query(
    IndexName="event-club-index",
    KeyConditionExpression=Key("event_id").eq(event_id) & Key("club_id").eq(club_id)
)

# List all orders for an event
table.query(
    IndexName="event-club-index",
    KeyConditionExpression=Key("event_id").eq(event_id)
)
```

---

### budget-alarms.yaml

Configures AWS Budget with €80/month threshold and alert notifications.

**Target account:** Nonprofit (506221081911)

**Deploy:**

```bash
aws cloudformation deploy \
  --template-file infrastructure/budget-alarms.yaml \
  --stack-name h-dcn-budget-alarms \
  --profile nonprofit-admin \
  --region eu-west-1
```
