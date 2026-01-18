# H-DCN Email System Documentation

## Overview

The H-DCN portal uses a centralized email system built on AWS SES with S3-based template management. This system supports automated emails for membership applications, webshop orders, and other business processes.

## Architecture

### Backend Components

- **Template Service**: `backend/handler/cognito_custom_message/template_service.py`
- **Email Templates**: `backend/email-templates/templates/*.html`
- **Template Variables**: `backend/email-templates/config/variables.json`
- **SES Integration**: AWS Simple Email Service for delivery

### Frontend Components

- **Generic Email Service**: `frontend/src/utils/emailService.ts`
- **Email Configuration**: Embedded in relevant config files (e.g., `memberFields.ts`)

## Email Templates

### Existing Templates

- `welcome-user.html` - New user account creation
- `resend-code.html` - Email verification codes
- `passwordless-recovery.html` - Account recovery
- `membership-application-confirmation.html` - Member application confirmation
- `membership-application-admin-notification.html` - Admin notification for new applications

### Template Variables

All templates support these standard variables from `variables.json`:

- `{{ORGANIZATION_NAME}}` - "Harley-Davidson Club Nederland"
- `{{ORGANIZATION_SHORT_NAME}}` - "H-DCN"
- `{{ORGANIZATION_WEBSITE}}` - "https://portal.h-dcn.nl"
- `{{ORGANIZATION_EMAIL}}` - "webhulpje@h-dcn.nl"
- `{{RECOVERY_URL}}` - Recovery page URL
- `{{HELP_URL}}` - Help page URL
- `{{SUPPORT_PHONE}}` - Support contact

### Custom Context Variables

Templates can also use context-specific variables passed at runtime:

- `{{DISPLAY_NAME}}` - User's display name
- `{{EMAIL}}` - User's email address
- `{{APPLICATION_DATE}}` - Formatted application date
- Plus any custom variables for specific use cases

## Usage Examples

### Membership Applications

**Configuration**: `frontend/src/config/memberFields.ts`

```typescript
export const MEMBERSHIP_EMAIL_CONFIG: EmailNotificationConfig = {
  enabled: true,
  templates: {
    applicantConfirmation: "membership-application-confirmation",
    adminNotification: "membership-application-admin-notification",
  },
  recipients: {
    admin: ["ledenadministratie@h-dcn.nl"],
  },
  triggers: {
    onSubmission: true,
    onStatusChange: true,
    onApproval: true,
  },
};
```

**Usage**: `frontend/src/utils/membershipService.ts`

```typescript
import { emailService } from './emailService';

await emailService.sendEmail({
  template: 'membership-application-confirmation',
  recipient: applicantEmail,
  context: { DISPLAY_NAME: 'John Doe', ... }
});
```

### Webshop Orders (Future)

**Configuration**: `frontend/src/config/webshopFields.ts`

```typescript
export const WEBSHOP_EMAIL_CONFIG = {
  enabled: true,
  templates: {
    orderConfirmation: "order-confirmation",
    orderShipped: "order-shipped",
    adminOrderNotification: "admin-order-notification",
  },
  recipients: {
    admin: ["orders@h-dcn.nl"],
    bcc: ["audit@h-dcn.nl"],
  },
};
```

## Generic Email Service API

### Core Methods

#### `sendEmail(options)`

Generic method for sending any email:

```typescript
await emailService.sendEmail({
  template: "template-name",
  recipient: "user@example.com",
  cc: ["cc@example.com"],
  bcc: ["bcc@example.com"],
  context: { CUSTOM_VAR: "value" },
});
```

#### `sendBulkEmails(emails)`

Send multiple emails efficiently:

```typescript
await emailService.sendBulkEmails([
  { template: 'newsletter', recipient: 'user1@example.com', context: {...} },
  { template: 'newsletter', recipient: 'user2@example.com', context: {...} }
]);
```

#### `sendTemplatedEmail(templateName, recipients, context)`

Simplified method for common use cases:

```typescript
await emailService.sendTemplatedEmail(
  "membership-application-confirmation",
  ["user@example.com"],
  { DISPLAY_NAME: "John Doe", APPLICATION_DATE: "2024-01-15" }
);
```

## Configuration Pattern

### Email Configuration Interface

```typescript
interface EmailNotificationConfig {
  enabled: boolean;
  templates: Record<string, string>;
  recipients: {
    admin: string[];
    cc?: string[];
    bcc?: string[];
  };
  triggers: Record<string, boolean>;
}
```

### Module-Specific Configuration

Each module defines its own email configuration:

- **Membership**: `MEMBERSHIP_EMAIL_CONFIG` in `memberFields.ts`
- **Webshop**: `WEBSHOP_EMAIL_CONFIG` in `webshopConfig.ts` (future)
- **Events**: `EVENT_EMAIL_CONFIG` in `eventConfig.ts` (future)

## File Structure

```
backend/
├── email-templates/
│   ├── config/
│   │   └── variables.json                    # Global template variables
│   └── templates/
│       ├── welcome-user.html                 # User account creation
│       ├── resend-code.html                  # Email verification
│       ├── passwordless-recovery.html        # Account recovery
│       ├── membership-application-confirmation.html
│       └── membership-application-admin-notification.html
├── handler/
│   ├── cognito_custom_message/
│   │   ├── app.py                           # Cognito email handler
│   │   └── template_service.py              # S3 template service
│   └── hdcn_cognito_admin/
│       └── template_service.py              # Admin template service
└── test_ses_email_delivery.py              # Email system testing

frontend/
├── src/
│   ├── config/
│   │   └── memberFields.ts                  # Membership email config
│   └── utils/
│       ├── emailService.ts                  # Generic email service
│       └── membershipService.ts             # Membership-specific usage
└── .kiro/specs/
    └── email-system.md                      # This documentation
```

## Testing

### Backend Testing

- `backend/test_ses_email_delivery.py` - Comprehensive SES testing
- `backend/test_email_templates.py` - Template rendering tests
- `backend/validate_templates.py` - Template validation

### Email Delivery Testing

```bash
cd backend
python test_ses_email_delivery.py
```

## Best Practices

### Template Design

1. **Responsive HTML**: Use table-based layouts for email compatibility
2. **Inline CSS**: Email clients don't support external stylesheets
3. **Fallback Text**: Always provide plain text alternatives
4. **Brand Consistency**: Use H-DCN colors and styling

### Configuration Management

1. **Module Separation**: Each module manages its own email config
2. **Feature Flags**: Use `enabled` and trigger flags for easy control
3. **Environment Specific**: Different configs for dev/staging/production
4. **Audit Trail**: Use BCC for compliance and record keeping

### Error Handling

1. **Graceful Degradation**: Application should work even if emails fail
2. **Retry Logic**: Implement retry for transient failures
3. **Logging**: Comprehensive logging for debugging
4. **Monitoring**: Track email delivery rates and failures

## Future Enhancements

### Planned Features

- **Email Queue**: Background processing for bulk emails
- **Template Editor**: Web-based template editing interface
- **Analytics**: Email open/click tracking
- **Personalization**: Advanced template personalization
- **Scheduling**: Delayed and scheduled email sending

### Additional Templates Needed

- Order confirmation and shipping notifications
- Event registration confirmations
- Newsletter templates
- Membership renewal reminders
- Payment failure notifications

## Security Considerations

### Email Security

- **SPF/DKIM**: Proper email authentication setup
- **Rate Limiting**: Prevent email abuse
- **Content Filtering**: Validate email content
- **PII Protection**: Handle personal data appropriately

### Access Control

- **Template Access**: Restrict template modification
- **Recipient Lists**: Validate email addresses
- **Admin Notifications**: Secure admin email addresses
- **Audit Logging**: Track all email sending activity

## Troubleshooting

### Common Issues

1. **Templates not loading**: Check S3 bucket permissions
2. **Variables not replacing**: Verify variable names match exactly
3. **Emails not sending**: Check SES configuration and limits
4. **Formatting issues**: Test templates across email clients

### Debug Commands

```bash
# Test SES connectivity
python backend/test_ses_email_delivery.py

# Validate templates
python backend/validate_templates.py

# Test template rendering
python backend/test_email_templates.py
```
