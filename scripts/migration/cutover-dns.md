# DNS Cutover Runbook

## Overview

This runbook documents the DNS cutover procedure for migrating h-dcn from the Personal Account (344561557829) to the Nonprofit Account (506221081911). DNS is managed in Squarespace — no DNS provider migration is needed, only record value changes.

**Requirements:** 18.1, 18.2, 18.3, 18.4, 18.5

---

## Prerequisites

- [ ] Nonprofit deployment verified end-to-end (all Phase 6 checks pass)
- [ ] Data migration verified (all 7 DynamoDB tables + S3 objects match)
- [ ] Cognito Migration Lambda Trigger tested with at least one user
- [ ] Squarespace DNS panel access confirmed
- [ ] Rollback runbook reviewed (`scripts/migration/rollback-dns.md`)
- [ ] Verification script tested (`scripts/migration/verify-cutover.ps1`)

---

## Phase 1: Lower DNS TTL (24 hours before cutover)

**When:** At least 24 hours before the planned cutover window.

### Steps

1. Log in to Squarespace → Settings → Domains → portal.h-dcn.nl → DNS Settings
2. For each record that will change (see Current DNS Records below), lower the TTL to **60 seconds**
3. Verify the TTL change has propagated:
   ```powershell
   # Check TTL from multiple resolvers
   nslookup -type=A portal.h-dcn.nl 8.8.8.8
   nslookup -type=CNAME portal.h-dcn.nl 1.1.1.1
   ```
4. Wait 24 hours for old cached records (with higher TTL) to expire

### Verification

- [ ] TTL shows 60 seconds in Squarespace DNS panel
- [ ] External DNS lookup confirms low TTL

---

## Phase 2: Document Current DNS Records (for rollback)

**IMPORTANT:** Record these values BEFORE making any changes. These are needed for rollback.

### Current DNS Records (Personal Account)

| Record Type | Host/Name         | Value (Personal Account)                | TTL |
| ----------- | ----------------- | --------------------------------------- | --- |
| CNAME       | api.h-dcn.nl      | `<FILL IN: current API Gateway domain>` | 60s |
| CNAME       | portal.h-dcn.nl   | `<FILL IN: current CloudFront domain>`  | 60s |
| A           | _(if applicable)_ | `<FILL IN>`                             | 60s |

> **Action:** Fill in the actual values from Squarespace before proceeding to Phase 3.
> Copy these values to `scripts/migration/rollback-dns.md` as well.

---

## Phase 3: Execute DNS Cutover

**When:** During a low-traffic window (recommended: weekday morning, 08:00-09:00 CET).

### Nonprofit Account Endpoints

| Record Type | Host/Name       | New Value (Nonprofit Account)                         |
| ----------- | --------------- | ----------------------------------------------------- |
| CNAME       | api.h-dcn.nl    | `<FILL IN: nonprofit API Gateway custom domain>`      |
| CNAME       | portal.h-dcn.nl | `<FILL IN: nonprofit CloudFront distribution domain>` |

### Steps

1. Open Squarespace → Settings → Domains → portal.h-dcn.nl → DNS Settings
2. Update each record to point to the nonprofit endpoints (see table above)
3. Save changes
4. Note the exact time of change: `__________ (UTC)`
5. Immediately run the verification script:
   ```powershell
   .\scripts\migration\verify-cutover.ps1
   ```

---

## Phase 4: 5-Minute Monitoring Checklist

Start a timer immediately after DNS change. Check each item every minute for 5 minutes.

| Time   | DNS Resolves to Nonprofit? | API Health Check? | Frontend Loads? | Login Works? | Action |
| ------ | -------------------------- | ----------------- | --------------- | ------------ | ------ |
| +1 min | ☐                          | ☐                 | ☐               | ☐            |        |
| +2 min | ☐                          | ☐                 | ☐               | ☐            |        |
| +3 min | ☐                          | ☐                 | ☐               | ☐            |        |
| +4 min | ☐                          | ☐                 | ☐               | ☐            |        |
| +5 min | ☐                          | ☐                 | ☐               | ☐            |        |

### Quick Check Commands

```powershell
# DNS resolution check
Resolve-DnsName portal.h-dcn.nl -Type CNAME
Resolve-DnsName api.h-dcn.nl -Type CNAME

# API health check
Invoke-WebRequest -Uri "https://api.h-dcn.nl/health" -Method GET -TimeoutSec 10

# Frontend check
Invoke-WebRequest -Uri "https://portal.h-dcn.nl" -Method GET -TimeoutSec 10
```

### Decision Point (at +5 minutes)

- **All checks pass:** Cutover successful. Continue monitoring for 24 hours.
- **Any check fails:** Execute rollback immediately. See Phase 5.

---

## Phase 5: Rollback Procedure

**Trigger:** Any failure detected during the 5-minute monitoring window.

**Target:** Complete rollback within 5 minutes (enabled by 60-second TTL).

### Steps

1. Follow the rollback runbook: `scripts/migration/rollback-dns.md`
2. Revert all DNS records in Squarespace to the Personal Account values (documented in Phase 2)
3. Wait 60 seconds for DNS propagation
4. Verify Personal Account is serving traffic:
   ```powershell
   Resolve-DnsName portal.h-dcn.nl -Type CNAME
   Invoke-WebRequest -Uri "https://portal.h-dcn.nl" -Method GET -TimeoutSec 10
   ```
5. Investigate the failure before attempting cutover again

### Post-Rollback

- [ ] Document what failed and why
- [ ] Fix the issue in the nonprofit deployment
- [ ] Re-verify end-to-end before next cutover attempt
- [ ] Keep TTL at 60 seconds for the next attempt

---

## Post-Cutover (after successful 5-minute window)

- [ ] Monitor for 24 hours — check CloudWatch dashboard in nonprofit account
- [ ] Verify Cognito Migration Lambda is handling user sign-ins correctly
- [ ] Keep Personal Account running in parallel for 7 days
- [ ] After 7 days of stable operation: proceed to decommissioning phase
- [ ] Restore DNS TTL to normal value (3600 seconds) after 7-day verification period

---

## Emergency Contacts

| Role          | Contact | Responsibility                             |
| ------------- | ------- | ------------------------------------------ |
| Administrator | Peter   | DNS changes, AWS access, rollback decision |

---

## Revision History

| Date      | Change                   | Author |
| --------- | ------------------------ | ------ |
| _(today)_ | Initial runbook creation | Kiro   |
