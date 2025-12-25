---
inclusion: manual
---

# H-DCN Project Guardrails

## 🎯 Core Principles

### 1. Security First

- **No hardcoded credentials** - Use environment variables and AWS Parameter Store (GitGuardian enforced)
- **Least privilege access** - IAM roles with minimal required permissions
- **Input validation** - Sanitize all member data inputs to prevent XSS/injection attacks
- **Authentication required** - All API endpoints must validate Cognito JWT tokens
- **HTTPS only** - No unencrypted communication (CloudFront + API Gateway)
- **Regional data access** - hdcnRegio\_\* groups can only access their region's members

### 2. Mobile-First Design

- **Responsive by default** - All components must work on mobile devices
- **Touch-friendly UI** - Minimum 44px touch targets
- **Progressive disclosure** - Hide non-essential elements on small screens
- **Performance optimized** - Minimize bundle size and API calls

### 3. Type Safety

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

## 🚀 Deployment Guidelines

### Version Control

- **Feature branches** - Create branches for new features
- **Descriptive commits** - Clear commit messages
- **Pull requests** - Code review before merging
- **Tag releases** - Version tags for deployments

### Testing Requirements

- **Unit tests** - Test individual functions/components
- **Integration tests** - Test API endpoints
- **Manual testing** - Verify UI functionality
- **Performance testing** - Check load handling

### Deployment Process

1. **Local testing** - Verify changes work locally
2. **Code review** - Get approval from team member
3. **Staging deployment** - Deploy to test environment
4. **Production deployment** - Deploy after staging validation
5. **Monitoring** - Watch logs and metrics post-deployment

## 🛡️ Security Checklist

### Before Every Deployment

- [ ] No credentials in code (GitGuardian pre-commit hook validates)
- [ ] Input validation implemented for member data forms
- [ ] CORS properly configured for H-DCN frontend domain
- [ ] Cognito JWT token validation in all Lambda functions
- [ ] Error messages don't leak member personal data
- [ ] Dependencies scanned with `npm audit` and `pip-audit`
- [ ] CloudTrail access logs enabled for audit trail

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

**Document Version**: 2.0  
**Last Updated**: December 2025  
**Review Schedule**: Quarterly  
**Owner**: H-DCN Development Team  
**Tools**: Kiro IDE, GitGuardian, AWS SAM, MCP Servers
