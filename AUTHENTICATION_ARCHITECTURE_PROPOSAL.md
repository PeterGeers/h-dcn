# H-DCN Authentication Architecture Proposal

## Current Issues

- Authentication logic duplicated across 40+ Lambda functions
- Inconsistent CORS configurations
- Manual JWT token handling in each function
- No centralized authentication service
- Difficult to maintain and debug

## Proposed Solution: Centralized Authentication

### 1. API Gateway Authorizer (Recommended)

```yaml
# In template.yaml
CognitoAuthorizer:
  Type: AWS::ApiGateway::Authorizer
  Properties:
    Name: CognitoAuthorizer
    Type: COGNITO_USER_POOLS
    IdentitySource: method.request.header.Authorization
    RestApiId: !Ref Api
    ProviderARNs:
      - !Sub "arn:aws:cognito-idp:${AWS::Region}:${AWS::AccountId}:userpool/${ExistingUserPoolId}"
```

### 2. Shared Authentication Layer (Current + Enhanced)

```python
# backend/shared/auth_service.py
class AuthService:
    @staticmethod
    def validate_request(event):
        """Single point of authentication validation"""
        # Extract JWT from API Gateway authorizer context
        # Validate permissions
        # Return user info and permissions

    @staticmethod
    def check_permissions(user_roles, required_permissions):
        """Centralized permission checking"""

    @staticmethod
    def get_user_context(event):
        """Extract user context from validated request"""
```

### 3. Simplified Lambda Functions

```python
# In each handler
from shared.auth_service import AuthService

def lambda_handler(event, context):
    # Authentication handled by API Gateway + shared service
    user_context = AuthService.get_user_context(event)

    # Business logic only
    return handle_business_logic(user_context, event)
```

### 4. Unified CORS Configuration

```yaml
# Single CORS configuration for entire API
Globals:
  Api:
    Cors:
      AllowMethods: "'OPTIONS,GET,POST,PUT,DELETE,PATCH'"
      AllowHeaders: "'Content-Type,Authorization,X-Enhanced-Groups,X-Requested-With'"
      AllowOrigin: "'*'"
```

## Benefits

1. **Single source of truth** for authentication
2. **Consistent behavior** across all endpoints
3. **Easier debugging** - centralized logging
4. **Better performance** - API Gateway handles auth
5. **Simpler Lambda functions** - focus on business logic
6. **Easier testing** - mock auth service

## Migration Plan

1. Implement API Gateway Authorizer for new endpoints
2. Create enhanced AuthService with current logic
3. Migrate existing functions one by one
4. Remove individual auth_fallback.py files
5. Standardize CORS configuration

## Immediate Fix for Current Issue

While we plan the migration, let's fix the immediate CORS issue:

- Add missing headers to global CORS config
- Ensure consistent CORS across all endpoints
- Test with centralized auth headers

Would you like me to implement this architecture?
