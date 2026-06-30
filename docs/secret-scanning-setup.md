# Secret Scanning Setup

This project uses a two-layer secret scanning approach to prevent secrets from reaching GitHub, while minimizing API quota usage.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Pre-commit (Kiro hook)                                 │
│ → Local regex scanner only (no API calls)                       │
│ → Fast feedback during development                              │
│ → Catches ~80% of common secret types                           │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: Pre-push (native git hook)                             │
│ → ggshield API scan (catches 400+ secret types)                 │
│ → Falls back to local scanner if API quota exhausted            │
│ → Hard gate — cannot be bypassed without --no-verify            │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: CI (GitHub Actions)                                    │
│ → ggshield commit-range scan on deploy                          │
│ → Final safety net                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Why This Design

Previously ggshield ran on every commit. During automated spec sessions (10-20 commits in rapid succession), this burned through the GitGuardian API quota (10k calls/month) within days. The fix:

- **Commits**: use a free, offline local scanner (no API calls)
- **Pushes**: use ggshield (1 API call per push, not per commit)
- **CI**: ggshield with `fetch-depth: 2` (scans only the new commit, not full history)

---

## Setup Instructions

### Prerequisites

1. **ggshield** installed and authenticated:

   ```bash
   pip install ggshield
   ggshield auth login
   ```

2. **PowerShell** available (Windows — already present)

3. **Kiro IDE** with hooks enabled

---

### Component 1: Local Secret Scanner

**File:** `scripts/scan-secrets-local.ps1`

This is a pure regex scanner that runs offline. It scans git staged files for:

- AWS access keys and secret keys
- Private keys (RSA, EC, DSA, OPENSSH)
- Stripe live keys
- GitHub/GitLab tokens
- Google API keys
- Slack tokens
- Generic secret assignments (password, token, api_key in quotes)
- Connection strings with passwords
- Hardcoded Bearer tokens
- Long JWT tokens

**Behavior:**

- Exit code 0 = clean (no secrets found)
- Exit code 1 = secrets detected (blocks the operation)
- Respects `.gitguardian.yaml` ignored_paths
- Skips binary files, comments, and known safe patterns (env var references, test fixtures)

**Manual run:**

```powershell
./scripts/scan-secrets-local.ps1          # Normal mode
./scripts/scan-secrets-local.ps1 -Verbose # Shows matched line content
```

---

### Component 2: Kiro Pre-commit Hook

**File:** `.kiro/hooks/ggshield-pre-commit.kiro.hook`

```json
{
  "enabled": true,
  "name": "Local Secret Scan (pre-commit)",
  "description": "Syncs auth layer, then runs local regex secret scanner on staged files. No external API calls — designed for spec burst workflows. Blocks commit if secrets found.",
  "version": "4",
  "when": {
    "type": "preToolUse",
    "toolTypes": [".*git_commit.*"]
  },
  "then": {
    "type": "runCommand",
    "command": "powershell -NoProfile -Command \"$src='backend/shared/auth_utils.py'; $dst='backend/layers/auth-layer/python/shared/auth_utils.py'; if((Test-Path $src) -and (Test-Path $dst)){if((Get-FileHash $src).Hash -ne (Get-FileHash $dst).Hash){Copy-Item $src $dst; git add $dst; Write-Host 'Auth layer synced'}}; & ./scripts/scan-secrets-local.ps1; exit $LASTEXITCODE\"",
    "timeout": 15
  }
}
```

**Trigger:** Fires before every `git_commit` MCP tool call (the MCP tool is used instead of shell `git commit` so this hook fires).

**What it does:**

1. Syncs the auth layer (copies `backend/shared/auth_utils.py` → `backend/layers/auth-layer/python/shared/auth_utils.py` if changed)
2. Runs the local secret scanner on staged files
3. Blocks the commit if secrets are found (exit code 1)

**Important:** Commits must use the MCP `git_commit` tool (not `execute_pwsh` with `git commit`) for this hook to fire. This is enforced via steering rules.

---

### Component 3: Native Git Pre-push Hook

**File:** `.githooks/pre-push`

```sh
#!/bin/sh
# Pre-push hook: runs ggshield secret scan before pushing.
# Falls back to local regex scanner if ggshield API quota is exhausted.
# Blocks push if secrets are found.

echo "Running secret scan before push..."

output=$(ggshield secret scan pre-commit 2>&1)
code=$?

if echo "$output" | grep -qiE "no more API calls|quota|rate.limit"; then
    echo "ggshield quota exhausted - falling back to local scanner"
    powershell -NoProfile -File ./scripts/scan-secrets-local.ps1
    exit $?
else
    echo "$output"
    exit $code
fi
```

**Trigger:** Fires on every `git push` — regardless of whether it comes from Kiro, terminal, VS Code, or any other tool.

**What it does:**

1. Runs `ggshield secret scan pre-commit` (API-based, 400+ secret patterns)
2. If ggshield API quota is exhausted, falls back to local scanner
3. Blocks the push if secrets are found (exit code 1)

**Bypass (emergency only):**

```bash
git push --no-verify
```

**Note:** `.git/hooks/` is not tracked by git. Each developer must set up this hook locally, or use a shared hooks directory (see "Sharing the hook" below).

---

### Component 4: CI Scan (GitHub Actions)

**Files:** `.github/workflows/deploy-backend.yml` and `.github/workflows/deploy-frontend.yml`

Both workflows include:

```yaml
- name: Checkout code
  uses: actions/checkout@v4
  with:
    fetch-depth: 2 # Only scan HEAD commit, not full history

- name: Secret scan (ggshield)
  uses: GitGuardian/ggshield-action@v1
  continue-on-error: true # Don't block deploy on quota exhaustion
  env:
    GITGUARDIAN_API_KEY: ${{ secrets.GITGUARDIAN_API_KEY }}
```

**Key settings:**

- `fetch-depth: 2` — scans only the new commit (not the full history, which was burning ~30 API calls per deploy)
- `continue-on-error: true` — deploy isn't blocked if quota is exhausted (pre-push hook already scanned locally)

---

## Sharing the Git Pre-push Hook

The hook lives in `.githooks/pre-push` (tracked by git). New clones need one config command:

```bash
git config core.hooksPath .githooks
```

This tells git to use `.githooks/` instead of `.git/hooks/`. The hook file is versioned and shared automatically.

---

## API Quota Budget

GitGuardian free tier: 10,000 API calls/month.

| Source               | Calls/month (estimated)        |
| -------------------- | ------------------------------ |
| Pre-push (local dev) | ~60 (2 pushes/day × 30 days)   |
| CI deploys           | ~120 (4 deploys/day × 30 days) |
| **Total**            | **~180**                       |

Previous usage before this setup: ~8,400 calls/month (every commit + full-history CI scans).

---

## Troubleshooting

### "no more API calls available"

- Expected behavior — the local scanner takes over automatically
- If persistent: check https://dashboard.gitguardian.com for quota usage
- Multiple projects sharing the same API key all consume from one pool

### Pre-push hook doesn't fire

- Check git is configured: `git config core.hooksPath` should return `.githooks`
- If not configured: run `git config core.hooksPath .githooks`
- Check the hook exists: `cat .githooks/pre-push`

### Local scanner false positives

- Add the file path to `ignored_paths` in `.gitguardian.yaml`
- The local scanner reads this config and respects it

### Kiro pre-commit hook doesn't fire

- Ensure commits use the MCP `git_commit` tool, not shell `git commit`
- Check `.kiro/hooks/ggshield-pre-commit.kiro.hook` has `"enabled": true`
