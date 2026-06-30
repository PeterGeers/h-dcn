# Email Architecture — H-DCN

## Overview

H-DCN uses **AWS SES** (Simple Email Service) for all outgoing email, delivered exclusively through **Cognito Custom Message triggers**. There are no direct SES API calls or SMTP/Gmail integrations for sending mail.

Google integration exists in the project but is limited to **Google Sheets data import** (member records), not email.

---

## AWS SES — Transactional Email

### How it works

```
User action (login, signup, recovery)
    ↓
AWS Cognito triggers CustomMessage Lambda
    ↓
cognito_custom_message handler customizes subject + body
    ↓
Cognito delivers the email via SES
```

SES is not called directly by any handler. Cognito owns the email delivery; the Lambda function only controls the **content**.

### From address

`webhulpje@h-dcn.nl` (configured via `ORGANIZATION_EMAIL` environment variable)

### Handler

`backend/handler/cognito_custom_message/app.py`

### Email types

| Trigger Source                      | Purpose                            | Template ID             |
| ----------------------------------- | ---------------------------------- | ----------------------- |
| `CustomMessage_AdminCreateUser`     | Welcome message with temp password | `welcome-user`          |
| `CustomMessage_ResendCode`          | Resend verification code           | `resend-code`           |
| `CustomMessage_ForgotPassword`      | Passwordless account recovery      | `passwordless-recovery` |
| `CustomMessage_UpdateUserAttribute` | Email change verification          | `update-user-attribute` |
| `CustomMessage_VerifyUserAttribute` | Attribute verification             | `verify-user-attribute` |
| `CustomMessage_Authentication`      | OTP login code delivery            | `authentication`        |
| Recovery-related triggers           | Passwordless recovery flow         | `passwordless-recovery` |
| Unrecognized triggers               | Generic fallback                   | `default-message`       |

### Template system

- Templates stored in S3 bucket: `h-dcn-email-templates` (defined as `EmailTemplatesBucket` in SAM template)
- Template service: `backend/handler/cognito_custom_message/template_service.py`
- Locales supported: **nl, en, de, fr, es, it, da, sv** (8 languages)
- Template files: `backend/email-templates/templates/{locale}/`
- Shared variables: `backend/email-templates/config/variables.json`
- Locale resolution: `shared.i18n.email_utils.resolve_email_locale()` — uses `clientMetadata.locale` from frontend, falls back to Dutch

### Fallback behavior

If S3 template rendering fails, each handler has an **inline Dutch fallback** hardcoded in the Python function. This ensures emails are always delivered even if S3 is unavailable.

### IAM permissions (SAM template)

The `CognitoCustomMessageFunction` role includes:

- `ses:SendEmail`
- `ses:SendRawEmail`
- `s3:GetObject` on the email templates bucket
- `s3:ListBucket` on the email templates bucket

---

## Google Integration — Sheets Only (NOT Gmail)

### Purpose

Google API is used exclusively for **importing member data from Google Sheets** into DynamoDB. It is NOT used for sending email.

### Components

| Script                                      | Purpose                                                                  |
| ------------------------------------------- | ------------------------------------------------------------------------ |
| `backend/scripts/import_members_sheets.py`  | Import member records from "Ledenbestand" spreadsheet into Members table |
| `backend/scripts/debug_sheet_headers.py`    | Debug utility for inspecting sheet column headers                        |
| `backend/scripts/test_google_connection.py` | Validate Google API credentials and sheet access                         |

### Authentication

- Library: `gspread` + `google.oauth2.service_account`
- Credentials file: `.googleCredentials.json` (project root, gitignored)
- Scopes: Google Sheets read access

### Important

- No Gmail API usage
- No SMTP sending
- No Google mail integration
- The `@gmail.com` addresses in test scripts are just test user email addresses in Cognito, not related to Gmail sending

---

## Summary Table

| Purpose                                         | Service           | Method                                        |
| ----------------------------------------------- | ----------------- | --------------------------------------------- |
| Transactional emails (codes, welcome, recovery) | AWS SES           | Cognito Custom Message trigger → SES delivers |
| Member data import from spreadsheet             | Google Sheets API | `gspread` with service account credentials    |
| Direct email sending (SMTP/Gmail)               | ❌ Not used       | —                                             |
| Marketing/bulk email                            | ❌ Not used       | —                                             |

---

## Configuration References

- SAM template parameters: `OrganizationName`, `OrganizationEmail`, `OrganizationWebsite`, `OrganizationShortName`
- Environment variables on the Lambda: `ORGANIZATION_NAME`, `ORGANIZATION_EMAIL`, `ORGANIZATION_WEBSITE`, `ORGANIZATION_SHORT_NAME`, `EMAIL_TEMPLATES_BUCKET`, `RECOVERY_URL`, `HELP_URL`, `SUPPORT_PHONE`
- Cognito User Pool: `eu-west-1_fcUkvwjH5` (triggers attached via SAM template)
