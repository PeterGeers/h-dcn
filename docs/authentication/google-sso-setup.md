**IMPORTANT**: All credentials have been moved to `.secrets` file for security.
See `.secrets.example` for the required configuration format.
For detailed security information, see `docs/security/secrets-management.md`.

# Google Workspace SSO Setup Guide

## Step 1: Google Cloud Console Configuration

### 1.1 Create/Select Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project for H-DCN
3. Note the Project ID for reference See Project ID cognito-leden-auth

### 1.2 Enable Google+ API (if needed)

1. Go to **APIs & Services > Library**
2. Search for "Google+ API"
3. Click **Enable** (may already be enabled)

### 1.3 Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **Internal** (for Google Workspace users only)
3. Fill in required fields:
   - **App name**: H-DCN Portal
   - **User support email**: webhulpje@h-dcn.nl
   - **Developer contact email**: webhulpje@h-dcn.nl
   - **Authorized domains**: h-dcn.nl, de1irtdutlxqu.cloudfront.net
4. Click **Save and Continue**
5. **Scopes**: Add these scopes:
   - `openid`
   - `email`
   - `profile`
6. Click **Save and Continue**

### 1.4 Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth 2.0 Client IDs**
3. Configure:

   - **Application type**: Web application
   - **Name**: H-DCN Portal SSO
   - **Authorized JavaScript origins**:
     - `https://de1irtdutlxqu.cloudfront.net`
     - `http://localhost:3000` (for development)
   - **Authorized redirect URIs**:
     - `https://h-dcn-auth-344561557829.auth.eu-west-1.amazoncognito.com/oauth2/idpresponse`
     - `https://de1irtdutlxqu.cloudfront.net/auth/callback`

4. Click **Create**
5. **IMPORTANT**: Copy the Client ID and Client Secret and add them to your `.secrets` file

## Step 2: Google Workspace Admin Configuration

### 2.1 Configure Domain Access (Optional)

1. Go to [Google Workspace Admin Console](https://admin.google.com/)
2. Navigate to **Security > API Controls > Domain-wide Delegation**
3. Configure OAuth app access policies as needed for your organization

## Step 3: Update AWS Cognito with Google Credentials

### 3.1 Add Google Identity Provider

Run this command using credentials from your `.secrets` file:

```bash
# Load credentials from .secrets file first
source .secrets  # On Linux/Mac
# OR manually set variables on Windows

sam deploy --parameter-overrides GoogleClientId="$GOOGLE_CLIENT_ID" GoogleClientSecret="$GOOGLE_CLIENT_SECRET" --no-confirm-changeset
```

### 3.2 Verify Configuration

Check that the Google Identity Provider was created:

```bash
aws cognito-idp describe-identity-provider \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --provider-name Google \
  --region eu-west-1
```

## Step 4: Test Google SSO

### 4.1 Frontend Testing

1. Build and deploy the frontend with Google Sign-In button
2. Test the "Sign in with Google" flow
3. Verify staff users (@h-dcn.nl) can authenticate
4. Verify non-staff users are rejected

### 4.2 Test User Journey

1. Staff user clicks "Sign in with Google"
2. Redirected to Google Workspace login
3. Authenticates with @h-dcn.nl credentials
4. Redirected back to H-DCN portal
5. Automatically logged in with appropriate permissions

## Step 5: Role Assignment Configuration

### 5.1 Automatic Staff Role Assignment

Staff users authenticated via Google SSO should automatically receive appropriate roles:

- `System_User_Management` (for admin users)
- `Members_CRUD_All` (for member management)
- Other roles based on their position

This can be configured in the Cognito Post-Confirmation trigger.

## Security Considerations

### ✅ Access Control

- All Google accounts can use Google SSO
- Role assignment based on email domain (@h-dcn.nl users get staff roles)
- Configurable at application level

### ✅ Secure Token Handling

- JWT tokens stored securely in browser
- Proper logout from both Google and Cognito

### ✅ Role Validation

- Staff roles assigned based on email domain
- Regular audit of user permissions

## Troubleshooting

### Common Issues

1. **"redirect_uri_mismatch" error**

   - Check that redirect URIs in Google Console match exactly
   - Ensure HTTPS is used for production URLs

2. **"access_denied" error**

   - Verify OAuth consent screen is configured
   - Check that user has @h-dcn.nl email

3. **"invalid_client" error**
   - Verify Client ID and Secret are correct
   - Check that credentials are properly deployed to AWS

### Testing Commands

```bash
# Test Google Identity Provider
aws cognito-idp list-identity-providers \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --region eu-west-1

# Check User Pool Client configuration
aws cognito-idp describe-user-pool-client \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --client-id 7p5t7sjl2s1rcu1emn85h20qeh \
  --region eu-west-1
```

## Next Steps After Setup

1. **Deploy Frontend**: Build and deploy frontend with Google Sign-In button
2. **Staff Training**: Brief staff on new Google SSO option
3. **Monitor Usage**: Track adoption and any issues
4. **Phase 2**: Implement simplified authentication for general members (1000+ users)

---

**Status**: Ready for Google Cloud Console configuration
**Next Action**: Create OAuth 2.0 credentials in Google Cloud Console
