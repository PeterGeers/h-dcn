# DNS Rollback Runbook

## Overview

Emergency rollback procedure to revert DNS records in Squarespace from the Nonprofit Account endpoints back to the Personal Account endpoints. This runbook must be executable within **5 minutes**.

**Requirements:** 18.5

---

## ⚠️ CRITICAL: Time-Sensitive Procedure

This rollback should complete in under 5 minutes. DNS propagation takes ~60 seconds (TTL was lowered to 60s before cutover).

**Total expected time:** 2-3 minutes for DNS change + 60 seconds propagation + 60 seconds verification = ~5 minutes.

---

## Prerequisites

- Squarespace login credentials available
- Personal Account DNS values documented (from cutover-dns.md Phase 2)
- Internet access to Squarespace admin panel

---

## Rollback DNS Values (Personal Account)

> **FILL THESE IN BEFORE CUTOVER** — Copy from `cutover-dns.md` Phase 2.

| Record Type | Host/Name         | Rollback Value (Personal Account)                |
| ----------- | ----------------- | ------------------------------------------------ |
| CNAME       | api.h-dcn.nl      | `<FILL IN: Personal Account API Gateway domain>` |
| CNAME       | portal.h-dcn.nl   | `<FILL IN: Personal Account CloudFront domain>`  |
| A           | _(if applicable)_ | `<FILL IN>`                                      |

---

## Rollback Steps

### Step 1: Revert DNS Records (Target: 2 minutes)

1. Open browser → [Squarespace DNS Settings](https://account.squarespace.com/)
2. Navigate to: Settings → Domains → h-dcn.nl → DNS Settings
3. For **each record** in the table above:
   - Click Edit on the record
   - Replace the current value (nonprofit endpoint) with the rollback value (personal account endpoint)
   - Save
4. Confirm all records show the Personal Account values

### Step 2: Wait for Propagation (60 seconds)

Wait 60 seconds for DNS caches to expire (TTL was set to 60s).

```powershell
Write-Host "Waiting 60 seconds for DNS propagation..." -ForegroundColor Yellow
Start-Sleep -Seconds 60
```

### Step 3: Verify Rollback (Target: 1 minute)

Run these commands to confirm DNS points back to Personal Account:

```powershell
# Verify DNS resolution
Write-Host "Checking DNS resolution..." -ForegroundColor Cyan
Resolve-DnsName portal.h-dcn.nl -Type CNAME
Resolve-DnsName api.h-dcn.nl -Type CNAME

# Verify frontend is accessible
Write-Host "Checking frontend..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "https://portal.h-dcn.nl" -Method GET -TimeoutSec 10 -UseBasicParsing
    Write-Host "Frontend: HTTP $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Frontend: ERROR - $_" -ForegroundColor Red
}

# Verify API is accessible
Write-Host "Checking API..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "https://api.h-dcn.nl/health" -Method GET -TimeoutSec 10 -UseBasicParsing
    Write-Host "API: HTTP $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "API: May return 4xx for unauthenticated (expected)" -ForegroundColor Yellow
}
```

### Step 4: Confirm Personal Account is Serving Traffic

```powershell
# Verify we're hitting the personal account API Gateway
# The response headers or behavior should match the personal account deployment
aws sts get-caller-identity --profile personal --region eu-west-1
```

---

## Verification Checklist

After rollback, confirm ALL of the following:

- [ ] DNS resolves to Personal Account endpoints (not nonprofit)
- [ ] Frontend loads at https://portal.h-dcn.nl
- [ ] API responds at https://api.h-dcn.nl
- [ ] User login works (test in browser)
- [ ] Data is accessible (members list loads)

---

## Post-Rollback Actions

1. **Document the failure:**
   - What failed during cutover?
   - At what time was the failure detected?
   - What was the error message/behavior?

2. **Keep TTL at 60 seconds** — Do NOT raise TTL until the next cutover attempt succeeds.

3. **Investigate root cause** in the nonprofit deployment:
   - Check CloudWatch Logs in nonprofit account
   - Check API Gateway configuration
   - Check CloudFront distribution status
   - Check Cognito Migration Lambda logs

4. **Fix and re-verify** before attempting cutover again:
   - Run `.\scripts\migration\verify-cutover.ps1` against nonprofit endpoints directly
   - Ensure all integration tests pass

5. **Schedule next cutover attempt** during another low-traffic window.

---

## Troubleshooting

### DNS not propagating after 60 seconds

- Try flushing local DNS cache: `ipconfig /flushdns`
- Check from external resolver: `nslookup portal.h-dcn.nl 8.8.8.8`
- Squarespace may have a minimum TTL — wait up to 5 minutes

### Cannot access Squarespace

- Use mobile browser as backup
- If completely locked out: the 60s TTL means traffic will naturally shift back once Squarespace becomes accessible again (no action needed if records weren't saved)

### Personal Account API not responding after rollback

- Verify Personal Account resources are still running:
  ```powershell
  aws cloudformation describe-stacks --stack-name h-dcn --profile personal --region eu-west-1
  ```
- Check if Lambda functions are still deployed
- Personal Account should be unchanged — it was running in parallel

---

## Timeline Template

| Time    | Action                       | Status |
| ------- | ---------------------------- | ------ |
| T+0     | Failure detected             |        |
| T+1 min | Squarespace DNS panel opened |        |
| T+2 min | DNS records reverted         |        |
| T+3 min | Waiting for propagation      |        |
| T+4 min | Verification started         |        |
| T+5 min | Rollback confirmed           |        |
