# H-DCN Project Guardrails

## 🎯 Core Principles

### 1. Security First
- **No hardcoded credentials** - Use environment variables and AWS Parameter Store
- **Least privilege access** - IAM roles with minimal required permissions
- **Input validation** - Sanitize all user inputs to prevent XSS/injection attacks
- **Authentication required** - All API endpoints must validate Cognito tokens
- **HTTPS only** - No unencrypted communication

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
- **No groups**: Registration only
- **hdcnLeden**: Webshop + Profile management
- **hdcnRegio_***: Regional member read access
- **hdcnAdmins**: Full system access

### Function Permissions
- **Granular control** - Use `function_permissions` parameter
- **Read/Write separation** - Explicit permission levels
- **Regional restrictions** - Limit access by geographic region
- **Audit trail** - Log all permission changes

## 📝 Code Quality Standards

### General Rules
- **Consistent formatting** - Use Prettier for code formatting
- **Meaningful names** - Clear, descriptive variable/function names
- **Documentation** - JSDoc comments for complex functions
- **Error messages** - User-friendly error descriptions
- **Performance** - Optimize for speed and memory usage

### React Components
```typescript
// ✅ Good: Proper TypeScript interface
interface ProductCardProps {
  product: Product;
  onSelect: (product: Product) => void;
}

const ProductCard: React.FC<ProductCardProps> = ({ product, onSelect }) => {
  // Component implementation
};

// ❌ Bad: No types, unclear props
const ProductCard = (props) => {
  // Implementation
};
```

### Lambda Functions
```python
# ✅ Good: Proper error handling
def lambda_handler(event, context):
    try:
        # Validate input
        if not event.get('body'):
            return error_response(400, "Missing request body")
        
        # Process request
        result = process_request(event['body'])
        return success_response(result)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return error_response(500, "Internal server error")

# ❌ Bad: No error handling
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
- [ ] No credentials in code
- [ ] Input validation implemented
- [ ] CORS properly configured
- [ ] Authentication checks in place
- [ ] Error messages don't leak sensitive data
- [ ] Dependencies updated and scanned
- [ ] Access logs enabled

### Regular Security Reviews
- [ ] Review IAM permissions quarterly
- [ ] Update Cognito security settings
- [ ] Scan for vulnerable dependencies
- [ ] Review API Gateway configurations
- [ ] Audit user access patterns

## 📊 Performance Standards

### Frontend Metrics
- **First Contentful Paint**: < 2 seconds
- **Largest Contentful Paint**: < 4 seconds
- **Bundle size**: < 1MB compressed
- **API response time**: < 500ms average

### Backend Metrics
- **Lambda cold start**: < 1 second
- **API Gateway latency**: < 200ms
- **DynamoDB response**: < 100ms
- **Error rate**: < 1%

## 🔧 Maintenance Guidelines

### Regular Tasks
- **Weekly**: Review CloudWatch logs and metrics
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and optimize AWS costs
- **Annually**: Security audit and penetration testing

### Documentation Updates
- **Code changes**: Update inline documentation
- **API changes**: Update API documentation
- **Architecture changes**: Update technical design docs
- **Process changes**: Update this guardrail document

## 🚨 Emergency Procedures

### Production Issues
1. **Immediate**: Check CloudWatch logs and metrics
2. **Assess**: Determine impact and affected users
3. **Communicate**: Notify stakeholders of issue
4. **Fix**: Apply hotfix or rollback if necessary
5. **Post-mortem**: Document root cause and prevention

### Security Incidents
1. **Isolate**: Disable affected components immediately
2. **Assess**: Determine scope of potential breach
3. **Notify**: Contact security team and stakeholders
4. **Investigate**: Analyze logs and access patterns
5. **Remediate**: Fix vulnerability and strengthen security

## 📋 Compliance Requirements

### Data Protection
- **GDPR compliance** - Handle personal data appropriately
- **Data retention** - Delete data according to policy
- **User consent** - Obtain consent for data processing
- **Data portability** - Allow users to export their data

### Audit Requirements
- **Access logging** - Log all data access
- **Change tracking** - Track all system modifications
- **User activity** - Monitor user actions
- **System events** - Log all system events

---

**Document Version**: 1.0  
**Last Updated**: October 2025  
**Review Schedule**: Quarterly  
**Owner**: H-DCN Development Team