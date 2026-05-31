# SAM Template Audit Report

**Date:** 2025-01-20
**Template:** `backend/template.yaml`
**Purpose:** Compare template-defined resources against deployed resources in Personal_Account (344561557829)
**Validates:** Requirements 12.1, 12.2

---

## 1. Resources Defined in SAM Template

### Parameters (14 total)

| Parameter                | Default                        | Purpose                                 |
| ------------------------ | ------------------------------ | --------------------------------------- |
| ExistingUserPoolId       | eu-west-1_OAT3oPCIm            | References existing Cognito pool        |
| ExistingUserPoolClientId | 6unl8mg5tbv5r727vc39d847vn     | References existing Cognito client      |
| Environment              | dev                            | Environment name (dev/test/prod)        |
| Table                    | Producten                      | DynamoDB table name (products)          |
| Region                   | eu-west-1                      | AWS region                              |
| MembersTable             | Members                        | DynamoDB table name                     |
| PaymentsTable            | Payments                       | DynamoDB table name                     |
| EventsTable              | Events                         | DynamoDB table name                     |
| MembershipsTable         | Memberships                    | DynamoDB table name                     |
| CartsTable               | Carts                          | DynamoDB table name                     |
| OrdersTable              | Orders                         | DynamoDB table name                     |
| DefaultTempPassword      | TempPass123!                   | Default temp password for Cognito users |
| ForceUpdate              | 2025-12-28                     | Force deployment update                 |
| OrganizationName         | Harley-Davidson Club Nederland | Email template org name                 |
| OrganizationWebsite      | https://portal.h-dcn.nl        | Email template website URL              |
| OrganizationEmail        | webhulpje@h-dcn.nl             | Email template contact email            |
| OrganizationShortName    | H-DCN                          | Email template short name               |
| SupportPhoneNumber       | +31 (0)20 123 4567             | Support phone for recovery              |
| RecoveryPageUrl          | /recovery                      | Recovery page path                      |
| HelpPageUrl              | /help/passwordless-recovery    | Help page path                          |
| GoogleClientId           | (empty)                        | Google OAuth Client ID                  |
| GoogleClientSecret       | (empty)                        | Google OAuth Client Secret              |

### IAM Roles (3)

| Logical ID        | Type           | Purpose                                                |
| ----------------- | -------------- | ------------------------------------------------------ |
| DynamoDBRole      | AWS::IAM::Role | Lambda execution role for DynamoDB + S3 + Cognito read |
| CognitoLambdaRole | AWS::IAM::Role | Lambda execution role for Cognito triggers             |
| CognitoAdminRole  | AWS::IAM::Role | Lambda execution role for Cognito admin operations     |

### Lambda Functions (33)

| Logical ID                        | Handler Path                        | API Path                                               |
| --------------------------------- | ----------------------------------- | ------------------------------------------------------ |
| CognitoCustomMessageFunction      | handler/cognito_custom_message      | (Cognito trigger)                                      |
| CognitoPreSignUpFunction          | handler/cognito_pre_signup          | (Cognito trigger)                                      |
| CognitoPostConfirmationFunction   | handler/cognito_post_confirmation   | (Cognito trigger)                                      |
| CognitoPostAuthenticationFunction | handler/cognito_post_authentication | (Cognito trigger)                                      |
| InsertProductFunction             | handler/insert_product              | POST /insert-product/                                  |
| DeleteProductFunction             | handler/delete_product              | DELETE /delete-product/{id}                            |
| GetProductByIdFunction            | handler/get_product_byid            | GET /getproduct-byid/{id}                              |
| scanProductFunction               | handler/scan_product                | GET /scan-product/                                     |
| UpdateProductFunction             | handler/update_product              | PUT /update-product/{id}                               |
| CreateMemberFunction              | handler/create_member               | POST /members                                          |
| GetMembersFunction                | handler/get_members                 | GET /members                                           |
| GetMembersFilteredFunction        | handler/get_members_filtered        | GET /api/members                                       |
| GetMemberByIdFunction             | handler/get_member_byid             | GET /members/{id}                                      |
| GetMemberSelfFunction             | handler/get_member_self             | GET/PUT/POST /members/me                               |
| UpdateMemberFunction              | handler/update_member               | PUT /members/{id}                                      |
| DeleteMemberFunction              | handler/delete_member               | DELETE /members/{id}                                   |
| CreatePaymentFunction             | handler/create_payment              | POST /payments                                         |
| GetPaymentsFunction               | handler/get_payments                | GET /payments                                          |
| GetPaymentByIdFunction            | handler/get_payment_byid            | GET /payments/{payment_id}                             |
| UpdatePaymentFunction             | handler/update_payment              | PUT /payments/{payment_id}                             |
| DeletePaymentFunction             | handler/delete_payment              | DELETE /payments/{payment_id}                          |
| GetMemberPaymentsFunction         | handler/get_member_payments         | GET /payments/member/{member_id}                       |
| CreateEventFunction               | handler/create_event                | POST /events                                           |
| GetEventsFunction                 | handler/get_events                  | GET /events                                            |
| GetEventByIdFunction              | handler/get_event_byid              | GET /events/{event_id}                                 |
| UpdateEventFunction               | handler/update_event                | PUT /events/{event_id}                                 |
| DeleteEventFunction               | handler/delete_event                | DELETE /events/{event_id}                              |
| HdcnCognitoAdminFunction          | handler/hdcn_cognito_admin          | ANY /cognito, /cognito/{proxy+}, /auth, /auth/{proxy+} |
| GetMembershipsFunction            | handler/get_memberships             | GET /memberships                                       |
| CreateMembershipFunction          | handler/create_membership           | POST /memberships                                      |
| GetMembershipByIdFunction         | handler/get_membership_byid         | GET /memberships/{id}                                  |
| UpdateMembershipFunction          | handler/update_membership           | PUT /memberships/{id}                                  |
| DeleteMembershipFunction          | handler/delete_membership           | DELETE /memberships/{id}                               |
| CreateCartFunction                | handler/create_cart                 | POST /carts                                            |
| GetCartFunction                   | handler/get_cart                    | GET /carts/{cart_id}                                   |
| ClearCartFunction                 | handler/clear_cart                  | DELETE /carts/{cart_id}                                |
| UpdateCartItemsFunction           | handler/update_cart_items           | PUT /carts/{cart_id}/items                             |
| CreateOrderFunction               | handler/create_order                | POST /orders                                           |
| GetOrdersFunction                 | handler/get_orders                  | GET /orders                                            |
| GetOrderByIdFunction              | handler/get_order_byid              | GET /orders/{order_id}                                 |
| UpdateOrderStatusFunction         | handler/update_order_status         | PUT /orders/{order_id}/status                          |
| GetCustomerOrdersFunction         | handler/get_customer_orders         | GET /orders/customer/{customer_id}                     |
| S3FileManagerFunction             | handler/s3_file_manager             | POST/DELETE/GET /s3/files                              |
| ExportMembersFunction             | handler/export_members              | GET /members/export                                    |

### Other Resources (5)

| Logical ID                          | Type                          | Purpose                               |
| ----------------------------------- | ----------------------------- | ------------------------------------- |
| AuthLayer                           | AWS::Serverless::LayerVersion | Shared authentication utilities layer |
| EmailTemplatesBucket                | AWS::S3::Bucket               | S3 bucket for email templates         |
| MyApi                               | AWS::Serverless::Api          | API Gateway REST API                  |
| CognitoCustomMessagePermission      | AWS::Lambda::Permission       | Cognito trigger permission            |
| CognitoPostConfirmationPermission   | AWS::Lambda::Permission       | Cognito trigger permission            |
| CognitoPostAuthenticationPermission | AWS::Lambda::Permission       | Cognito trigger permission            |
| CognitoPreSignUpPermission          | AWS::Lambda::Permission       | Cognito trigger permission            |

---

## 2. Deployed Resources NOT in Template (Gaps)

### DynamoDB Tables — 7 tables missing (CRITICAL)

The template references table names via parameters but does **NOT** define the tables themselves. All 7 tables exist as manually-created resources in the Personal_Account:

| Table Name  | Partition Key  | Known GSIs        | In Template?       |
| ----------- | -------------- | ----------------- | ------------------ |
| Producten   | id (S)         | —                 | ❌ Referenced only |
| Members     | id (S)         | email-index       | ❌ Referenced only |
| Payments    | payment_id (S) | member_id-index   | ❌ Referenced only |
| Events      | event_id (S)   | date-index        | ❌ Referenced only |
| Memberships | id (S)         | —                 | ❌ Referenced only |
| Carts       | cart_id (S)    | user_id-index     | ❌ Referenced only |
| Orders      | order_id (S)   | customer_id-index | ❌ Referenced only |

**Impact:** Deploying to the nonprofit account will fail because these tables won't exist. They must be defined as `AWS::DynamoDB::Table` resources.

**Addressed in:** Task 3.2

### Cognito User Pool and Client — missing (CRITICAL)

The template references the existing Cognito User Pool via parameters (`ExistingUserPoolId`, `ExistingUserPoolClientId`) but does NOT define:

- The User Pool itself (`AWS::Cognito::UserPool`)
- The User Pool Client (`AWS::Cognito::UserPoolClient`)
- The User Pool Domain
- The Identity Provider (Google Workspace SSO)
- User Pool Groups (hdcnLeden, admin, etc.)

**Impact:** The nonprofit account will have no Cognito pool. Users cannot authenticate.

**Addressed in:** Task 3.3

### S3 Bucket (my-hdcn-bucket) — missing (CRITICAL)

The template references `my-hdcn-bucket` in IAM policies and the S3FileManagerFunction but does NOT define the bucket as a resource. The bucket is used for:

- Product images (`product-images/`)
- Website images (`imagesWebsite/`)
- Analytics data (`analytics/`)
- General file storage

**Impact:** S3 operations will fail in the nonprofit account. The bucket must be defined as `AWS::S3::Bucket`.

**Addressed in:** Task 3.4

---

## 3. Hardcoded References Requiring Parameterization

### 3.1 Hardcoded Account ID (344561557829)

| Location in template.yaml       | Line  | Current Value                                                          | Fix                                 |
| ------------------------------- | ----- | ---------------------------------------------------------------------- | ----------------------------------- |
| Outputs → CognitoUserPoolDomain | ~1232 | `https://h-dcn-auth-new-344561557829.auth.eu-west-1.amazoncognito.com` | Use `!Sub` with `${AWS::AccountId}` |

**Addressed in:** Task 3.5

### 3.2 Hardcoded Cognito User Pool ID

| Location in template.yaml               | Line | Current Value                  | Fix                                           |
| --------------------------------------- | ---- | ------------------------------ | --------------------------------------------- |
| DynamoDBRole → CognitoReadAccess policy | ~407 | `userpool/eu-west-1_OAT3oPCIm` | Use `!Sub .../userpool/${ExistingUserPoolId}` |

**Note:** Other Cognito references correctly use `!Sub` with `${ExistingUserPoolId}` (e.g., CognitoLambdaRole, CognitoAdminRole, Lambda Permissions). Only the DynamoDBRole has this inconsistency.

**Addressed in:** Task 3.5

### 3.3 Hardcoded S3 Bucket Name (my-hdcn-bucket)

| Location in template.yaml        | Context                  | Current Value                             | Fix                                          |
| -------------------------------- | ------------------------ | ----------------------------------------- | -------------------------------------------- |
| DynamoDBRole → S3AnalyticsAccess | Resource ARN             | `arn:aws:s3:::my-hdcn-bucket/analytics/*` | Use `!Sub` with bucket parameter             |
| DynamoDBRole → S3AnalyticsAccess | ListBucket Resource      | `arn:aws:s3:::my-hdcn-bucket`             | Use `!Sub` with bucket parameter             |
| DynamoDBRole → S3AnalyticsAccess | Condition prefix         | `analytics/*`                             | OK (prefix is logical, not account-specific) |
| S3FileManagerFunction → Policies | S3ReadPolicy BucketName  | `my-hdcn-bucket`                          | Use `!Ref` to new S3 bucket resource         |
| S3FileManagerFunction → Policies | S3WritePolicy BucketName | `my-hdcn-bucket`                          | Use `!Ref` to new S3 bucket resource         |
| S3FileManagerFunction → Policies | DeleteObject Resource    | `arn:aws:s3:::my-hdcn-bucket/*`           | Use `!Sub` with bucket parameter             |
| Outputs → AnalyticsDataInfo      | Value                    | `s3://my-hdcn-bucket/analytics/`          | Use `!Sub` with bucket reference             |

**Addressed in:** Task 3.5

### 3.4 Other Hardcoded References (outside template.yaml)

These are outside the SAM template scope but noted for completeness:

| File                                                  | Hardcoded Value                               | Fix                                       |
| ----------------------------------------------------- | --------------------------------------------- | ----------------------------------------- |
| `scripts/config.sh`                                   | `AWS_ACCOUNT_ID="344561557829"`               | Dynamic via `aws sts get-caller-identity` |
| `scripts/config.sh`                                   | `COGNITO_DOMAIN="h-dcn-auth-344561557829..."` | Environment variable                      |
| `scripts/config.sh`                                   | `COGNITO_USER_POOL_ID="eu-west-1_OAT3oPCIm"`  | Environment variable                      |
| `frontend/src/components/auth/OAuthCallback.tsx`      | Account ID in Cognito domain                  | Environment variable                      |
| `frontend/src/components/auth/GoogleSignInButton.tsx` | Account ID in Cognito domain                  | Environment variable                      |
| `frontend/src/services/googleAuthService.ts`          | Account ID in Cognito domain                  | Environment variable                      |
| 30+ scripts in `scripts/`                             | `eu-west-1_OAT3oPCIm` hardcoded               | Should use config/env variable            |
| Multiple scripts in `scripts/`                        | `my-hdcn-bucket` hardcoded                    | Should use config/env variable            |

---

## 4. Gap Summary by Category

| Category                  | Gap Count                                   | Severity | Task to Address |
| ------------------------- | ------------------------------------------- | -------- | --------------- |
| DynamoDB Tables           | 7 tables not defined                        | CRITICAL | Task 3.2        |
| Cognito User Pool         | Pool + Client + Domain + IdP not defined    | CRITICAL | Task 3.3        |
| S3 Bucket                 | Main app bucket not defined                 | CRITICAL | Task 3.4        |
| Hardcoded Account IDs     | 1 occurrence in template                    | HIGH     | Task 3.5        |
| Hardcoded Cognito Pool ID | 1 occurrence in template                    | HIGH     | Task 3.5        |
| Hardcoded S3 Bucket Name  | 6 occurrences in template                   | HIGH     | Task 3.5        |
| Missing Resource Tags     | No Project/Environment/ManagedBy/Owner tags | MEDIUM   | Task 3.6        |
| Missing PITR              | Tables not defined, so no PITR config       | MEDIUM   | Task 3.2        |
| Missing S3 Versioning     | Main bucket not defined, so no versioning   | MEDIUM   | Task 3.4        |

---

## 5. What IS Working Well

- ✅ All Lambda functions are defined in the template
- ✅ API Gateway is fully defined with CORS configuration
- ✅ IAM roles use `!Sub` with `${AWS::AccountId}` for most ARNs (except noted gaps)
- ✅ X-Ray tracing enabled globally
- ✅ Lambda Layer (AuthLayer) is defined
- ✅ Email Templates S3 bucket is properly defined with encryption and public access block
- ✅ Cognito Lambda permissions use `!Sub` with `${ExistingUserPoolId}` (except DynamoDBRole)
- ✅ Table names are parameterized (even though tables aren't created by the template)
- ✅ Environment parameter exists for multi-environment support

---

## 6. Recommended Task Execution Order

1. **Task 3.2** — Add DynamoDB table definitions (7 tables with indexes and PITR)
2. **Task 3.3** — Add Cognito User Pool, Client, Domain, and Identity Provider
3. **Task 3.4** — Add S3 bucket definition with versioning and lifecycle rules
4. **Task 3.5** — Remove all hardcoded values and parameterize
5. **Task 3.6** — Add resource tagging (Globals section)
6. **Task 3.7** — Add samconfig.toml nonprofit environment
7. **Task 3.8** — Validate template with `sam validate` and `cfn-lint`
