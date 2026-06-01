# AWS & DynamoDB Guidelines

## AWS Account Structure

- **Old account (344561557829)**: Legacy, contains old Cognito pools (`eu-west-1_OAT3oPCIm`, `eu-west-1_VtKQHhXGN`). Do NOT deploy here.
- **Nonprofit account (506221081911)**: Production. All infrastructure lives here.
  - Cognito pool: `eu-west-1_fcUkvwjH5` (H-DCN-Authentication-Pool)
  - App client: `6jhvk853b0lfg9q1m861qs0cug` (H-DCN-Web-Client)
  - Pool tier: PLUS (supports WebAuthn/passkeys)
  - Region: eu-west-1

## AWS CLI Profiles

- `default` / `personal`: Points to old account 344561557829. Do NOT use for deployments.
- `nonprofit-deploy`: Assumes `NonprofitDeployRole` in 506221081911. No MFA required. Use for all deployments and infrastructure changes.
- `nonprofit-dev`: Requires MFA. Use for interactive/admin work.
- `nonprofit-admin`: Requires MFA. Full admin access.

**Always use `--profile nonprofit-deploy`** for automated operations (SAM deploy, Cognito config, S3 operations).

## DynamoDB Conventions

### Tables (all in nonprofit account, eu-west-1)

| Table       | Key               | Description             |
| ----------- | ----------------- | ----------------------- |
| Members     | member_id (S)     | Club member profiles    |
| Producten   | product_id (S)    | Webshop products        |
| Payments    | payment_id (S)    | Stripe payment records  |
| Events      | event_id (S)      | Club events             |
| Memberships | membership_id (S) | Membership type records |
| Carts       | cart_id (S)       | Shopping carts          |
| Orders      | order_id (S)      | Webshop orders          |

### Access Patterns

- Tables are referenced via SAM template parameters (e.g., `!Ref MembersTable`)
- Lambda handlers get table names from environment variables (e.g., `MEMBERS_TABLE_NAME`)
- Use `boto3.resource('dynamodb')` + `Table(table_name)` pattern
- Scan operations should be avoided in production — use GSIs or query patterns where possible
- All tables use PAY_PER_REQUEST billing (on-demand)

### CRITICAL: DynamoDB Tables Are NOT in CloudFormation

DynamoDB tables, Cognito User Pool, and S3 data buckets are managed OUTSIDE the SAM template. They were created manually. **Never** add them as CloudFormation resources without `DeletionPolicy: Retain` — a previous deploy deleted production data this way.

## Cognito Configuration

- Pool `eu-west-1_fcUkvwjH5` is managed externally (not in SAM template)
- Lambda triggers are attached via SAM template events
- WebAuthn is configured with RP ID `h-dcn.nl` (covers portal.h-dcn.nl)
- Auth flows: ALLOW_USER_AUTH, ALLOW_REFRESH_TOKEN_AUTH, ALLOW_USER_SRP_AUTH, ALLOW_CUSTOM_AUTH
- Google SSO is configured as an identity provider

## SAM Template Rules

- `ExistingUserPoolId` default: `eu-west-1_fcUkvwjH5`
- `ExistingUserPoolClientId` default: `6jhvk853b0lfg9q1m861qs0cug`
- All Lambda functions that need Cognito access get `COGNITO_USER_POOL_ID` via Environment block
- Use `!Ref ExistingUserPoolId` in IAM policies, never hardcode pool IDs
- Deploy command: `sam deploy --stack-name h-dcn --region eu-west-1 --profile nonprofit-deploy --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --resolve-s3 --no-confirm-changeset`
