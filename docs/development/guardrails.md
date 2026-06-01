# Development Guardrails — Full Reference

Comprehensive safety rules, emergency procedures, checklists, and compliance requirements for H-DCN development.

> **Quick version**: See [`.kiro/steering/guardrails.md`](../../.kiro/steering/guardrails.md) for the concise steering file loaded into AI context.

---

## S3 Bucket Architecture

H-DCN uses two S3 buckets with strictly separated purposes. Mixing them up has caused data loss in the past.

### Code Bucket (safe to overwrite)

| Property        | Value                                               |
| --------------- | --------------------------------------------------- |
| Bucket name     | `h-dcn-frontend-506221081911`                       |
| Purpose         | Frontend build artifacts (HTML, CSS, JS)            |
| Deployment      | Automated via `frontend-build-and-deploy-fast.ps1`  |
| `--delete` flag | Safe to use — content is regenerated on every build |

### Data Bucket (NEVER delete content)

| Property        | Value                                                  |
| --------------- | ------------------------------------------------------ |
| Bucket name     | `h-dcn-data-506221081911`                              |
| Purpose         | `parameters.json`, product images, logos, user uploads |
| Deployment      | Manual only, via utility scripts with backups          |
| `--delete` flag | **NEVER** — contains irreplaceable business data       |

### Separation Rules

1. **NEVER use `--delete` on `h-dcn-data-506221081911`** — contains irreplaceable business data
2. **NEVER deploy code to `h-dcn-data-506221081911`** — it's for data only
3. **NEVER deploy data to `h-dcn-frontend-506221081911`** — it gets overwritten on next deploy
4. **ALWAYS backup before data operations** — use `scripts/utilities/backup-parameters.ps1`
5. **`parameters.json` is DATA, not code** — lives in `h-dcn-data-506221081911`, not the frontend bucket

### Environment Variables for Buckets

```bash
REACT_APP_S3_BUCKET=h-dcn-frontend-506221081911
REACT_APP_IMAGES_BUCKET=h-dcn-data-506221081911
REACT_APP_IMAGES_BASE_URL=https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com
REACT_APP_LOGO_BUCKET_URL=https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com
```

---

## Environment Variable Validation Patterns

### Fail-Fast Policy

All critical environment variables MUST throw errors when missing. Fallback values are **forbidden** for production-critical configuration because they can silently route operations to the wrong bucket or endpoint.

### Critical Variables (MUST throw if missing)

```bash
# Buckets
REACT_APP_S3_BUCKET=h-dcn-frontend-506221081911
REACT_APP_IMAGES_BUCKET=h-dcn-data-506221081911

# API
REACT_APP_API_BASE_URL=https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod

# Authentication (see .kiro/steering/authentication.md for full Cognito details)
REACT_APP_USER_POOL_ID=eu-west-1_fcUkvwjH5
REACT_APP_USER_POOL_WEB_CLIENT_ID=6jhvk853b0lfg9q1m861qs0cug

# URLs
REACT_APP_IMAGES_BASE_URL=https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com
REACT_APP_LOGO_BUCKET_URL=https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com
REACT_APP_AWS_REGION=eu-west-1
```

### Optional Variables (safe defaults allowed)

```bash
REACT_APP_CACHE_VERSION=1.0    # UI cache busting
```

### Validation Pattern — TypeScript

```typescript
// ✅ REQUIRED — Fail fast pattern
const validateEnvironment = () => {
  const required = [
    "REACT_APP_S3_BUCKET",
    "REACT_APP_IMAGES_BUCKET",
    "REACT_APP_API_BASE_URL",
    "REACT_APP_USER_POOL_ID",
    "REACT_APP_USER_POOL_WEB_CLIENT_ID",
  ];

  for (const envVar of required) {
    if (!process.env[envVar]) {
      throw new Error(`${envVar} environment variable is required`);
    }
  }
};
```

### Forbidden Pattern — Dangerous Fallbacks

```typescript
// ❌ FORBIDDEN — This caused data loss when code bucket var was missing
const bucketName = process.env.REACT_APP_S3_BUCKET || "h-dcn-data-506221081911";

// ❌ FORBIDDEN — Cross-bucket fallback
const bucketName =
  process.env.REACT_APP_IMAGES_BUCKET || "h-dcn-frontend-506221081911";

// ✅ REQUIRED — Throw immediately
const bucketName = process.env.REACT_APP_S3_BUCKET;
if (!bucketName) {
  throw new Error("REACT_APP_S3_BUCKET environment variable is required");
}
```

### Secrets Management

- **Development**: Use `.secrets` file (never commit — in `.gitignore`)
- **Production**: AWS Parameter Store or Lambda environment variables
- **Local testing**: Use `load-secrets.ps1` to load from `.secrets`
- **CI/CD**: GitHub Actions secrets or AWS IAM roles
- **Pre-commit**: GitGuardian hook prevents credential leaks

---

## Safe and Dangerous Command Lists

### ✅ Safe Commands

```powershell
# Frontend code deployment (overwrites code bucket — safe)
.\scripts\deployment\frontend-build-and-deploy-fast.ps1

# Backend deployment via SAM
.\scripts\deployment\backend-build-and-deploy-fast.ps1

# Data operations WITH backups
.\scripts\utilities\backup-parameters.ps1
.\scripts\utilities\deploy-parameters.ps1
.\scripts\utilities\restore-images-from-local.ps1

# Sync only static assets to code bucket
aws s3 sync build/static/ s3://h-dcn-frontend-506221081911/static/ --delete --profile nonprofit-deploy
```

### ❌ Dangerous Commands — NEVER RUN

```powershell
# NEVER delete data bucket content
aws s3 sync build/ s3://h-dcn-data-506221081911/ --delete
aws s3 rm s3://h-dcn-data-506221081911/ --recursive

# NEVER deploy code to data bucket
aws s3 sync build/ s3://h-dcn-data-506221081911/

# NEVER deploy data to code bucket
aws s3 cp parameters.json s3://h-dcn-frontend-506221081911/

# NEVER use default AWS profile for deployments (points to old account)
aws s3 sync build/ s3://h-dcn-frontend-506221081911/   # Missing --profile!
```

### AWS CLI Profile Rules

> For full AWS account structure and CLI profile details, see [`.kiro/steering/aws-dynamodb.md`](../../.kiro/steering/aws-dynamodb.md).

- **Always use `--profile nonprofit-deploy`** for automated operations
- **Never use `default` profile** — it points to the old account (344561557829)
- **`nonprofit-dev`** — for interactive/admin work (requires MFA)

---

## Emergency Recovery Procedures

### Data Loss Recovery

| Step | Action                | Command/Detail                                                                               |
| ---- | --------------------- | -------------------------------------------------------------------------------------------- |
| 1    | Stop all operations   | Cancel running syncs immediately (Ctrl+C)                                                    |
| 2    | Check S3 versioning   | `aws s3api list-object-versions --bucket h-dcn-data-506221081911 --profile nonprofit-deploy` |
| 3    | Restore from versions | Use AWS Console or CLI to restore previous object versions                                   |
| 4    | Local backup restore  | Run `.\scripts\utilities\restore-images-from-local.ps1` if local backups exist               |
| 5    | Fix database URLs     | Run `fix-product-image-urls.ps1` to update image references                                  |
| 6    | Post-mortem           | Document cause and update guardrails                                                         |

### Wrong Bucket Deployment

| Step | Action           | Detail                                       |
| ---- | ---------------- | -------------------------------------------- |
| 1    | Stop immediately | Cancel running sync (Ctrl+C)                 |
| 2    | Assess damage    | Check what was overwritten in data bucket    |
| 3    | Restore data     | Use S3 versioning or local backups           |
| 4    | Fix environment  | Verify `.env` has correct bucket assignments |
| 5    | Re-deploy safely | Use proper deployment scripts only           |
| 6    | Prevention       | Update guardrails to prevent recurrence      |

### Production Issues

| Step | Action        | Detail                                                     |
| ---- | ------------- | ---------------------------------------------------------- |
| 1    | Check logs    | CloudWatch logs for affected Lambda functions              |
| 2    | Assess impact | Determine effect on member data access and club operations |
| 3    | Communicate   | Notify H-DCN stakeholders and affected regional admins     |
| 4    | Fix           | Apply hotfix or rollback using SAM CLI deployment          |
| 5    | Post-mortem   | Document root cause and update guardrails                  |

### Security Incidents

| Step | Action       | Detail                                                     |
| ---- | ------------ | ---------------------------------------------------------- |
| 1    | Isolate      | Disable affected Lambda functions or Cognito User Pool     |
| 2    | Assess scope | Determine potential member data breach extent              |
| 3    | Notify       | Contact H-DCN board and affected members per GDPR          |
| 4    | Investigate  | Analyze CloudTrail logs and access patterns                |
| 5    | Remediate    | Fix vulnerability, rotate credentials, strengthen controls |

---

## Security Checklists

### Before Every Deployment

- [ ] Bucket verification — confirm correct bucket variables in `.env`
- [ ] Backup data — run `backup-parameters.ps1` if touching data
- [ ] Script verification — using `frontend-build-and-deploy-fast.ps1` for code
- [ ] No credentials in code (GitGuardian pre-commit hook validates)
- [ ] Input validation implemented for member data forms
- [ ] CORS properly configured for H-DCN frontend domain
- [ ] Error messages don't leak member personal data
- [ ] Dependencies scanned with `npm audit` and `pip-audit`

> For authentication validation requirements (Cognito JWT, auth patterns), see [`.kiro/steering/authentication.md`](../../.kiro/steering/authentication.md).

### Before Data Operations

- [ ] Environment variables set — all required bucket variables present
- [ ] No dangerous fallbacks — code throws errors for missing critical vars
- [ ] Backup created — current data backed up before changes
- [ ] Correct bucket targeted — double-check data goes to `h-dcn-data-506221081911`
- [ ] No `--delete` flags — never use `--delete` on data bucket operations
- [ ] Using `--profile nonprofit-deploy` — not the default profile

### Regular Security Reviews

- [ ] Review `hdcnRegio_*` group permissions quarterly
- [ ] Update Cognito User Pool security settings monthly
- [ ] Scan for vulnerable dependencies (GitGuardian dashboard, `npm audit`, `pip-audit`)
- [ ] Review API Gateway CORS and authentication configurations
- [ ] Audit member data access patterns in CloudWatch logs
- [ ] Validate `function_permissions` parameter store entries
- [ ] Test regional access restrictions (hdcnRegio_Noord, hdcnRegio_Zuid, etc.)

---

## Compliance Requirements

### GDPR / Data Protection

| Requirement           | Implementation                                   |
| --------------------- | ------------------------------------------------ |
| Data minimization     | Only collect necessary member data               |
| Data retention        | Delete inactive member data per club policy      |
| User consent          | Obtain consent for data processing and marketing |
| Data portability      | Allow members to export personal data            |
| Right to be forgotten | Implement member data deletion on request        |
| Breach notification   | Notify within 72 hours per GDPR Article 33       |

### Audit Requirements

| Area                | What to log                                          |
| ------------------- | ---------------------------------------------------- |
| Access logging      | All member data access with user identification      |
| Change tracking     | All modifications to member profiles and permissions |
| User activity       | Regional admin actions and member self-service       |
| System events       | Authentication attempts and permission changes       |
| Regional compliance | Data access respects geographic restrictions         |

### Access Control

> For full Cognito configuration and auth patterns, see [`.kiro/steering/authentication.md`](../../.kiro/steering/authentication.md).

| Role                             | Access Level                               |
| -------------------------------- | ------------------------------------------ |
| No groups                        | Membership registration only               |
| `hdcnLeden`                      | Webshop + profile management               |
| `hdcnRegio_Noord/Zuid/Oost/West` | Regional member administration (read-only) |
| `hdcnAdmins`                     | Full system access                         |

- Granular control via `function_permissions` parameter store
- Read/write separation with explicit permission levels
- Regional restrictions limit member data access by geography
- All permission changes logged in CloudWatch

---

## Architecture Safety Rules

### Frontend (React/TypeScript)

- **TypeScript everywhere** — all new code must be `.tsx`/`.ts`, no `any` without justification
- **Component isolation** — each component in its own file
- **Error boundaries** — wrap components to handle errors gracefully
- **Runtime validation** — validate API responses match expected types
- **No custom CSS** — use Chakra UI theme tokens exclusively

### Backend (AWS Lambda)

- **Single responsibility** — one function per API endpoint
- **Stateless design** — no local state between invocations
- **Consistent error format** — use `create_success_response()` / `create_error_response()`
- **Structured logging** — for debugging in CloudWatch

> For DynamoDB conventions, table structure, and SAM template rules, see [`.kiro/steering/aws-dynamodb.md`](../../.kiro/steering/aws-dynamodb.md).

### Critical Infrastructure Rule

**DynamoDB tables, Cognito User Pool, and S3 data buckets are managed OUTSIDE CloudFormation.** Never add them as CloudFormation resources without `DeletionPolicy: Retain` — a previous deploy deleted production data this way.

---

## Performance Standards

### Frontend Metrics

| Metric                   | Target           |
| ------------------------ | ---------------- |
| First Contentful Paint   | < 2 seconds      |
| Largest Contentful Paint | < 4 seconds      |
| Bundle size              | < 1MB compressed |
| API response time        | < 500ms average  |

### Backend Metrics

| Metric              | Target     |
| ------------------- | ---------- |
| Lambda cold start   | < 1 second |
| API Gateway latency | < 200ms    |
| DynamoDB response   | < 100ms    |
| Error rate          | < 1%       |

---

## AI Assistant Safety Rules

### The "Ask Before Adding" Rule

**ONLY fix the exact problem described. If you see other potential issues, ASK first.**

Examples of what to ask about:

- "I notice the status validation might cause issues, should I fix that too?"
- "Should I add logging for this operation?"
- "I see a potential security issue, should I address it?"

What NOT to do:

- ❌ Adding validation logic without being asked
- ❌ Adding "enhanced security" features
- ❌ Adding logging or audit trails without request
- ❌ "Improving" code beyond the specific issue
- ❌ Adding business logic validation in backend when frontend should handle it

This prevents wasted deployment time (30+ minutes each cycle), introducing new bugs, and breaking existing functionality.

---

## Maintenance Schedule

| Frequency       | Task                                                                 |
| --------------- | -------------------------------------------------------------------- |
| Weekly          | Review CloudWatch logs for API errors and access patterns            |
| Monthly         | Update dependencies and security patches (`npm audit`, `pip-audit`)  |
| Quarterly       | Review AWS costs, optimize DynamoDB/Lambda usage, review permissions |
| Annually        | Security audit and penetration testing for member data protection    |
| After incidents | Update this document and steering file with lessons learned          |

---

## Safe Deployment Process

1. **Environment check** — verify correct bucket variables are set
2. **Local testing** — verify changes work locally
3. **Code review** — get approval from team member
4. **Backup data** — run `backup-parameters.ps1` before data changes
5. **Deploy** — use safe deployment scripts only:
   - Frontend: `scripts/deployment/frontend-build-and-deploy-fast.ps1`
   - Backend: `scripts/deployment/backend-build-and-deploy-fast.ps1`
6. **Monitor** — watch CloudWatch logs and metrics post-deployment

---

_Document Version: 4.0 — Migrated from legacy steering file_
_Last Updated: 2025_
_Review Schedule: After any data loss incident + Quarterly_
