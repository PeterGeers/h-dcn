---
inclusion: always
---

# Guardrails

Critical safety rules for H-DCN development. Violations can cause irreversible data loss or production outages.

## S3 Bucket Separation

Two buckets exist in account 506221081911. They serve completely different purposes and must NEVER be confused.

| Bucket                        | Purpose                                | Overwritable? |
| ----------------------------- | -------------------------------------- | ------------- |
| `h-dcn-frontend-506221081911` | Frontend build artifacts (HTML/CSS/JS) | Yes (deploy)  |
| `h-dcn-data-506221081911`     | User data: images, uploads, config     | **NEVER**     |

Rules:

- Never use `--delete` flag against the data bucket
- Never run `aws s3 rm --recursive` against the data bucket
- Never use the data bucket as a fallback value for frontend config
- If a command targets `h-dcn-data-*`, stop and verify intent before executing

## Environment Variables

Critical environment variables MUST throw on missing values. Silent fallbacks mask misconfigurations that can route operations to the wrong bucket or endpoint.

| Variable                            | Value / Purpose                                               |
| ----------------------------------- | ------------------------------------------------------------- |
| `REACT_APP_S3_BUCKET`               | Frontend code bucket                                          |
| `REACT_APP_IMAGES_BUCKET`           | Data bucket (images, uploads)                                 |
| `REACT_APP_API_BASE_URL`            | `https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod` |
| `REACT_APP_USER_POOL_ID`            | Cognito pool ID                                               |
| `REACT_APP_USER_POOL_WEB_CLIENT_ID` | Cognito app client ID                                         |

```typescript
// ✅ Correct — fail fast
if (!process.env.REACT_APP_S3_BUCKET) {
  throw new Error("REACT_APP_S3_BUCKET is required");
}

// ❌ Forbidden — dangerous fallback
const bucket = process.env.REACT_APP_S3_BUCKET || "h-dcn-data-506221081911";
```

## Deployment

### Allowed deployment methods

- `scripts/deployment/frontend-build-and-deploy-fast.ps1` — frontend to code bucket
- `scripts/deployment/backend-build-and-deploy-fast.ps1` — backend via SAM
- GitHub Actions workflows (`deploy-backend.yml`, `deploy-frontend.yml`)

### Forbidden commands

```bash
# NEVER execute these — they destroy production data
aws s3 sync build/ s3://h-dcn-data-506221081911/ --delete
aws s3 rm s3://h-dcn-data-506221081911/ --recursive
```

Any `aws s3` command with `--delete` targeting the data bucket requires explicit user confirmation before execution, regardless of context.

## Core Rules

1. **Fix only what is asked** — do not add unrequested features, validation, logging, or refactoring
2. **Ask before adding** — if you notice unrelated issues, mention them but do not fix without permission
3. **No dangerous fallbacks** — critical env vars must throw on missing values
4. **Never `--delete` on data bucket** — contains irreplaceable business data (member photos, uploads, config)
5. **Deploy via scripts or CI only** — never raw `aws s3 sync` to production buckets
6. **No secrets in code** — GitGuardian pre-commit hook enforces this; do not bypass with `--no-verify`
7. **Backup before destructive data operations** — use `scripts/utilities/` backup scripts before migrations or bulk updates

## Emergency Recovery: Wrong Bucket Deployment

If a sync or delete accidentally targets the data bucket:

1. Cancel immediately (Ctrl+C)
2. Check versioning: `aws s3api list-object-versions --bucket h-dcn-data-506221081911 --profile nonprofit-deploy`
3. Restore deleted/overwritten objects from S3 versions
4. Verify `.env` has correct bucket assignments before retrying

## Reference

Full guardrails with checklists and compliance details: [`docs/development/guardrails.md`](../../docs/development/guardrails.md)
