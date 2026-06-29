# H-DCN Deployment

## How Deployment Works

Production deploys happen via **GitHub Actions** — not the local PowerShell scripts.

| Trigger                            | What happens                                                          |
| ---------------------------------- | --------------------------------------------------------------------- |
| Push to `main` (backend/ changed)  | `deploy-backend.yml` → SAM build + deploy to `h-dcn` stack            |
| Push to `main` (frontend/ changed) | `deploy-frontend.yml` → npm build + S3 sync + CloudFront invalidation |
| Manual (`workflow_dispatch`)       | Same workflows, pick stage: `prod` or `test`                          |

### Stacks

| Stage | Stack name   | Frontend            | API                  |
| ----- | ------------ | ------------------- | -------------------- |
| prod  | `h-dcn`      | portal.h-dcn.nl     | via API Gateway      |
| test  | `h-dcn-test` | testportal.h-dcn.nl | separate API Gateway |

### Deploy a Feature Branch

```bash
# Deploy to test stack from a feature branch:
gh workflow run deploy-backend.yml --ref feature/my-branch -f stage=test
gh workflow run deploy-frontend.yml --ref feature/my-branch -f stage=test
```

### Run Full Test Suite Before Merge

The `Full Test Suite` workflow (`nightly-tests.yml`) runs all backend + frontend tests. Trigger it on your feature branch before merging to main:

```bash
gh workflow run nightly-tests.yml --ref feature/my-branch
```

This runs the complete backend pytest suite (~90 min) and all frontend tests (~30 min). Results are in the GitHub Actions job summary + downloadable artifacts. Currently run monthly with corrective actions tracked in `.kiro/specs/Common/code-quality-maintenance`.

### Deploy to Production

Merge to `main` — workflows trigger automatically (path-filtered).

---

## Data Migrations

Before deploying a feature branch to production, check [`scripts/MIGRATIONS.md`](../MIGRATIONS.md) for pending data migrations. Run them in listed order with `--dry-run` first.

---

## Local PowerShell Scripts

These scripts exist for **manual local deploys** (debugging, testing). They are NOT used by CI.

| Script                               | Purpose                                                      |
| ------------------------------------ | ------------------------------------------------------------ |
| `backend-build-and-deploy-fast.ps1`  | SAM build + deploy with AuthLayer sync check                 |
| `frontend-build-and-deploy-fast.ps1` | React build + S3 sync + CloudFront invalidation              |
| `deploy-full-stack.ps1`              | Runs both above + smoke tests                                |
| `smoke-test-production.js`           | Tests deployed endpoints (frontend + API reachable, CORS OK) |

```powershell
# Full local deploy (backend + frontend + smoke tests)
.\scripts\deployment\deploy-full-stack.ps1

# Backend only
.\scripts\deployment\backend-build-and-deploy-fast.ps1

# Frontend only
.\scripts\deployment\frontend-build-and-deploy-fast.ps1

# Options for deploy-full-stack:
.\scripts\deployment\deploy-full-stack.ps1 -SkipBackend
.\scripts\deployment\deploy-full-stack.ps1 -SkipFrontend
.\scripts\deployment\deploy-full-stack.ps1 -SkipTests
```

---

## Pre-Deployment Validation

The local backend script automatically:

- Checks AuthLayer sync (`backend/layers/auth-layer/python/shared/auth_utils.py` matches source)
- Validates SAM template syntax
- Runs `scripts/validate_all.py` (Python syntax + handler integrity)

---

## Troubleshooting

### 502 Bad Gateway

- Lambda not invoked or erroring on startup
- Check CloudWatch logs: `aws logs tail /aws/lambda/<function-name> --follow --region eu-west-1 --profile nonprofit-deploy`

### 403 Forbidden

- Expected for protected endpoints without auth
- Check JWT token is access token (not ID token)
- Verify Cognito pool ID matches

### CORS Errors

- API Gateway CORS config in `template.yaml` Globals section
- Lambda responses must include CORS headers (handled by `auth_utils.py`)
- Custom headers need to be in `Access-Control-Allow-Headers`

### AuthLayer Out of Sync

The Kiro pre-commit hook auto-syncs. Manual fix:

```powershell
Copy-Item backend\layers\auth-layer\python\shared\auth_utils.py backend\layers\auth-layer\python\shared\auth_utils.py
```

(Source of truth is the layer file itself — all handlers import from `shared.auth_utils`.)

### SAM Build Fails

- Check Docker is running (container-based builds)
- Check `template.yaml` YAML syntax
- Validate Python dependencies in `requirements.txt`

### Frontend Build Fails

- Run `npx tsc --noEmit` for type errors
- Run `npx eslint src/` for lint errors (CI fails on lint errors)
- Check `.env` file exists with required vars

---

## AWS Account & Credentials

- **Account:** 506221081911 (nonprofit)
- **Region:** eu-west-1
- **CI auth:** OIDC role assumption (`NonprofitDeployRole`)
- **Local auth:** `--profile nonprofit-deploy` (no MFA required)
- **Cognito pool:** `eu-west-1_fcUkvwjH5` (managed outside CloudFormation)

---

## Monitoring

```bash
# Tail logs for a specific function
aws logs tail /aws/lambda/<function-name> --follow --region eu-west-1 --profile nonprofit-deploy

# List API Gateways
aws apigateway get-rest-apis --region eu-west-1 --profile nonprofit-deploy
```
