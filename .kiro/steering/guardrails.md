---
inclusion: auto
---

# Guardrails

Critical safety rules for H-DCN development. Prevents data loss and deployment mistakes.

## S3 Bucket Separation — NEVER MIX

| Bucket                        | Purpose                                | Safe to overwrite? |
| ----------------------------- | -------------------------------------- | ------------------ |
| `h-dcn-frontend-506221081911` | Frontend code (HTML/CSS/JS)            | Yes                |
| `h-dcn-data-506221081911`     | Data: images, parameters.json, uploads | **NEVER**          |

## Environment Variables — Fail Fast, No Fallbacks

Critical env vars MUST throw errors when missing. No fallback values allowed.

- `REACT_APP_S3_BUCKET` — frontend code bucket
- `REACT_APP_IMAGES_BUCKET` — data bucket (never use as fallback for code bucket)
- `REACT_APP_API_BASE_URL` — `https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod`
- `REACT_APP_USER_POOL_ID` — Cognito pool
- `REACT_APP_USER_POOL_WEB_CLIENT_ID` — Cognito client

```typescript
// ❌ NEVER: const bucket = process.env.REACT_APP_S3_BUCKET || "h-dcn-data-506221081911";
// ✅ ALWAYS: throw new Error("REACT_APP_S3_BUCKET is required") when missing
```

## Safe Deployment

Use ONLY these scripts for production deployments:

- `scripts/deployment/frontend-build-and-deploy-fast.ps1` — frontend to code bucket
- `scripts/deployment/backend-build-and-deploy-fast.ps1` — backend via SAM

Forbidden commands:

- `aws s3 sync build/ s3://h-dcn-data-506221081911/ --delete`
- `aws s3 rm s3://h-dcn-data-506221081911/ --recursive`
- Any `--delete` on the data bucket

## Core Rules

1. **Only fix what's asked** — don't add unrequested features, validation, or logging
2. **Ask before adding** — if you see other issues, ask permission first
3. **No dangerous fallbacks** — critical env vars must throw, never fall back
4. **Never `--delete` on data bucket** — irreplaceable business data
5. **Deploy via scripts only** — never raw `aws s3 sync` to production buckets
6. **No secrets in code** — GitGuardian pre-commit hook enforces this
7. **Backup before data ops** — use `scripts/utilities/` backup scripts

## Emergency: Wrong Bucket Deployment

1. Stop sync immediately (Ctrl+C)
2. Check S3 versioning: `aws s3api list-object-versions --bucket h-dcn-data-506221081911`
3. Restore from versions or local backups
4. Verify `.env` has correct bucket assignments

## Reference

Full guardrails with checklists, emergency procedures, and compliance:
[`docs/development/guardrails.md`](../../docs/development/guardrails.md)
