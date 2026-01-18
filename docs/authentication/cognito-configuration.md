# AWS Cognito Configuration Guide

## Overview

This guide provides comprehensive documentation for the AWS Cognito User Pool configuration used in the H-DCN Portal. The system implements passwordless authentication with Google OAuth integration, passkey support, and role-based access control.

## Architecture

### User Pool Configuration

- **User Pool Name**: H-DCN-Authentication-Pool
- **Region**: eu-west-1
- **User Pool ID**: `eu-west-1_OAT3oPCIm`
- **Authentication Methods**:
  - Google OAuth (All Google accounts)
  - Passkey/WebAuthn (All users)
  - Email verification (Fallback)

### Key Features

- ✅ **Passwordless Authentication**: No passwords required
- ✅ **Multi-Factor Authentication**: Passkey + Email verification
- ✅ **Google Workspace Integration**: Staff SSO via Google OAuth
- ✅ **Role-Based Access Control**: 12 distinct user roles
- ✅ **Dutch Language Support**: All communications in Dutch
- ✅ **Cross-Device Authentication**: Passkey sync across devices

## User Pool Settings

### Basic Configuration

```yaml
# From backend/template.yaml
HDCNCognitoUserPool:
  Type: AWS::Cognito::UserPool
  Properties:
    UserPoolName: H-DCN-Authentication-Pool

    # Passwordless configuration
    Policies:
      PasswordPolicy:
        MinimumLength: 12
        RequireUppercase: false
        RequireLowercase: false
        RequireNumbers: false
        RequireSymbols: false
        TemporaryPasswordValidityDays: 1

    # Email configuration
    EmailConfiguration:
      EmailSendingAccount: COGNITO_DEFAULT
      ReplyToEmailAddress: noreply@h-dcn.nl

    # Account recovery
    AccountRecoverySetting:
      RecoveryMechanisms:
        - Name: verified_email
          Priority: 1
```

### User Attributes

Required attributes for all users:

- **email** (required, mutable)
- **email_verified** (boolean)
- **given_name** (optional)
- **family_name** (optional)
- **custom:member_id** (custom attribute for member linking)

### Authentication Flows

Enabled authentication flows:

- `ALLOW_USER_SRP_AUTH` - Secure Remote Password
- `ALLOW_REFRESH_TOKEN_AUTH` - Token refresh
- `ALLOW_CUSTOM_AUTH` - Custom authentication (for passkeys)

## Identity Providers

### Google OAuth Configuration

```yaml
GoogleIdentityProvider:
  Type: AWS::Cognito::UserPoolIdentityProvider
  Properties:
    UserPoolId: !Ref HDCNCognitoUserPool
    ProviderName: Google
    ProviderType: Google
    ProviderDetails:
      client_id: !Ref GoogleClientId
      client_secret: !Ref GoogleClientSecret
      authorize_scopes: "openid email profile"
    AttributeMapping:
      email: email
      given_name: given_name
      family_name: family_name
```

**Requirements:**

- All Google accounts allowed
- Automatic role assignment based on email domain
- Staff users (`@h-dcn.nl`) get elevated permissions

### Passkey/WebAuthn Configuration

Implemented via custom authentication flow:

- **Relying Party ID**: `h-dcn.nl`
- **Supported Authenticators**: Platform and cross-platform
- **User Verification**: Required
- **Attestation**: None (for broader compatibility)

## User Roles and Groups

### Role Hierarchy

| Precedence | Group Name               | Description                               |
| ---------- | ------------------------ | ----------------------------------------- |
| 5          | System_User_Management   | System administration and user management |
| 10         | Members_CRUD_All         | Full member data management               |
| 15         | Members_Status_Approve   | Approve member status changes             |
| 20         | Members_Read_All         | Read access to all member data            |
| 25         | Events_CRUD_All          | Full event management                     |
| 30         | Events_Read_All          | Read access to events                     |
| 35         | Products_CRUD_All        | Full product/webshop management           |
| 40         | Products_Read_All        | Read access to products                   |
| 45         | Communication_Export_All | Export data and create mailing lists      |
| 50         | Communication_Read_All   | Read communication data                   |
| 55         | System_Logs_Read         | Read system logs and audit trails         |
| 100        | hdcnLeden                | Basic member role (default for all users) |

### Automatic Role Assignment

**Staff Users** (`@h-dcn.nl` emails):

- `System_User_Management`
- `Members_CRUD_All`
- `Events_CRUD_All`
- `Products_CRUD_All`
- `Communication_Export_All`
- `System_Logs_Read`
- `hdcnLeden`

**Regular Members**:

- `hdcnLeden` (assigned automatically)

## Email Templates

### Supported Email Types

1. **Email Verification**

   - Sent during registration
   - 24-hour validity
   - Dutch language

2. **Account Recovery**

   - Passwordless recovery process
   - 1-hour validity
   - Guides to passkey setup

3. **Admin User Invitation**
   - For admin-created accounts
   - 7-day validity
   - Temporary password included

### Template Configuration

```yaml
# Email verification
EmailVerificationMessage: |
  Welkom bij H-DCN! Uw verificatiecode is {####}. 
  Deze code is 24 uur geldig.

EmailVerificationSubject: "H-DCN Account Verificatie"

# Custom message Lambda
CognitoCustomMessageFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: handler/cognito_custom_message/
    Handler: app.lambda_handler
    Runtime: python3.9
```

## Lambda Triggers

### Post-Confirmation Trigger

Automatically assigns roles after user confirmation:

```python
# backend/handler/cognito_post_confirmation/app.py
def lambda_handler(event, context):
    email = event['request']['userAttributes']['email']

    if email.endswith('@h-dcn.nl'):
        # Assign staff roles
        assign_staff_roles(user_pool_id, username)
    else:
        # Assign basic member role
        assign_basic_role(user_pool_id, username)
```

### Custom Message Trigger

Provides Dutch email templates:

```python
# backend/handler/cognito_custom_message/app.py
def lambda_handler(event, context):
    trigger_source = event['triggerSource']

    if trigger_source == 'CustomMessage_SignUp':
        return create_verification_message(event)
    elif trigger_source == 'CustomMessage_ForgotPassword':
        return create_recovery_message(event)
```

## Security Configuration

### Password Policy

```yaml
PasswordPolicy:
  MinimumLength: 12
  RequireUppercase: false
  RequireLowercase: false
  RequireNumbers: false
  RequireSymbols: false
  TemporaryPasswordValidityDays: 1
```

**Note**: Passwords are only used as fallback. Primary authentication is passwordless.

### Account Lockout

```yaml
UserPoolAddOns:
  AdvancedSecurityMode: ENFORCED

DeviceConfiguration:
  ChallengeRequiredOnNewDevice: true
  DeviceOnlyRememberedOnUserPrompt: false
```

### MFA Configuration

- **Primary**: Passkey/WebAuthn (inherent MFA)
- **Fallback**: Email verification codes
- **SMS**: Not configured (email-only approach)

## Deployment

### Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **SAM CLI** installed and configured
3. **Google OAuth credentials** in `.secrets` file
4. **Domain verification** for email sending

### Deployment Steps

1. **Load secrets**:

   ```powershell
   . .\scripts\utilities\load-secrets.ps1
   ```

2. **Deploy infrastructure**:

   ```bash
   cd backend
   sam build
   sam deploy --parameter-overrides \
     GoogleClientId="$env:GOOGLE_CLIENT_ID" \
     GoogleClientSecret="$env:GOOGLE_CLIENT_SECRET"
   ```

3. **Verify deployment**:
   ```bash
   aws cognito-idp describe-user-pool \
     --user-pool-id eu-west-1_OAT3oPCIm \
     --region eu-west-1
   ```

### Post-Deployment Configuration

1. **Domain configuration** (if using custom domain)
2. **Email verification** setup
3. **Test user creation** and role assignment
4. **Frontend configuration** update

## Testing

### Authentication Flow Testing

1. **Google OAuth**:

   ```bash
   # Test Google OAuth redirect
   curl -I "https://accounts.google.com/o/oauth2/v2/auth?client_id=$GOOGLE_CLIENT_ID&redirect_uri=https://h-dcn-auth-344561557829.auth.eu-west-1.amazoncognito.com/oauth2/idpresponse&response_type=code&scope=openid%20email%20profile"
   ```

2. **Passkey Registration**:

   - Navigate to registration page
   - Complete email verification
   - Test passkey creation
   - Verify cross-device sync

3. **Role Assignment**:
   ```python
   # Test role assignment
   python backend/test_automatic_role_assignment.py
   ```

### Email Template Testing

```bash
# Test email delivery
python backend/test_email_templates.py
```

## Monitoring and Logging

### CloudWatch Metrics

- **SignInSuccesses**: Successful authentication attempts
- **SignInThrottles**: Throttled authentication attempts
- **UserRegistrations**: New user registrations
- **TokenRefreshes**: Token refresh operations

### Lambda Function Logs

- **Post-Confirmation**: `/aws/lambda/cognito-post-confirmation`
- **Custom Message**: `/aws/lambda/cognito-custom-message`
- **Role Assignment**: `/aws/lambda/cognito-role-assignment`

### Audit Trail

All user actions are logged with:

- User ID and email
- Action performed
- Timestamp
- IP address
- User agent

## Troubleshooting

### Common Issues

1. **Google OAuth redirect mismatch**:

   - Verify redirect URIs in Google Cloud Console
   - Check Cognito domain configuration

2. **Passkey registration fails**:

   - Verify HTTPS is used
   - Check browser WebAuthn support
   - Verify relying party ID matches domain

3. **Role assignment not working**:

   - Check Lambda function logs
   - Verify IAM permissions
   - Test post-confirmation trigger

4. **Email delivery issues**:
   - Check SES configuration
   - Verify domain verification
   - Check spam folders

### Debug Commands

```bash
# Check user pool configuration
aws cognito-idp describe-user-pool --user-pool-id eu-west-1_OAT3oPCIm

# List identity providers
aws cognito-idp list-identity-providers --user-pool-id eu-west-1_OAT3oPCIm

# Check user groups
aws cognito-idp list-groups --user-pool-id eu-west-1_OAT3oPCIm

# Test Lambda functions
aws lambda invoke --function-name cognito-post-confirmation test-output.json
```

## Maintenance

### Regular Tasks

1. **Monitor authentication metrics**
2. **Review failed login attempts**
3. **Update email templates** as needed
4. **Rotate Google OAuth credentials** annually
5. **Review and update user roles** quarterly

### Backup and Recovery

- **User Pool configuration**: Stored in SAM template (version controlled)
- **User data**: Regular exports via Cognito API
- **Lambda functions**: Source code in Git repository

### Updates and Migrations

1. **Test changes** in development environment
2. **Update SAM template** with new configuration
3. **Deploy via CI/CD pipeline**
4. **Verify functionality** post-deployment
5. **Monitor for issues** in production

## Support

### Documentation References

- [AWS Cognito Developer Guide](https://docs.aws.amazon.com/cognito/latest/developerguide/)
- [WebAuthn Specification](https://www.w3.org/TR/webauthn-2/)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)

### Internal Resources

- `docs/authentication/google-sso-setup.md` - Google OAuth configuration
- `docs/security/secrets-management.md` - Credential management
- `.kiro/specs/cognito-authentication/` - Detailed technical specifications

### Contact Information

- **Technical Issues**: webmaster@h-dcn.nl
- **User Support**: webmaster@h-dcn.nl
- **Security Concerns**: webmaster@h-dcn.nl

---

**Last Updated**: December 29, 2025  
**Version**: Production v2.0  
**Maintained By**: H-DCN Development Team
