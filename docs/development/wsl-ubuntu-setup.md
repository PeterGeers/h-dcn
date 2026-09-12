# WSL / Ubuntu Development Setup

This guide sets up the h-dcn development environment on WSL/Ubuntu (Linux). After
the WSL/Ubuntu migration, the commit/push path is **pure bash — no PowerShell is
required on Linux**. Deployments run through GitHub Actions (triggered by push to
`main`); the same commands can be run manually.

> The Linux working copy is created by **cloning fresh from GitHub**, not by
> copying the Windows working tree. This guarantees a clean, LF-normalized
> checkout without Windows-specific artifacts (`sam-env/`, Windows `.venv/`,
> `.aws-sam/`, `node_modules/`).

---

## 1. Toolchain

Install the following on Ubuntu. `bash` and coreutils are already present.
**`pwsh` (PowerShell) is NOT required.**

| Tool | Version | Notes |
| --- | --- | --- |
| Python | 3.11 | Matches the Lambda runtime and CI |
| Node.js | 18 | Matches CI (`actions/setup-node@v4` node 18) |
| AWS CLI | v2 | For S3, Cognito, deploy operations |
| AWS SAM CLI | latest | `sam build` / `sam deploy` |
| Docker | latest | Only needed for `sam build --use-container` |
| ggshield | latest | Secret scanning (pre-push); local scanner is the fallback |
| git | latest | — |

Example installs (adjust to preference):

```bash
# Python 3.11 + venv
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Node 18 (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip && sudo ./aws/install

# AWS SAM CLI — see AWS docs for the current Linux installer
# Docker — install Docker Engine (or enable Docker Desktop WSL integration)

# ggshield
pip install ggshield
```

---

## 2. Clone the repository

Clone into the **WSL native filesystem** (`/home/...`), **never** under `/mnt/c`
(the Windows mount is slow and applies Windows file semantics).

```bash
git clone https://github.com/PeterGeers/h-dcn.git /home/peter/projects/h-dcn
cd /home/peter/projects/h-dcn

# Until the migration branch is merged to main:
git checkout feature/wsl-ubuntu-migration
```

---

## 3. Git hooks

The repo ships a shared hooks directory. Point git at it and make the scripts
executable:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-push scripts/scan-secrets-local.sh scripts/precommit-guard.sh
```

- **Pre-commit** (Kiro hook, `.kiro/hooks/ggshield-pre-commit.json`): runs
  `scripts/precommit-guard.sh` — syncs the auth layer and runs the local bash
  secret scanner. Blocks a commit if a secret is found.
- **Pre-push** (`.githooks/pre-push`): runs ggshield on the changed files, falling
  back to `scripts/scan-secrets-local.sh` when the API quota is exhausted or
  ggshield is not installed.

Neither hook uses PowerShell.

---

## 4. Recreate machine-local artifacts

These files are gitignored and per-machine. **Recreate them natively — do not
copy them from the Windows tree.** Credentials are referenced by key name; supply
the values from your password manager / AWS.

### Backend virtualenv (Python 3.11, Linux `bin/`)

```bash
python3.11 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt -r backend/tests/requirements.txt
```

> Never reuse `backend/sam-env/` or a Windows `.venv/` from the old machine — they
> contain Windows binaries (`Scripts/`, `Lib/`) that do not work on Linux.

### Frontend dependencies

```bash
( cd frontend && npm install )
```

### Config and credential files (recreate by hand)

| File | Purpose |
| --- | --- |
| `backend/samconfig.toml` | SAM deploy defaults |
| `frontend/.env`, `frontend/.env.local` | Frontend env vars (see `frontend/.env.example`) |
| `.awsCredentials.json` | AWS credentials (by key name) |
| `.googleCredentials.json` | Google service credentials (by key name) |
| `.secrets` | Local secrets (by key name) |

AWS CLI profiles follow the existing conventions — use `--profile nonprofit-deploy`
for deploy/infra operations (see the `aws-dynamodb` steering; do not duplicate
account IDs here).

---

## 5. Deploying

The canonical deploy path is **GitHub Actions**, triggered by a push to `main`
(path-filtered). No PowerShell or local scripts are involved.

Equivalent manual commands (mirroring CI), for local use:

```bash
# Backend
cd backend
sam build
sam deploy   # uses samconfig.toml / --parameter-overrides as in the workflow

# Frontend
cd frontend
GENERATE_SOURCEMAP=false npm run build      # or: npm run build:prod
aws s3 sync build/ s3://<frontend-bucket>/ --delete --exclude "events/*/og.html"
aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
```

> The `scripts/**/*.ps1` files retained in the repo (deployment convenience,
> utilities, security helpers) are **Windows-only and not supported on Linux**.
> On Linux, use the CI workflows or the manual commands above instead.

---

## 6. Verification checklist

After setup, confirm the environment works:

- [ ] **Backend tests** — from `backend/`, run a targeted file, e.g.
      `pytest tests/unit/test_<name>.py` (do not run the full suite in automation).
- [ ] **Frontend type check** — from `frontend/`, `npx tsc --noEmit` passes.
- [ ] **Frontend targeted test** — e.g.
      `npx react-scripts test --watchAll=false --testPathPattern="<file>"`.
- [ ] **SAM build** — from `backend/`, `sam build` succeeds. If using
      `sam build --use-container`, Docker must be running; without Docker, use the
      plain `sam build` (as CI does).
- [ ] **Pre-commit hook** — a commit runs the auth-layer sync and the bash secret
      scanner; a staged fake secret is blocked.
- [ ] **Pre-push hook** — a push runs the secret scan.
- [ ] **Machine-local artifacts** — `.env`, `samconfig.toml`, and credential files
      are present and remain gitignored (never committed).

---

## Related docs

- `docs/secret-scanning-setup.md` — secret-scanning architecture (bash scanner + hooks)
- `docs/decisions/wsl-ubuntu-migration.md` — the migration decision record
