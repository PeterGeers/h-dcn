#!/usr/bin/env bash
#
# Local secret scanner — fallback when ggshield API quota is exhausted.
# No external API calls. Pure regex pattern matching on staged files.
#
# Bash port of scripts/scan-secrets-local.ps1. Behaviour is intentionally
# identical: scans git-staged files for common secret patterns and returns
# exit code 1 if secrets are found, 0 if clean. Respects .gitguardian.yaml
# ignored_paths.
#
# Patterns detected:
#   - AWS access keys (AKIA...) and secret keys
#   - Private keys (RSA, EC, DSA, OPENSSH)
#   - Stripe keys (sk_live_, pk_live_)
#   - GitHub / GitLab tokens
#   - Google API keys
#   - Slack tokens
#   - Generic secret/password/token assignments
#   - Connection-string passwords
#   - Bearer tokens
#   - Base64 JWTs (eyJ...)
#
# NOTE: This is NOT a replacement for ggshield — it catches ~80% of common
# leaks. Use alongside ggshield when the API is available.

set -uo pipefail

VERBOSE=0
if [ "${1:-}" = "-v" ] || [ "${1:-}" = "--verbose" ]; then
    VERBOSE=1
fi

# --- Secret patterns (name | POSIX ERE | case-insensitive flag) ---
# Each entry: "Name|||regex|||ci"  (ci = 1 for case-insensitive)
patterns=(
    "AWS Access Key ID|||AKIA[0-9A-Z]{16}|||0"
    "AWS Secret Access Key|||(aws_secret_access_key|aws_secret_key|secret_key)[[:space:]]*[=:][[:space:]]*[A-Za-z0-9/+=]{40}|||1"
    "Private Key|||-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----|||0"
    "Stripe Secret Key|||sk_live_[0-9a-zA-Z]{24,}|||0"
    "Stripe Publishable Key|||pk_live_[0-9a-zA-Z]{24,}|||0"
    "GitHub Token|||(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}|||0"
    "GitLab Token|||glpat-[A-Za-z0-9-]{20,}|||0"
    "Google API Key|||AIza[0-9A-Za-z_-]{35}|||0"
    "Slack Token|||xox[bpors]-[0-9a-zA-Z-]{10,}|||0"
    "Generic Secret Assignment|||(secret|password|passwd|token|api_key|apikey|auth_token)[[:space:]]*[=:][[:space:]]*[\"'][A-Za-z0-9/+=_-]{8,}[\"']|||1"
    "Connection String Password|||(password|pwd)[[:space:]]*=[[:space:]]*[\"'][^;\"'[:space:]]{8,}[\"']|||1"
    "Bearer Token (hardcoded)|||bearer[[:space:]]+[A-Za-z0-9._~+/-]{20,}=*|||1"
    "Base64 JWT (long)|||eyJ[A-Za-z0-9_-]{50,}\.[A-Za-z0-9_-]{50,}\.[A-Za-z0-9_-]{50,}|||0"
)

# --- Ignored paths: default plus ignored_paths from .gitguardian.yaml ---
ignored_patterns=("scripts/scan-secrets-local.sh" "scripts/scan-secrets-local.ps1")

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -n "$repo_root" ] && [ -f "$repo_root/.gitguardian.yaml" ]; then
    in_ignored=0
    while IFS= read -r line; do
        if printf '%s' "$line" | grep -qE '^[[:space:]]*ignored_paths:'; then
            in_ignored=1
            continue
        fi
        if [ "$in_ignored" -eq 1 ]; then
            if printf '%s' "$line" | grep -qE '^[[:space:]]+-[[:space:]]+'; then
                val=$(printf '%s' "$line" | sed -E 's/^[[:space:]]+-[[:space:]]+//; s/["'"'"']//g')
                val=$(printf '%s' "$val" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
                [ -n "$val" ] && ignored_patterns+=("$val")
            elif printf '%s' "$line" | grep -qE '^[^[:space:]#]'; then
                in_ignored=0
            fi
        fi
    done < "$repo_root/.gitguardian.yaml"
fi

# Convert a glob-ish ignore pattern to an ERE and test a file path.
# Mirrors the PowerShell version: * -> .* and ? -> . (no other escaping),
# which is sufficient for the simple globs used in .gitguardian.yaml.
is_ignored() {
    local file="$1" pat re
    for pat in "${ignored_patterns[@]}"; do
        re=$(printf '%s' "$pat" | sed 's/\*/.*/g; s/?/./g')
        if printf '%s' "$file" | grep -Eq -- "$re" 2>/dev/null; then
            return 0
        fi
    done
    return 1
}

# --- Binary extensions to skip ---
binary_exts="png jpg jpeg gif webp ico pdf zip tar gz woff woff2 ttf eot xlsx xls"
is_binary_ext() {
    local ext="${1##*.}"
    ext=$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')
    case " $binary_exts " in
        *" $ext "*) return 0 ;;
        *) return 1 ;;
    esac
}

# --- Get staged files ---
staged=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
if [ -z "$staged" ]; then
    [ "$VERBOSE" -eq 1 ] && echo "No staged files to scan."
    exit 0
fi

findings=0
findings_out=""

while IFS= read -r file; do
    [ -z "$file" ] && continue
    is_ignored "$file" && continue
    is_binary_ext "$file" && continue

    content=$(git show ":$file" 2>/dev/null || true)
    [ -z "$content" ] && continue

    line_no=0
    while IFS= read -r cline; do
        line_no=$((line_no + 1))

        # Skip comment lines
        printf '%s' "$cline" | grep -qE '^[[:space:]]*(#|//|/\*|\*)' && continue
        # Skip obvious placeholders / test fixtures
        printf '%s' "$cline" | grep -qiE 'example|placeholder|dummy|test.*token|fake|mock' && continue
        # Skip field/variable names that merely contain "password"
        printf '%s' "$cline" | grep -qE 'event_password|user_password|password_hash|hash_password|checkpw|hashpw|verify_password' && continue

        for entry in "${patterns[@]}"; do
            name="${entry%%|||*}"
            rest="${entry#*|||}"
            regex="${rest%%|||*}"
            ci="${rest##*|||}"

            matched=0
            if [ "$ci" -eq 1 ]; then
                printf '%s' "$cline" | grep -Eiq -- "$regex" && matched=1
            else
                printf '%s' "$cline" | grep -Eq -- "$regex" && matched=1
            fi

            if [ "$matched" -eq 1 ]; then
                # Skip clear variable/env references, not literals
                if printf '%s' "$cline" | grep -Eq '\$\{|\$\(|process\.env|os\.environ|getenv'; then
                    continue
                fi

                findings=$((findings + 1))
                snippet=$(printf '%s' "$cline" | sed -E 's/^[[:space:]]+//')
                if [ "${#snippet}" -gt 100 ]; then
                    snippet="${snippet:0:100}..."
                fi
                findings_out="${findings_out}  ${file}:${line_no} [${name}]"$'\n'
                if [ "$VERBOSE" -eq 1 ]; then
                    findings_out="${findings_out}    ${snippet}"$'\n'
                fi
            fi
        done
    done <<< "$content"
done <<< "$staged"

# --- Report ---
if [ "$findings" -eq 0 ]; then
    echo "No new secrets have been found"
    exit 0
else
    echo ""
    echo "====== SECRETS DETECTED ======"
    echo "$findings potential secret(s) found in staged files:"
    echo ""
    printf '%s' "$findings_out"
    echo ""
    echo "Commit blocked. Remove secrets before committing."
    echo "If these are false positives, add the file to ignored_paths in .gitguardian.yaml"
    exit 1
fi
