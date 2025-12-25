# H-DCN Cognito Email Templates Configuration

## Overview

This document describes the email template configuration for the H-DCN Cognito authentication system. The system uses both built-in Cognito email templates and custom Lambda functions to provide comprehensive, branded email communications in Dutch.

## Email Template Architecture

### 1. Built-in Cognito Templates (SAM Template Configuration)

Located in `backend/template.yaml` under the `HDCNCognitoUserPool` resource:

- **EmailVerificationMessage**: Basic email verification with Dutch text
- **EmailVerificationSubject**: Subject line for verification emails
- **VerificationMessageTemplate**: Comprehensive template for different message types
- **AdminCreateUserConfig**: Templates for admin-created user invitations

### 2. Custom Lambda Templates (Advanced Scenarios)

Two Lambda functions provide advanced email customization:

- **CognitoCustomMessageFunction**: Handles all custom message scenarios
- **CognitoPostConfirmationFunction**: Handles post-confirmation actions

## Supported Email Scenarios

### Basic Verification Emails

- **Trigger**: User registration, email verification
- **Language**: Dutch
- **Content**: Welcome message, verification code, instructions
- **Validity**: 24 hours

### Admin-Created User Invitations

- **Trigger**: Administrator creates user account
- **Language**: Dutch
- **Content**: Welcome message, temporary password, activation instructions
- **Validity**: 7 days

### Password Recovery (Fallback)

- **Trigger**: Password reset request (fallback scenario)
- **Language**: Dutch
- **Content**: Recovery code, security instructions
- **Validity**: 1 hour

### Passwordless Account Recovery

- **Trigger**: Account recovery in passwordless system
- **Language**: Dutch
- **Content**: Passwordless recovery guidance, passkey setup instructions
- **Validity**: 1 hour
- **Features**: Step-by-step recovery process, security benefits explanation

### Account Update Verification

- **Trigger**: User changes email or other verified attributes
- **Language**: Dutch
- **Content**: Change confirmation, verification code
- **Validity**: 24 hours

### Authentication Codes

- **Trigger**: Multi-factor authentication, suspicious activity
- **Language**: Dutch
- **Content**: Login code, security warning
- **Validity**: 3 minutes

## Configuration Parameters

The email templates use environment variables for easy customization:

```yaml
OrganizationName: "Harley-Davidson Club Nederland"
OrganizationWebsite: "https://h-dcn.nl"
OrganizationEmail: "info@h-dcn.nl"
OrganizationShortName: "H-DCN"
SupportPhoneNumber: "+31 (0)20 123 4567"
RecoveryPageUrl: "/recovery"
HelpPageUrl: "/help/passwordless-recovery"
```

## Email Template Features

### Consistent Branding

- H-DCN logo and colors (when supported by email client)
- Consistent footer with organization details
- Professional Dutch language throughout

### Security Features

- Clear validity periods for all codes
- Security warnings for suspicious activity
- Instructions for users who didn't request actions

### User Experience

- Clear, step-by-step instructions
- Friendly, welcoming tone
- Contact information for support

### Passwordless Recovery Features

- Clear explanation of passwordless authentication benefits
- Step-by-step recovery process guidance
- Security warnings and best practices
- Multiple contact options for support
- Customizable URLs and contact information

### Enhanced Security

- Time-limited recovery codes (1 hour validity)
- Clear security warnings for unauthorized requests
- Multiple verification steps
- Guidance away from password-based authentication

## Customization Guide

### Modifying Built-in Templates

Edit the `backend/template.yaml` file:

```yaml
EmailVerificationMessage: |
  Your custom message here with {####} placeholder
EmailVerificationSubject: "Your Custom Subject"
```

### Modifying Lambda Templates

Edit the Lambda function files:

- `backend/handler/cognito_custom_message/app.py`
- `backend/handler/cognito_post_confirmation/app.py`

### Changing Organization Details

Update the parameters in `backend/template.yaml`:

```yaml
Parameters:
  OrganizationName:
    Type: String
    Default: "Your Organization Name"
```

## Deployment

Deploy email template changes using AWS SAM:

```bash
cd backend
sam build
sam deploy
```

## Testing Email Templates

### Manual Testing

1. Create test user account
2. Trigger various authentication scenarios
3. Check email delivery and formatting

### Automated Testing

- Lambda function logs show email content
- CloudWatch logs track email delivery
- Test different trigger scenarios

## Troubleshooting

### Common Issues

1. **Emails not delivered**

   - Check SES configuration
   - Verify email addresses are not in sandbox mode
   - Check spam folders

2. **Template formatting issues**

   - Verify YAML formatting in SAM template
   - Check Lambda function syntax
   - Review CloudWatch logs for errors

3. **Missing environment variables**
   - Verify parameter values in SAM template
   - Check Lambda function environment configuration
   - Redeploy if parameters changed

### Monitoring

- **CloudWatch Logs**: Monitor Lambda function execution
- **Cognito Metrics**: Track email delivery rates
- **User Feedback**: Monitor support requests for email issues

## Security Considerations

### Email Content Security

- No sensitive data in email templates
- Clear instructions for legitimate vs. suspicious activity
- Contact information for security concerns

### Code Security

- Input validation in Lambda functions
- Error handling to prevent information disclosure
- Logging for audit trails

### Compliance

- GDPR-compliant language and opt-out instructions
- Clear data usage explanations
- Privacy policy references

## Account Recovery Template Features

### Passwordless-First Approach

The account recovery templates are specifically designed for passwordless authentication:

- **No password reset**: Templates guide users to set up new authentication methods instead of resetting passwords
- **Passkey promotion**: Clear explanation of passkey benefits and setup process
- **Email fallback**: Alternative email-based authentication for devices without WebAuthn support
- **Security education**: Templates explain why passwordless is more secure

### Recovery Process Flow

1. **User requests account recovery**
2. **System sends recovery email with time-limited code**
3. **User verifies identity with recovery code**
4. **System guides user through new authentication setup**
5. **User gains immediate access with new authentication method**

### Template Customization

Account recovery templates support extensive customization through SAM template parameters:

```yaml
# Organization branding
OrganizationName: "Your Organization"
OrganizationWebsite: "https://your-site.com"
OrganizationEmail: "support@your-site.com"

# Recovery-specific settings
SupportPhoneNumber: "+31 (0)20 123 4567"
RecoveryPageUrl: "/custom-recovery"
HelpPageUrl: "/help/recovery-guide"
```

### Multi-Language Support

Currently supports Dutch language with plans for:

- English templates
- German templates
- Automatic language detection based on user preferences

## Future Enhancements

### Planned Features

- HTML email templates with rich formatting
- Multi-language support (English, German)
- Email template A/B testing
- Integration with external email marketing platforms

### Extensibility

- Additional trigger scenarios
- Custom branding per user group
- Dynamic content based on user attributes
- Integration with CRM systems

## Support

For email template issues or customization requests:

- Technical issues: Check CloudWatch logs
- Content changes: Update SAM template or Lambda functions
- Deployment issues: Verify SAM CLI configuration
- User experience feedback: Monitor support channels
