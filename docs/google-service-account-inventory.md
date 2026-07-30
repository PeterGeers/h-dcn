# Google Service Account Inventory

## Active Service Account

| Field             | Value                                                          |
| ----------------- | -------------------------------------------------------------- |
| Email             | `hdcn-portal@hdcn-portal.iam.gserviceaccount.com`              |
| Project           | `hdcn-portal`                                                  |
| Project Number    | `1081576340476`                                                |
| Display Name      | hdcn-portal                                                    |
| Key File          | `.googleCredentials.json` (project root, gitignored)           |
| Key Expiry Policy | 90 days (org policy `iam.serviceAccountKeyExpiryHours = 2160`) |

## Authorized Scopes

| Scope                   | Used By                         |
| ----------------------- | ------------------------------- |
| `spreadsheets.readonly` | gspread (ledenbestand sync)     |
| `drive.readonly`        | Drive file listing              |
| `drive.file`            | Drive shared drive access       |
| `calendar`              | Calendar event sync (local dev) |
| `calendar.readonly`     | Calendar read operations        |

## Granted Roles

- Workload Identity User (for WIF from AWS Lambda)

## Key Rotation Procedure

1. Generate new key:

   ```bash
   gcloud iam service-accounts keys create .googleCredentials.json \
     --iam-account=hdcn-portal@hdcn-portal.iam.gserviceaccount.com
   ```

2. Verify connectivity:

   ```bash
   python scripts/verify_google_sa.py
   ```

3. If all checks pass, delete the old key from GCP console or:

   ```bash
   gcloud iam service-accounts keys list \
     --iam-account=hdcn-portal@hdcn-portal.iam.gserviceaccount.com \
     --filter="keyType=USER_MANAGED"
   # Delete the old key ID:
   gcloud iam service-accounts keys delete <OLD_KEY_ID> \
     --iam-account=hdcn-portal@hdcn-portal.iam.gserviceaccount.com
   ```

4. Confirm the new key is the only USER_MANAGED key remaining.

## Rotation Schedule

- **Manual setup required**: Create a recurring Google Calendar event on your personal calendar
- Frequency: every 83 days (7 days before 90-day expiry)
- Title: "Rotate .googleCredentials.json key"
- Description: "Key rotation reminder. Steps: 1) generate new key, 2) run verify_google_sa.py, 3) delete old key. See docs/google-service-account-inventory.md"
- First occurrence: approximately 83 days after key creation date

## Notes

- The org policy enforces 90-day max lifetime on new keys
- Keys created before the policy was set may show `9999-12-31` expiry — delete and recreate these
- Google Photos uploads use a separate OAuth token (SSM parameter `/h-dcn/google-photos-oauth`) — NOT this service account
- WIF (Workload Identity Federation) is used for Lambda → Google Calendar sync in production — no key file involved there
