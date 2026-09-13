# Tech Stack

## Backend

- **Runtime**: Python 3.11
- **Framework**: AWS SAM (Serverless Application Model)
- **Infrastructure**: AWS Lambda, API Gateway (REST), DynamoDB, S3, Cognito, SES, CloudFront
- **Region**: eu-west-1 (Ireland)
- **Architecture**: One Lambda function per API endpoint, each in its own directory under `backend/handler/`
- **Shared code**: Lambda Layer (`backend/layers/auth-layer/`) providing `shared.auth_utils` and `shared.maintenance_fallback`
- **Key libraries**: boto3, gspread, google-auth, requests

## Frontend

- **Framework**: React 18 with TypeScript
- **UI library**: Chakra UI v2
- **Auth**: AWS Amplify v6
- **Build tool**: react-scripts (Create React App) with Webpack
- **State/forms**: Formik + Yup validation
- **HTTP client**: Axios
- **Charts**: Recharts, Visx
- **PDF generation**: jsPDF + jspdf-autotable
- **Payments**: Stripe (react-stripe-js)
- **Testing**: Jest + React Testing Library
- **i18n**: react-i18next with 8 languages (nl, en, de, fr, es, it, da, sv). Namespace per module (e.g., `presmeet`, `auth`, `common`). All user-facing strings must use `useTranslation()` with translation keys — never hardcoded text. Translation files at `frontend/src/locales/{lang}/{namespace}.json`.
  > **Important:** Always use `npx react-scripts test` (or `npm test`) — never `npx jest`

## CI/CD

- **Platform**: GitHub Actions
- **Backend deploy**: `sam build --use-container` → `sam deploy` to CloudFormation stack `h-dcn`
- **Frontend deploy**: `npm run build` → S3 sync → CloudFront invalidation
- **Security scanning**: GitGuardian (ggshield) — native git pre-push hook + CI `commit-range` scan
- **Pre-commit**: Kiro hook (`.kiro/hooks/ggshield-pre-commit.kiro.hook`) — syncs auth layer + runs local regex secret scanner (no API calls)
- **Pre-push**: Native git hook (`.githooks/pre-push`) — runs ggshield API scan, falls back to local scanner if quota exhausted
- **Trigger**: Push to `main` branch (path-filtered)

## DynamoDB Tables

- Producten, Members, Payments, Events, Memberships, Carts, Orders

## File Size Guidelines

**Target: 500 lines | Maximum: 1000 lines**

- Target 500 lines in new code and refactoring
- Maximum 1000 lines — files exceeding this require refactoring
- Exceptions: test files, generated files, configuration files with extensive mappings

**Frontend**: split components, extract hooks, move utils. **Backend**: split modules, extract helpers, use service layer, separate blueprint files.

## Common Commands

### Git

Use plain terminal git in the WSL shell (same as the other projects in this
setup). Run git from the native Linux path (`/home/peter/projects/h-dcn`), not
the `\\wsl.localhost\...` UNC path — the UNC path triggers "dubious ownership"
errors. No MCP git server is required; if one is configured it is optional.

```bash
# Stage specific files (avoid `git add .` / `git add -A` — stage by name):
git add path/to/file.py

# Commit with a conventional-commit message:
git commit -m "type: subject"

# Push (secret scanning is enforced here by the native pre-push hook,
# .githooks/pre-push — it runs regardless of how you committed):
git push
```

Notes:
- Secret scanning is enforced at **pre-push** (`.githooks/pre-push`), so it fires
  on every push no matter how the commit was made.
- Never bypass hooks with `--no-verify` (per guardrails).
- Never push directly to `main` unless explicitly asked; prefer a PR via `gh`.

### Backend

```bash
# Build (from backend/)
sam build --use-container

# Local invoke a single function
sam local invoke <FunctionName> -e events/event.json

# Start local API
sam local start-api

# Deploy (prod)
sam deploy --stack-name h-dcn --region eu-west-1 --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --resolve-s3 --no-confirm-changeset --no-fail-on-empty-changeset

# Run tests (from backend/)
pytest tests/
```

> **Local testing setup:** see [`docs/development/local-backend-testing.md`](../../docs/development/local-backend-testing.md) for the isolated venv (`PYTHONNOUSERSITE=1`), pinned deps, and `sam local` + DynamoDB Local (native WSL Docker engine).

### Frontend

```bash
# Install dependencies (from frontend/)
npm install

# Start dev server
npm start

# Production build
npm run build:prod

# Run tests
npm test -- --watchAll=false

# Type check
npm run type-check
```
