# Authentication Troubleshooting Guide

## Overview

This guide provides solutions for common authentication issues in the H-DCN Portal. It covers Google OAuth, Passkey authentication, and general Cognito-related problems.

## Quick Diagnosis

### Authentication Flow Check

1. **Check browser console** for JavaScript errors
2. **Verify network requests** in browser DevTools
3. **Check user's email domain** (@h-dcn.nl vs others)
4. **Test WebAuthn support** in browser
5. **Verify Cognito configuration** in AWS Console

### Common Error Patterns

| Error Message               | Likely Cause                    | Quick Fix                   |
| --------------------------- | ------------------------------- | --------------------------- |
| `redirect_uri_mismatch`     | Google OAuth misconfiguration   | Check redirect URIs         |
| `NotAllowedError`           | User cancelled biometric prompt | Retry authentication        |
| `TimeoutError`              | Authentication timeout          | Increase timeout for mobile |
| `NotSupportedError`         | WebAuthn not supported          | Use email fallback          |
| `InvalidParameterException` | Cognito attribute issue         | Check custom attributes     |

## Google OAuth Issues

### 1. Redirect URI Mismatch

**Error**: `redirect_uri_mismatch` or `Error 400: redirect_uri_mismatch`

**Symptoms**:

- User redirected to Google error page
- OAuth flow fails at Google authorization step
- Error mentions invalid redirect URI

**Diagnosis**:

```bash
# Check current redirect URIs in Google Cloud Console
# Should include:
# - https://h-dcn-auth-344561557829.auth.eu-west-1.amazoncognito.com/oauth2/idpresponse
# - https://de1irtdutlxqu.cloudfront.net/auth/callback
```

**Solution**:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services > Credentials**
3. Edit OAuth 2.0 Client ID
4. Add missing redirect URIs:
   ```
   https://h-dcn-auth-344561557829.auth.eu-west-1.amazoncognito.com/oauth2/idpresponse
   https://de1irtdutlxqu.cloudfront.net/auth/callback
   ```
5. Save changes and test

### 2. Access Denied for Users

**Error**: "Geen toegang" or "Access Denied"

**Symptoms**:

- Users can't authenticate via Google
- OAuth flow completes but user is rejected
- User sees access denied message

**Diagnosis**:

```javascript
// Check user's email domain in browser console
console.log("User email:", user.email);
console.log("Is staff:", user.email.endsWith("@h-dcn.nl"));
```

**Solution**:
Check if there are any application-level restrictions or authentication flow issues.

**If access is denied**:

1. Check application logs for specific error details
2. Verify Google OAuth configuration
3. Test with different Google account
4. Alternative: Use passkey authentication instead

### 3. Invalid Client Error

**Error**: `invalid_client` or client authentication failed

**Symptoms**:

- OAuth flow fails immediately
- Google returns client error
- No authorization prompt shown

**Diagnosis**:

```bash
# Verify Google credentials are correctly deployed
aws cognito-idp describe-identity-provider \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --provider-name Google \
  --region eu-west-1
```

**Solution**:

1. Check `.secrets` file has correct credentials
2. Redeploy with correct credentials:
   ```powershell
   . .\scripts\utilities\load-secrets.ps1
   .\scripts\deployment\deploy-with-secrets.ps1
   ```
3. Verify credentials in AWS Cognito Console

## Passkey Authentication Issues

### 1. WebAuthn Not Supported

**Error**: `NotSupportedError` or "WebAuthn not supported"

**Symptoms**:

- Passkey registration/authentication fails
- Browser doesn't show biometric prompt
- Error about WebAuthn support

**Diagnosis**:

```javascript
// Check WebAuthn support in browser console
console.log("WebAuthn supported:", !!window.PublicKeyCredential);
console.log(
  "Platform authenticator available:",
  await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
);
```

**Solution**:

1. **Update browser** to latest version
2. **Enable WebAuthn** in browser settings
3. **Use supported browser**:
   - Chrome 67+
   - Firefox 60+
   - Safari 14+
   - Edge 18+
4. **Fallback to email verification** if WebAuthn unavailable

### 2. Biometric Prompt Cancelled

**Error**: `NotAllowedError` or user cancellation

**Symptoms**:

- User cancels biometric prompt
- Authentication fails with "not allowed" error
- No credential created/used

**Diagnosis**:

```javascript
// Check for user cancellation
if (error.name === "NotAllowedError") {
  console.log("User cancelled biometric prompt");
}
```

**Solution**:

1. **Retry authentication** - show clear instructions
2. **Guide user** through biometric setup
3. **Alternative authentication** if repeatedly cancelled
4. **Check device settings** for biometric authentication

### 3. Credential ID ArrayBuffer Error

**Error**: "The provided value is not of type '(ArrayBuffer or ArrayBufferView)'"

**Symptoms**:

- Mobile passkey authentication fails
- Desktop works but mobile doesn't
- Error about ArrayBuffer conversion

**Diagnosis**:

```javascript
// Check credential ID format
console.log("Credential ID type:", typeof credentialId);
console.log("Is ArrayBuffer:", credentialId instanceof ArrayBuffer);
```

**Solution**:
Already fixed in current implementation. If still occurring:

1. **Update frontend code** to latest version
2. **Check ArrayBuffer conversion** in `webAuthnService.ts`
3. **Verify base64url encoding** is correct

### 4. Mobile Timeout Issues

**Error**: `TimeoutError` on mobile devices

**Symptoms**:

- Authentication works on desktop
- Mobile devices timeout during biometric prompt
- Error after 60 seconds

**Diagnosis**:

```javascript
// Check timeout configuration
console.log(
  "Is mobile:",
  /Android|iPhone|iPad|iPod|BlackBerry|IEMobile/i.test(navigator.userAgent)
);
console.log("Timeout used:", isMobile ? 300000 : 60000);
```

**Solution**:
Already implemented - mobile devices get 5-minute timeout. If still occurring:

1. **Check mobile detection** logic
2. **Verify timeout configuration** in WebAuthn options
3. **Guide user** to respond quickly to biometric prompt

## Cognito Configuration Issues

### 1. User Pool Not Found

**Error**: `UserPoolId` not found or invalid

**Symptoms**:

- Authentication requests fail
- AWS API returns user pool not found
- Configuration errors in logs

**Diagnosis**:

```bash
# Verify user pool exists
aws cognito-idp describe-user-pool \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --region eu-west-1
```

**Solution**:

1. **Check AWS region** - must be `eu-west-1`
2. **Verify user pool ID** in configuration
3. **Redeploy infrastructure** if missing:
   ```bash
   cd backend
   sam deploy
   ```

### 2. Custom Attribute Issues

**Error**: `InvalidParameterException` for custom attributes

**Symptoms**:

- User attribute updates fail
- Custom attributes not found
- Passkey credential storage fails

**Diagnosis**:

```bash
# Check custom attributes configuration
aws cognito-idp describe-user-pool \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --query 'UserPool.Schema[?Name==`custom:passkey_cred_ids`]'
```

**Solution**:

1. **Verify custom attributes** exist in user pool
2. **Check attribute name length** (≤20 characters)
3. **Redeploy SAM template** if attributes missing

### 3. Role Assignment Failures

**Error**: Groups not assigned to user

**Symptoms**:

- User authenticates but has no permissions
- JWT token missing `cognito:groups` claim
- Access denied to protected resources

**Diagnosis**:

```bash
# Check user's group memberships
aws cognito-idp admin-list-groups-for-user \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --username user@example.com
```

**Solution**:

1. **Check post-confirmation trigger** is working
2. **Verify Lambda function** has correct permissions
3. **Manually assign groups** if needed:
   ```bash
   aws cognito-idp admin-add-user-to-group \
     --user-pool-id eu-west-1_OAT3oPCIm \
     --username user@example.com \
     --group-name hdcnLeden
   ```

## Email Delivery Issues

### 1. Verification Emails Not Received

**Symptoms**:

- Users don't receive verification emails
- Email verification fails
- No emails in inbox or spam

**Diagnosis**:

```bash
# Check SES configuration
aws ses get-send-quota --region eu-west-1
aws ses get-send-statistics --region eu-west-1
```

**Solution**:

1. **Check spam folder** first
2. **Verify SES configuration** in AWS Console
3. **Check email address** is valid
4. **Test email delivery**:
   ```bash
   python backend/test_ses_email_delivery.py
   ```

### 2. Email Templates Not Working

**Symptoms**:

- Emails sent but wrong content
- Missing Dutch translations
- Template formatting issues

**Diagnosis**:

```bash
# Check Lambda function logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/cognito-custom-message \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Solution**:

1. **Check Lambda function** is deployed
2. **Verify template configuration** in SAM template
3. **Test custom message trigger**:
   ```bash
   python backend/test_email_templates.py
   ```

## Frontend Issues

### 1. Authentication State Not Persisting

**Symptoms**:

- User logged out after page refresh
- Authentication state lost
- Tokens not stored properly

**Diagnosis**:

```javascript
// Check token storage in browser
console.log("Access token:", localStorage.getItem("accessToken"));
console.log("ID token:", localStorage.getItem("idToken"));
console.log("Refresh token:", localStorage.getItem("refreshToken"));
```

**Solution**:

1. **Check token storage** implementation
2. **Verify token refresh** logic
3. **Check browser storage** permissions

### 2. CORS Issues

**Error**: Cross-origin request blocked

**Symptoms**:

- API requests fail from frontend
- CORS errors in browser console
- Authentication requests blocked

**Diagnosis**:

```javascript
// Check API endpoint configuration
console.log("API endpoint:", process.env.REACT_APP_API_URL);
console.log("Origin:", window.location.origin);
```

**Solution**:

1. **Check API Gateway CORS** configuration
2. **Verify allowed origins** in backend
3. **Update CORS settings** in SAM template

### 3. Route Protection Issues

**Symptoms**:

- Protected routes accessible without authentication
- Authentication guards not working
- Unauthorized access to admin features

**Diagnosis**:

```javascript
// Check authentication state
console.log("Is authenticated:", isAuthenticated);
console.log("User roles:", userRoles);
console.log("Required roles:", requiredRoles);
```

**Solution**:

1. **Check route guards** implementation
2. **Verify role-based access** logic
3. **Test permission validation**

## Debugging Tools

### Browser Console Commands

```javascript
// Check authentication state
window.authDebug = {
  user: getCurrentUser(),
  tokens: getTokens(),
  roles: getUserRoles(),
  webauthn: !!window.PublicKeyCredential,
};

// Test WebAuthn support
navigator.credentials
  .create({
    publicKey: {
      challenge: new Uint8Array(32),
      rp: { name: "Test", id: "localhost" },
      user: { id: new Uint8Array(16), name: "test", displayName: "Test" },
      pubKeyCredParams: [{ alg: -7, type: "public-key" }],
      timeout: 60000,
    },
  })
  .then(console.log)
  .catch(console.error);
```

### AWS CLI Commands

```bash
# Check Cognito configuration
aws cognito-idp describe-user-pool --user-pool-id eu-west-1_OAT3oPCIm

# List identity providers
aws cognito-idp list-identity-providers --user-pool-id eu-west-1_OAT3oPCIm

# Check user details
aws cognito-idp admin-get-user \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --username user@example.com

# Test Lambda functions
aws lambda invoke \
  --function-name cognito-post-confirmation \
  --payload '{"test": true}' \
  response.json
```

### Log Analysis

```bash
# CloudWatch logs for authentication
aws logs filter-log-events \
  --log-group-name /aws/lambda/cognito-post-confirmation \
  --filter-pattern "ERROR"

# API Gateway logs
aws logs filter-log-events \
  --log-group-name API-Gateway-Execution-Logs \
  --filter-pattern "authentication"
```

## Escalation Procedures

### Level 1: User Support

1. **Check common issues** in this guide
2. **Verify user's browser** and device
3. **Test basic authentication** flow
4. **Guide through alternative** authentication

### Level 2: Technical Support

1. **Check AWS CloudWatch** logs
2. **Verify infrastructure** configuration
3. **Test API endpoints** directly
4. **Review recent deployments**

### Level 3: Development Team

1. **Deep dive into code** implementation
2. **Check for recent changes** in Git
3. **Review security configurations**
4. **Coordinate with AWS support** if needed

## Prevention Strategies

### Monitoring

1. **Set up CloudWatch alarms** for authentication failures
2. **Monitor error rates** and patterns
3. **Track user experience** metrics
4. **Regular health checks** of authentication flow

### Testing

1. **Automated testing** of authentication flows
2. **Cross-browser testing** for WebAuthn
3. **Mobile device testing** regularly
4. **Load testing** for high traffic

### Documentation

1. **Keep troubleshooting guide** updated
2. **Document new issues** and solutions
3. **Share knowledge** with team
4. **User education** materials

---

**Last Updated**: December 29, 2025  
**Version**: Production v2.0  
**Maintained By**: H-DCN Development Team
