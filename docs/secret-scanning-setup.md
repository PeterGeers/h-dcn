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

2. **bash** and **python3** available (Linux/WSL — already present; used by the local scanner and the pre-commit guard)

3. **Kiro IDE** with hooks enabled

---

### Component 1: Local Secret Scanner

**File:** `scripts/scan-secrets-local.sh`

This is a pure regex scanner (bash) that runs offline. It scans git staged files for:

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

```bash
sh scripts/scan-secrets-local.sh            # Normal mode
sh scripts/scan-secrets-local.sh --verbose  # Shows matched line content
```

---

### Component 2: Kiro Pre-commit Hook

**File:** `.kiro/hooks/ggshield-pre-commit.json`

```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "Local Secret Scan (pre-commit)",
      "trigger": "PreToolUse",
      "description": "Syncs auth layer, then runs local regex secret scanner on staged files. Blocks commit if secrets found.",
      "matcher": "execute_pwsh",
      "action": {
        "type": "command",
        "command": "sh scripts/precommit-guard.sh",
        "timeout": 15
      }
    }
  ]
}
```

**Trigger:** `PreToolUse` matching the `execute_pwsh` tool. The bash guard (`scripts/precommit-guard.sh`) reads the tool-call JSON on stdin and only acts when the command contains `git commit`.

**What it does (in `scripts/precommit-guard.sh`):**

1. Exits 0 immediately if the intercepted command is not a `git commit`.
2. Syncs the auth layer (copies `backend/shared/auth_utils.py` → `backend/layers/auth-layer/python/shared/auth_utils.py` if they differ, via `cmp`/`cp`) and stages the layer copy.
3. Runs the local bash secret scanner on staged files and propagates its exit code — a finding blocks the commit.

---

### Component 3: Native Git Pre-push Hook

**File:** `.githooks/pre-push`

The hook scans only the changed files in the push (quota-safe) with ggshield, and
falls back to the local bash scanner (`sh "$REPO_ROOT/scripts/scan-secrets-local.sh"`)
when the ggshield API quota is exhausted or ggshield is not installed. It uses
`#!/bin/sh` and contains no PowerShell. See `.githooks/pre-push` for the current
implementation.

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

- Check `.kiro/hooks/ggshield-pre-commit.json` exists with `matcher: "execute_pwsh"` and `trigger: "PreToolUse"`
- The guard only acts when the intercepted command contains `git commit`; other `execute_pwsh` calls are a no-op
