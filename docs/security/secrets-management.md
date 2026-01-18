# H-DCN Portal Secrets Management

## Overview

This document outlines how sensitive credentials and secrets are managed in the H-DCN Portal project to ensure security and prevent accidental exposure.

## Secrets Storage

### Local Development

All sensitive credentials are stored in a `.secrets` file in the project root:

- **File**: `.secrets` (never committed to version control)
- **Template**: `.secrets.example` (committed as a template)
- **Location**: Project root directory

### Required Secrets

The following secrets are required for the application:

```bash
# Google OAuth Configuration
GOOGLE_PROJECT_ID=your-google-project-id
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# AWS Cognito Configuration
COGNITO_USER_POOL_ID=your-cognito-user-pool-id
COGNITO_CLIENT_ID=your-cognito-client-id
COGNITO_CLIENT_SECRET=your-cognito-client-secret

# AWS Configuration
AWS_REGION=eu-west-1
CLOUDFRONT_DISTRIBUTION_ID=your-cloudfront-distribution-id
```

## Security Measures

### Git Protection

The following files are excluded from version control via `.gitignore`:

```gitignore
# Secrets and credentials (NEVER commit these!)
.secrets
*.secrets
.credentials
*.credentials
.env.secrets
```

### Documentation Cleanup

All documentation files have been cleaned of hardcoded credentials:

- ✅ `docs/authentication/google-sso-setup.md` - Credentials removed
- ✅ References replaced with `.secrets` file instructions
- ✅ Deployment scripts updated to use environment variables

## Usage

### Loading Secrets (Windows PowerShell)

```powershell
# Load secrets into environment variables
. .\scripts\utilities\load-secrets.ps1

# Use in deployment
.\scripts\deployment\deploy-with-secrets.ps1
```

### Loading Secrets (Linux/Mac)

```bash
# Load secrets into environment variables
source .secrets

# Use in deployment
sam deploy --parameter-overrides \
  GoogleClientId="$GOOGLE_CLIENT_ID" \
  GoogleClientSecret="$GOOGLE_CLIENT_SECRET" \
  --no-confirm-changeset
```

### Manual Environment Variables (Windows CMD)

```cmd
# Set variables manually if needed
set GOOGLE_CLIENT_ID=your-client-id
set GOOGLE_CLIENT_SECRET=your-client-secret
```

## Production Deployment

### AWS Parameter Store (Recommended)

For production deployments, store secrets in AWS Systems Manager Parameter Store:

```bash
# Store secrets in Parameter Store
aws ssm put-parameter \
  --name "/hdcn/google/client-id" \
  --value "your-client-id" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/hdcn/google/client-secret" \
  --value "your-client-secret" \
  --type "SecureString"
```

### Environment Variables in CI/CD

For GitHub Actions or other CI/CD systems:

1. Store secrets in repository secrets
2. Use environment variables in deployment scripts
3. Never log or echo secret values

## Security Best Practices

### ✅ Do's

- Use `.secrets` file for local development
- Use AWS Parameter Store for production
- Use environment variables in scripts
- Regularly rotate credentials
- Use least-privilege access policies
- Review code for hardcoded secrets before commits

### ❌ Don'ts

- Never commit `.secrets` file to version control
- Never hardcode credentials in source code
- Never log or echo secret values
- Never share credentials via email or chat
- Never use production credentials in development

## Credential Rotation

### Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services > Credentials**
3. Create new OAuth 2.0 Client ID
4. Update `.secrets` file with new credentials
5. Deploy updated configuration
6. Delete old credentials after verification

### AWS Cognito Credentials

1. Generate new client secret in AWS Cognito Console
2. Update `.secrets` file
3. Deploy updated configuration
4. Verify authentication still works

## Incident Response

If credentials are accidentally exposed:

1. **Immediate**: Rotate all exposed credentials
2. **Review**: Check git history for exposure
3. **Clean**: Remove from any logs or documentation
4. **Deploy**: Update all environments with new credentials
5. **Monitor**: Watch for unauthorized access attempts

## Verification

To verify secrets are properly protected:

```powershell
# Check that .secrets is not tracked by git
git status --ignored

# Verify .secrets is in .gitignore
Get-Content .gitignore | Select-String "secrets"

# Test that secrets load correctly
. .\scripts\utilities\load-secrets.ps1
echo $env:GOOGLE_CLIENT_ID  # Should show your client ID

# Run GitGuardian scan (excluding common false positives)
ggshield secret scan path . --recursive --exclude ".git,.aws-sam,.venv,node_modules,.pytest_cache"
```

```

## Support

For questions about secrets management:

- **Technical**: Contact webmaster@h-dcn.nl
- **Security**: Contact security@h-dcn.nl
- **Documentation**: See `docs/authentication/` folder

---

**Remember**: When in doubt, treat it as a secret. It's better to be overly cautious with sensitive information.
```
