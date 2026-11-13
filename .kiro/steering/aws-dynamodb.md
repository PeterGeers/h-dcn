# AWS & DynamoDB Guidelines

## AWS Account Structure

> **Updated for the merged H-DCN + myAdmin platform.** As the two systems merge
> into one multi-tenant platform, identity is being reorganized into a dedicated,
> tenant-neutral account, while all shared infrastructure/data consolidates in the
> nonprofit account. The previous "personal = legacy, do NOT deploy" rule is
> **retired** — the personal account is being repurposed as the identity account.
> (H-DCN is still greenfield: the only real user is `webmaster@h-dcn.nl`, so
> re-enrolling users into the reorganized pool is trivial.)

- **Personal / identity account (344561557829)**: **Identity account.** Home of
  the reorganized Cognito user pool — the main access function for the whole
  platform, kept tenant-neutral so it can outlive any single tenant/org.
  - **Survivor pool: `eu-west-1_Hdp40eWmu` (`myAdmin`)** — currently powers the
    live myAdmin app; becomes the unified pool for the merged platform.
  - App client: **`<TBD — myAdmin app client / new H-DCN client>`**
  - Pool tier: verify PLUS (WebAuthn/passkeys) is enabled — required for the
    merged platform.
  - Region: eu-west-1
  - **Legacy pools in this account — decommission once the merged platform is
    live; do not build on them:**
    - `eu-west-1_OAT3oPCIm` (`H-DCN-Authentication-Pool`) — legacy; has old
      `webshop-backend-*` Lambda triggers.
    - `eu-west-1_VtKQHhXGN` (`Leden`) — legacy members pool.
- **Nonprofit account (506221081911)**: **Infrastructure & data account.** All
  generic AWS services live here: DynamoDB, S3, SES, SNS, Secrets Manager, SSM
  Parameters, CloudFront, API Gateway, Lambda. No Cognito user pool of record
  here after the reorg (Lambda triggers attach to the identity pool
  cross-account).
  - Region: eu-west-1
  - The former H-DCN pool `eu-west-1_fcUkvwjH5` here is **legacy** once identity
    consolidates on the survivor pool. H-DCN is greenfield (only real user
    `webmaster@h-dcn.nl`), so there are effectively no users to migrate —
    re-enrol into the survivor pool and decommission this one.
- **Railway (external, unchanged)**: hosts the myAdmin Flask backend + MySQL — the
  system of record for tenant management (`tenants`, `tenant_modules`,
  `user_tenant_roles`). Not an AWS account; noted here for completeness.

## AWS CLI Profiles

- `default` / `personal`: Points to the **identity account** (344561557829). Use
  for **Cognito / identity administration only** (pool + app client + triggers).
  No longer "do not use" — but it is not for general infrastructure.
- `nonprofit-deploy`: Assumes `NonprofitDeployRole` in 506221081911. No MFA
  required. Use for all deployments and infrastructure changes (DynamoDB, S3, SES,
  SNS, Secrets, Parameters, Lambda, API Gateway).
- `nonprofit-dev`: Requires MFA. Use for interactive/admin work.
- `nonprofit-admin`: Requires MFA. Full admin access.

**Rule of thumb:** `--profile nonprofit-deploy` for all generic infrastructure
operations; the identity-account profile only for Cognito/identity administration.

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

### Clearing Optional Fields (REMOVE pattern)

When a user empties an optional field (removes all items from a list, clears a map), the frontend MUST send `[]` or `null` — never `undefined`. The backend MUST use DynamoDB `REMOVE` for empty/null values instead of `SET`.

- `[]` or `null` → REMOVE attribute from DynamoDB
- `undefined` (key absent) → no action (field unchanged)
- Non-empty value → SET attribute

See: `docs/patterns/dynamodb-remove-pattern.md` for implementation examples.

**Applies to:** `order_item_fields`, `purchase_rules`, `variant_schema`, `images`, and any other optional list/map attributes.

## Cognito Configuration

> The survivor pool lives in the **identity account (344561557829)**, not
> nonprofit. The old nonprofit pool `eu-west-1_fcUkvwjH5` and the legacy personal
> pools (`OAT3oPCIm`, `VtKQHhXGN`) are all superseded by the survivor pool.

- Survivor pool `eu-west-1_Hdp40eWmu` (`myAdmin`) lives in the identity account,
  managed externally (not in the SAM template).
- **Unified multi-tenant claims:** the token carries `cognito:groups` (roles) and
  `custom:tenants` (tenant access). Both backends (H-DCN Lambdas and myAdmin Flask)
  read these identically and **verify the JWT signature** against the pool JWKS —
  never trust unverified headers.
- Lambda triggers are attached via SAM template events (cross-account to the
  identity pool).
- WebAuthn RP ID `h-dcn.nl` (covers portal.h-dcn.nl); PLUS tier required.
- Auth flows: ALLOW_USER_AUTH, ALLOW_REFRESH_TOKEN_AUTH, ALLOW_USER_SRP_AUTH, ALLOW_CUSTOM_AUTH
- Google SSO configured as an identity provider.

## SAM Template Rules

- `ExistingUserPoolId` default: **`eu-west-1_Hdp40eWmu`** (survivor pool in
  identity account; was `eu-west-1_fcUkvwjH5`)
- `ExistingUserPoolClientId` default: **`<TBD — app client for survivor pool>`**
  (was `6jhvk853b0lfg9q1m861qs0cug`)
- All Lambda functions that need Cognito access get `COGNITO_USER_POOL_ID` via
  Environment block
- Use `!Ref ExistingUserPoolId` in IAM policies, never hardcode pool IDs
- Deploy command: `sam deploy --stack-name h-dcn --region eu-west-1 --profile nonprofit-deploy --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --resolve-s3 --no-confirm-changeset`
