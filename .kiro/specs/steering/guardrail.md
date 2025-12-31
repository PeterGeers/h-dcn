---
inclusion: manual
---

# H-DCN Project Guardrails

## 🚨 CRITICAL SAFETY RULES - READ FIRST

### ⚠️ S3 Bucket Architecture - NEVER MIX THESE UP

```bash
# CODE BUCKET (safe to overwrite)
REACT_APP_S3_BUCKET=testportal-h-dcn-frontend
# Contains: HTML, CSS, JS, build artifacts
# Deployment: Automated, can use --delete safely

# DATA BUCKET (NEVER delete content)
REACT_APP_IMAGES_BUCKET=my-hdcn-bucket
# Contains: parameters.json, product images, logos, user uploads
# Deployment: Manual only, NEVER use --delete
```

### 🛡️ Data Protection Rules

1. **NEVER use `--delete` on `my-hdcn-bucket`** - Contains irreplaceable business data
2. **NEVER deploy code to `my-hdcn-bucket`** - It's for data only
3. **NEVER deploy data to `testportal-h-dcn-frontend`** - It gets overwritten
4. **ALWAYS backup before data operations** - Use `backup-parameters.ps1`
5. **parameters.json is DATA, not code** - Lives in `my-hdcn-bucket`, not frontend

### 🚫 Dangerous Fallback Patterns - FORBIDDEN

```typescript
// ❌ FORBIDDEN - Dangerous fallbacks that caused data loss
bucketName: string = process.env.REACT_APP_S3_BUCKET || "my-hdcn-bucket";
bucketName: string =
  process.env.REACT_APP_IMAGES_BUCKET || "testportal-h-dcn-frontend";

// ✅ REQUIRED - Fail fast with clear errors
const bucketName = process.env.REACT_APP_S3_BUCKET;
if (!bucketName) {
  throw new Error("REACT_APP_S3_BUCKET environment variable is required");
}
```

### 📋 Safe Deployment Commands

```powershell
# ✅ SAFE - Frontend code deployment
.\scripts\deployment\deploy-frontend-safe.ps1

# ✅ SAFE - Data operations with backups
.\scripts\utilities\backup-parameters.ps1
.\scripts\utilities\deploy-parameters.ps1

# ❌ DANGEROUS - Never run these on data bucket
aws s3 sync build/ s3://my-hdcn-bucket/ --delete
aws s3 rm s3://my-hdcn-bucket/ --recursive
```

## 🎯 Core Principles

### 1. Security First

- **No hardcoded credentials** - Use environment variables and AWS Parameter Store (GitGuardian enforced)
- **Least privilege access** - IAM roles with minimal required permissions
- **Input validation** - Sanitize all member data inputs to prevent XSS/injection attacks
- **Authentication required** - All API endpoints must validate Cognito JWT tokens
- **HTTPS only** - No unencrypted communication (CloudFront + API Gateway)
- **Regional data access** - hdcnRegio\_\* groups can only access their region's members

### 2. Environment Variables - NO DANGEROUS FALLBACKS

```bash
# ✅ REQUIRED - All critical environment variables
REACT_APP_S3_BUCKET=testportal-h-dcn-frontend          # Frontend code bucket
REACT_APP_IMAGES_BUCKET=my-hdcn-bucket                 # Data/images bucket
REACT_APP_IMAGES_BASE_URL=https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com
REACT_APP_LOGO_BUCKET_URL=https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com
REACT_APP_API_BASE_URL=https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod
REACT_APP_AWS_REGION=eu-west-1
REACT_APP_USER_POOL_ID=eu-west-1_VtKQHhXGN
REACT_APP_USER_POOL_WEB_CLIENT_ID=77blkk6a3rpablme00m2die68g
```

**Fallback Policy**:

- **Critical buckets**: MUST throw error if missing (no fallbacks)
- **API endpoints**: MUST throw error if missing (no fallbacks)
- **UI settings**: Can have safe defaults (cache version, UI flags)
- **Development only**: Local fallbacks allowed for non-production

### 3. Mobile-First Design

- **Responsive by default** - All components must work on mobile devices
- **Touch-friendly UI** - Minimum 44px touch targets
- **Progressive disclosure** - Hide non-essential elements on small screens
- **Performance optimized** - Minimize bundle size and API calls

### 4. Type Safety

- **TypeScript everywhere** - All new code must be TypeScript (.tsx/.ts)
- **Strict typing** - No `any` types without justification
- **Interface definitions** - Proper types for all data structures
- **Runtime validation** - Validate API responses match expected types

## 🏗️ Architecture Guidelines

### Frontend (React)

- **Component isolation** - Each component in its own file
- **Reusable components** - Shared components in `/components` directory
- **Module organization** - Feature-based folder structure
- **State management** - Use React Context for global state
- **Error boundaries** - Wrap components to handle errors gracefully

### Backend (AWS Lambda)

- **Single responsibility** - One function per API endpoint
- **Stateless design** - No local state between invocations
- **Error handling** - Consistent error response format
- **Logging** - Structured logging for debugging
- **Cold start optimization** - Minimize initialization code

### Database (DynamoDB)

- **Consistent naming** - Use camelCase for attribute names
- **Efficient queries** - Design partition/sort keys for access patterns
- **Data validation** - Validate data before writing
- **Backup strategy** - Enable point-in-time recovery

## 🔐 Secrets & Environment Management

### Required Environment Variables

```bash
# Critical - MUST be set, no fallbacks allowed
REACT_APP_S3_BUCKET=testportal-h-dcn-frontend
REACT_APP_IMAGES_BUCKET=my-hdcn-bucket
REACT_APP_API_BASE_URL=https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod
REACT_APP_AWS_REGION=eu-west-1

# Authentication - MUST be set
REACT_APP_USER_POOL_ID=eu-west-1_VtKQHhXGN
REACT_APP_USER_POOL_WEB_CLIENT_ID=77blkk6a3rpablme00m2die68g

# URLs - MUST be set
REACT_APP_IMAGES_BASE_URL=https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com
REACT_APP_LOGO_BUCKET_URL=https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com

# Optional - Can have safe defaults
REACT_APP_CACHE_VERSION=1.0
```

### Secrets Management

- **Development**: Use `.secrets` file (never commit)
- **Production**: Use AWS Parameter Store or environment variables
- **Local testing**: Use `load-secrets.ps1` to load from `.secrets`
- **CI/CD**: Use GitHub secrets or AWS IAM roles

### Environment Variable Validation

```typescript
// ✅ REQUIRED - Fail fast pattern
const validateEnvironment = () => {
  const required = [
    "REACT_APP_S3_BUCKET",
    "REACT_APP_IMAGES_BUCKET",
    "REACT_APP_API_BASE_URL",
  ];

  for (const envVar of required) {
    if (!process.env[envVar]) {
      throw new Error(`${envVar} environment variable is required`);
    }
  }
};

// ❌ FORBIDDEN - Dangerous fallback pattern
const bucketName = process.env.REACT_APP_S3_BUCKET || "my-hdcn-bucket";
```

## 🔐 Access Control Rules

### Role-Based Permissions

- **No groups**: Membership registration only
- **hdcnLeden**: Webshop access + Profile management
- **hdcnRegio_Noord**: Northern region member administration (read-only)
- **hdcnRegio_Zuid**: Southern region member administration (read-only)
- **hdcnRegio_Oost**: Eastern region member administration (read-only)
- **hdcnRegio_West**: Western region member administration (read-only)
- **hdcnAdmins**: Full system access including user management, events, products, and system configuration

### Function Permissions

- **Granular control** - Use `function_permissions` parameter store for dynamic access control
- **Read/Write separation** - Explicit permission levels (read, write, delete)
- **Regional restrictions** - Limit member data access by geographic region
- **Audit trail** - Log all permission changes in CloudWatch
- **Dynamic loading** - Permissions loaded from Parameter Store at runtime

## 📝 Code Quality Standards

### General Rules

- **Consistent formatting** - Use Prettier for code formatting
- **Meaningful names** - Clear, descriptive variable/function names
- **Documentation** - JSDoc comments for complex functions
- **Error messages** - User-friendly error descriptions
- **Performance** - Optimize for speed and memory usage

### React Components

```typescript
// ✅ Good: H-DCN specific TypeScript interface
interface MemberCardProps {
  member: Member;
  onSelect: (member: Member) => void;
  showRegion?: boolean;
  allowEdit?: boolean;
}

const MemberCard: React.FC<MemberCardProps> = ({
  member,
  onSelect,
  showRegion = true,
  allowEdit = false,
}) => {
  // Component implementation with proper error boundaries
};

// ❌ Bad: No types, unclear props
const MemberCard = (props) => {
  // Implementation
};
```

### Lambda Functions

```python
# ✅ Good: H-DCN specific error handling with security
def lambda_handler(event, context):
    try:
        # Validate Cognito JWT token
        user_groups = validate_cognito_token(event['headers']['Authorization'])

        # Check function permissions from Parameter Store
        if not has_function_access(user_groups, 'get_members', 'read'):
            return error_response(403, "Insufficient permissions")

        # Validate input for member data
        if not event.get('body'):
            return error_response(400, "Missing member data")

        # Process request with regional filtering
        result = process_member_request(event['body'], user_groups)
        return success_response(result)

    except CognitoTokenError as e:
        logger.error(f"Authentication failed: {str(e)}")
        return error_response(401, "Invalid authentication token")
    except ValidationError as e:
        logger.error(f"Validation failed: {str(e)}")
        return error_response(400, "Invalid member data format")
    except Exception as e:
        logger.error(f"Unexpected error in get_members: {str(e)}")
        return error_response(500, "Internal server error")

# ❌ Bad: No error handling or security validation
def lambda_handler(event, context):
    result = process_request(event['body'])
    return result
```

## 🚀 Safe Deployment Guidelines

### S3 Bucket Operations

#### ✅ SAFE Operations

```powershell
# Frontend code deployment (safe to overwrite)
.\scripts\deployment\deploy-frontend-safe.ps1

# Data operations with proper backups
.\scripts\utilities\backup-parameters.ps1
.\scripts\utilities\deploy-parameters.ps1
.\scripts\utilities\restore-images-from-local.ps1

# Sync only static assets (excludes data)
aws s3 sync build/static/ s3://testportal-h-dcn-frontend/static/ --delete
```

#### ❌ DANGEROUS Operations - NEVER RUN

```powershell
# NEVER delete data bucket content
aws s3 sync build/ s3://my-hdcn-bucket/ --delete
aws s3 rm s3://my-hdcn-bucket/ --recursive

# NEVER deploy code to data bucket
aws s3 sync build/ s3://my-hdcn-bucket/

# NEVER deploy data to code bucket
aws s3 cp parameters.json s3://testportal-h-dcn-frontend/
```

### Emergency Recovery Procedures

#### Data Loss Recovery

1. **Check S3 versioning** - `aws s3api list-object-versions --bucket my-hdcn-bucket`
2. **Restore from versions** - Use AWS Console or CLI to restore previous versions
3. **Local backup restore** - Use `restore-images-from-local.ps1` if available
4. **Database URL fix** - Run `fix-product-image-urls.ps1` after restoration

#### Wrong Bucket Deployment

1. **Stop immediately** - Cancel any running sync operations
2. **Assess damage** - Check what was overwritten in data bucket
3. **Restore data** - Use S3 versioning or local backups
4. **Fix environment** - Verify correct bucket variables are set
5. **Re-deploy safely** - Use proper deployment scripts

### Version Control & Testing

- **Feature branches** - Create branches for new features
- **Descriptive commits** - Clear commit messages
- **Pull requests** - Code review before merging
- **Tag releases** - Version tags for deployments

### Testing Requirements

- **Unit tests** - Test individual functions/components
- **Integration tests** - Test API endpoints
- **Manual testing** - Verify UI functionality
- **Performance testing** - Check load handling

### Safe Deployment Process

1. **Environment check** - Verify correct bucket variables are set
2. **Local testing** - Verify changes work locally
3. **Code review** - Get approval from team member
4. **Backup data** - Run `backup-parameters.ps1` before data changes
5. **Staging deployment** - Deploy to test environment first
6. **Production deployment** - Use safe deployment scripts only
7. **Monitoring** - Watch logs and metrics post-deployment

### Kiro IDE Safety Instructions

When using Kiro for H-DCN development:

```bash
# ✅ SAFE - Tell Kiro to use these commands
"Use deploy-frontend-safe.ps1 for frontend deployment"
"Use backup-parameters.ps1 before any data changes"
"Never use --delete on my-hdcn-bucket"

# ❌ DANGEROUS - Never let Kiro run these
"aws s3 sync build/ s3://my-hdcn-bucket/ --delete"
"aws s3 rm s3://my-hdcn-bucket/"
```

**Kiro Context Files**:

- Use `#guardrail` to load these safety rules
- Use `#tech` for architecture guidance
- Use `#bucket-separation` for deployment strategy

## 🛡️ Security & Safety Checklist

### Before Every Deployment

- [ ] **Bucket verification** - Confirm correct bucket variables in .env
- [ ] **Backup data** - Run `backup-parameters.ps1` if touching data
- [ ] **Script verification** - Using `deploy-frontend-safe.ps1` for code
- [ ] No credentials in code (GitGuardian pre-commit hook validates)
- [ ] Input validation implemented for member data forms
- [ ] CORS properly configured for H-DCN frontend domain
- [ ] Cognito JWT token validation in all Lambda functions
- [ ] Error messages don't leak member personal data
- [ ] Dependencies scanned with `npm audit` and `pip-audit`
- [ ] CloudTrail access logs enabled for audit trail

### Before Data Operations

- [ ] **Environment variables set** - All required bucket variables present
- [ ] **No dangerous fallbacks** - Code throws errors for missing critical vars
- [ ] **Backup created** - Current data backed up before changes
- [ ] **Correct bucket targeted** - Double-check data goes to `my-hdcn-bucket`
- [ ] **No --delete flags** - Never use --delete on data bucket operations

### Regular Security Reviews

- [ ] Review hdcnRegio\_\* group permissions quarterly
- [ ] Update Cognito User Pool security settings monthly
- [ ] Scan for vulnerable dependencies with GitGuardian dashboard
- [ ] Review API Gateway CORS and authentication configurations
- [ ] Audit member data access patterns in CloudWatch logs
- [ ] Validate function_permissions parameter store entries
- [ ] Test regional access restrictions (hdcnRegio_Noord, hdcnRegio_Zuid, etc.)

## 📊 Performance Standards

### Frontend Metrics (H-DCN Dashboard)

- **First Contentful Paint**: < 2 seconds (member dashboard loading)
- **Largest Contentful Paint**: < 4 seconds (member list with photos)
- **Bundle size**: < 1MB compressed (optimize for mobile club members)
- **API response time**: < 500ms average (member data queries)

### Backend Metrics (AWS Lambda)

- **Lambda cold start**: < 1 second (acceptable for club management use case)
- **API Gateway latency**: < 200ms (member data operations)
- **DynamoDB response**: < 100ms (member/event/product queries)
- **Error rate**: < 1% (critical for member data integrity)

## 🔧 Maintenance Guidelines

### Regular Tasks

- **Weekly**: Review CloudWatch logs for member access patterns and API errors
- **Monthly**: Update dependencies and security patches (npm audit, pip-audit)
- **Quarterly**: Review AWS costs and optimize DynamoDB/Lambda usage
- **Annually**: Security audit and penetration testing for member data protection

### Documentation Updates

- **Code changes**: Update inline JSDoc comments and TypeScript interfaces
- **API changes**: Update API documentation for member/event/product endpoints
- **Architecture changes**: Update Kiro steering files (structure.md, tech.md)
- **Process changes**: Update this guardrail document and team workflows

### Kiro IDE Integration

- **Steering files**: Use `#guardrail`, `#tech`, `#testing` for context-aware assistance
- **MCP servers**: Leverage AWS docs and Git integration for development
- **Project templates**: Use established patterns for new features
- **GitGuardian**: Pre-commit hooks prevent credential leaks automatically

## 🚨 Emergency Procedures

### Data Loss Incidents

1. **Immediate**: Stop all deployment operations
2. **Assess**: Check S3 versioning - `aws s3api list-object-versions --bucket my-hdcn-bucket`
3. **Restore**: Use S3 versioning to restore deleted files
4. **Local restore**: Use `restore-images-from-local.ps1` if local backups available
5. **Database fix**: Run `fix-product-image-urls.ps1` to update URLs
6. **Post-mortem**: Document cause and update guardrails

### Wrong Bucket Deployment

1. **Immediate**: Cancel running sync operations (Ctrl+C)
2. **Assess**: Check what was overwritten in data bucket
3. **Restore**: Use S3 versioning or local backups to restore data
4. **Environment**: Verify correct bucket variables in .env file
5. **Re-deploy**: Use proper deployment scripts only
6. **Prevention**: Update guardrails to prevent recurrence

### Production Issues

1. **Immediate**: Check CloudWatch logs for affected Lambda functions (get_members, create_member, etc.)
2. **Assess**: Determine impact on member data access and club operations
3. **Communicate**: Notify H-DCN stakeholders and affected regional admins
4. **Fix**: Apply hotfix or rollback using SAM CLI deployment
5. **Post-mortem**: Document root cause and update guardrails to prevent recurrence

### Security Incidents

1. **Isolate**: Disable affected Lambda functions or Cognito User Pool immediately
2. **Assess**: Determine scope of potential member data breach
3. **Notify**: Contact H-DCN board and affected members per GDPR requirements
4. **Investigate**: Analyze CloudTrail logs and member access patterns
5. **Remediate**: Fix vulnerability, rotate credentials, and strengthen security controls

## 📋 Compliance Requirements

### Data Protection

- **GDPR compliance** - Handle H-DCN member personal data appropriately
- **Data retention** - Delete inactive member data according to club policy
- **User consent** - Obtain consent for member data processing and marketing
- **Data portability** - Allow members to export their personal data
- **Right to be forgotten** - Implement member data deletion on request

### Audit Requirements

- **Access logging** - Log all member data access with user identification
- **Change tracking** - Track all modifications to member profiles and permissions
- **User activity** - Monitor regional admin actions and member self-service
- **System events** - Log all authentication attempts and permission changes
- **Regional compliance** - Ensure data access respects geographic restrictions

---

**Document Version**: 3.0 - Practical Safety Focus  
**Last Updated**: December 30, 2025  
**Review Schedule**: After any data loss incident + Quarterly  
**Owner**: H-DCN Development Team  
**Tools**: Kiro IDE, GitGuardian, AWS SAM, MCP Servers  
**Focus**: Prevent bucket confusion, data deletion, wrong deployments

## CRITICAL: ASK BEFORE ADDING UNREQUESTED FEATURES

**ALWAYS ASK PERMISSION before adding any code, validation, or features that were not explicitly requested.**

### Examples of what to ASK about first:

- "I notice the status validation might cause issues, should I fix that too?"
- "Should I add logging for this operation?"
- "I see a potential security issue, should I address it?"
- "Would you like me to add error handling for this edge case?"

### What NOT to do:

- ❌ Adding validation logic without being asked
- ❌ Adding "enhanced security" features
- ❌ Adding logging or audit trails without request
- ❌ "Improving" code beyond the specific issue
- ❌ Adding business logic validation in backend when frontend should handle it

### The Rule:

**ONLY fix the exact problem described. If you see other potential issues, ASK first.**

This prevents:

- Wasted deployment time (30+ minutes each time)
- Introducing new bugs
- Adding unwanted complexity
- Breaking existing functionality

### Session Continuity:

- Each new session should read existing steering files
- Don't assume previous context - ask for clarification
- Focus on the immediate problem, not "potential improvements"
