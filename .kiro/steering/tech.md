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

## CI/CD

- **Platform**: GitHub Actions
- **Backend deploy**: `sam build --use-container` → `sam deploy` to CloudFormation stack `h-dcn`
- **Frontend deploy**: `npm run build` → S3 sync → CloudFront invalidation
- **Security scanning**: GitGuardian (ggshield) — CI `commit-range` scan + Kiro preToolUse hook for local commits
- **Pre-commit**: Kiro hook (`.kiro/hooks/ggshield-pre-commit.kiro.hook`) — syncs auth layer + runs `ggshield secret scan pre-commit`
- **Trigger**: Push to `main` branch (path-filtered)

## DynamoDB Tables

- Producten, Members, Payments, Events, Memberships, Carts, Orders

## Common Commands

### Git

```bash
# Always use --no-verify when committing (shell hook can't run in Kiro's environment)
# Secret scanning + auth layer sync is handled by the Kiro preToolUse hook (ggshield-pre-commit)
git commit --no-verify -m "message"
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
