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
- **Security scanning**: GitGuardian (ggshield) — CI `commit-range` scan + Kiro preToolUse hook for local commits
- **Pre-commit**: Kiro hook (`.kiro/hooks/ggshield-pre-commit.kiro.hook`) — syncs auth layer + runs `ggshield secret scan pre-commit`
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

```bash
# IMPORTANT: Always use the MCP git tool (mcp_git_git_commit) for commits — NOT execute_pwsh with "git commit".
# This ensures the ggshield preToolUse hook fires for secret scanning + auth layer sync.
# The MCP tool automatically uses --no-verify.

# For staging files, use the MCP git_add tool:
# mcp_git_git_add(repo_path, files)

# For committing, use the MCP git_commit tool:
# mcp_git_git_commit(repo_path, message)

# Only use shell for git push (no MCP tool available for push):
git push
```

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
