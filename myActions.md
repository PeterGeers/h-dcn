# Build & Actions (Windows PowerShell)

This file documents the exact steps to build and run the H-DCN workspace (frontend + backend) on Windows PowerShell. Paste or run the commands in PowerShell (`pwsh.exe`).

## Prerequisites
- Node.js 18+ (install from https://nodejs.org/)
- Python 3.11 (SAM template uses python3.11)
- AWS CLI v2 configured (run `aws configure` or set environment variables)
- AWS SAM CLI installed
- Docker Desktop (required for `sam build --use-container` and `sam local`)

## Frontend (React)
Working directory: `frontend`

1) Install dependencies

```powershell
cd C:\Users\peter\aws\h-dcn\frontend
npm install
# or if you prefer pnpm:
# pnpm install
```

2) Run development server

```powershell
npm start
```

3) Create production build

```powershell
# Normal build
npm run build
# Windows-specific production build (avoids source maps as provided by package.json)
npm run build:prod
```

Output: `frontend\build\` (static assets). Use `frontend\deploy.ps1` to upload to S3 (README mentions this).

Notes:
- Copy `.env.example` to `.env` and set `REACT_APP_*` env vars before running dev/build.
- `build:prod` uses a Windows `set` command in `package.json` so it's safe for PowerShell.

## Backend (AWS SAM)
Working directory: `backend`

Template uses `python3.11` for Lambda functions. Recommended: use Docker + `sam build --use-container` to ensure identical Lambda environment.

1) Optional: create & activate a Python virtual environment for running tests and scripts

```powershell
cd C:\Users\peter\aws\h-dcn\backend
python -m venv .\.venv
.\.venv\Scripts\Activate.ps1
pip install -r tests/requirements.txt   # if you will run backend tests
```

2) Build with SAM (recommended: containerized)

```powershell
# From backend folder
sam build --use-container
```

This produces build artifacts in `backend\.aws-sam\build\`.

3) Deploy (first time: guided)

```powershell
sam deploy --guided
```

Follow the interactive prompts (stack name, region, S3 bucket for artifacts, etc.). If `samconfig.toml` is already present from a previous deploy, you can re-run simply `sam deploy`.

4) Local testing (requires Docker)

```powershell
# Start local API
sam local start-api

# Invoke a single function (example event file exists in backend/events/event.json)
sam local invoke FunctionLogicalId -e events/event.json
```

## Tests
- Frontend

```powershell
cd C:\Users\peter\aws\h-dcn\frontend
npm test
```

- Backend (unit)

```powershell
cd C:\Users\peter\aws\h-dcn\backend
# Activate venv if created earlier
pip install -r tests/requirements.txt
python -m pytest tests/unit -v
```

Integration tests require a deployed stack and proper `AWS_SAM_STACK_NAME` env var as noted in README.

## Troubleshooting & Tips
- SAM build errors with compiled/binary wheels: ensure Docker is running and `--use-container` is used.
- Windows PowerShell script execution policy: to run `.ps1` scripts, you may need to bypass execution policy for a single run:

```powershell
powershell -ExecutionPolicy Bypass -File .\frontend\deploy.ps1
```

- If `react-scripts build` fails due to env var differences, confirm `.env` is present and variables are prefixed with `REACT_APP_`.
- If `sam build` is slow, increase Docker resources (RAM/CPUs) in Docker Desktop settings.

## Quick checklist (copyable)

```powershell
# Frontend
cd C:\Users\peter\aws\h-dcn\frontend
npm install
copy .env.example .env
npm run build:prod

# Backend
cd ..\backend
sam build --use-container
sam deploy --guided
```

## Next steps you can ask me to run
- Run `npm install` and `npm run build` and report results.
- Run `sam build --use-container` locally and share the output (requires Docker running).
- Create a single PowerShell script that chains frontend build + backend SAM build and optionally deploys.

---

File created by request on Oct 17, 2025.
