# H-DCN Automatic Role Assignment Documentation

## Overview

The H-DCN Cognito authentication system automatically assigns the `hdcnLeden` (basic member) role to all new users when they complete email verification. This ensures that every authenticated user has at least the basic member permissions required to access the system.

## Architecture

### Components

1. **Cognito User Pool**: `eu-west-1_OAT3oPCIm` (H-DCN-Authentication-Pool)
2. **Post-Confirmation Lambda**: `webshop-backend-CognitoPostConfirmationFunction-*`
3. **Default Role Group**: `hdcnLeden` (Cognito User Pool Group)

### Trigger Flow

```
User Registration → Email Verification → PostConfirmation_ConfirmSignUp → Lambda Function → Role Assignment
```

## Implementation Details

### Lambda Function Configuration

**File**: `backend/handler/cognito_post_confirmation/app.py`

**Environment Variables**:
- `DEFAULT_MEMBER_GROUP`: `hdcnLeden`
- `ORGANIZATION_NAME`: `Harley-Davidson Club Nederland`
- `ORGANIZATION_WEBSITE`: `https://h-dcn.nl`
- `ORGANIZATION_EMAIL`: `webhulpje@h-dcn.nl`
- `ORGANIZATION_SHORT_NAME`: `H-DCN`

**Trigger Sources Handled**:
- `PostConfirmation_ConfirmSignUp`: New user signup confirmation
- `PostConfirmation_ConfirmForgotPassword`: Password recovery confirmation

### Infrastructure as Code (SAM Template)

**File**: `backend/template.yaml`

**Key Resources**:
```yaml
# Lambda Function
CognitoPostConfirmationFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: handler/cognito_post_confirmation
    Handler: app.lambda_handler
    Runtime: python3.11
    Environment:
      Variables:
        DEFAULT_MEMBER_GROUP: hdcnLeden

# User Pool Configuration
HDCNCognitoUserPool:
  Type: AWS::Cognito::UserPool
  Properties:
    LambdaConfig:
      PostConfirmation: !GetAtt CognitoPostConfirmationFunction.Arn

# Default Role Group
HDCNLedenGroup:
  Type: AWS::Cognito::UserPoolGroup
  Properties:
    UserPoolId: !Ref HDCNCognitoUserPool
    GroupName: hdcnLeden
    Description: "Basic H-DCN member role - access to personal data and webshop"
    Precedence: 100
```

## Role Assignment Logic

### New User Flow

1. **User Registration**: User creates account with email
2. **Email Verification**: User clicks verification link in email
3. **Post-Confirmation Trigger**: Cognito triggers Lambda function
4. **Role Assignment**: Lambda adds user to `hdcnLeden` group
5. **Confirmation**: User gains basic member permissions

### Function: `handle_signup_confirmation()`

```python
def handle_signup_confirmation(user_pool_id, username, email, given_name, family_name):
    """
    Handle post-confirmation actions for new user signup
    
    Actions performed:
    1. Add user to default member group (hdcnLeden)
    2. Log successful group assignment
    3. Send admin notification
    """
    default_group = os.environ.get('DEFAULT_MEMBER_GROUP', 'hdcnLeden')
    add_user_to_group(user_pool_id, username, default_group)
    send_admin_notification(email, given_name, family_name, 'new_signup')
```

## Testing

### Automated Tests

**Test Files**:
1. `test_automatic_role_assignment_verification.py` - Basic role assignment test
2. `test_lambda_role_assignment.py` - Direct Lambda function test
3. `assign_hdcn_leden_role_to_existing_users.py` - Existing user role assignment

### Test Results Summary

**Latest Test Results** (2025-12-25):
- ✅ Lambda function correctly assigns `hdcnLeden` role to new users
- ✅ All 71 existing users now have `hdcnLeden` role assigned
- ✅ Role assignment verification working correctly
- ✅ Post-confirmation trigger properly configured

### Running Tests

```bash
# Test direct Lambda function invocation
python test_lambda_role_assignment.py

# Test existing user role assignment
python assign_hdcn_leden_role_to_existing_users.py

# Basic role assignment verification
python test_automatic_role_assignment_verification.py
```

## Monitoring and Logging

### CloudWatch Logs

**Log Group**: `/aws/lambda/webshop-backend-CognitoPostConfirmationFunction-*`

**Key Log Messages**:
- `Processing post-confirmation for trigger: PostConfirmation_ConfirmSignUp`
- `Successfully added user {email} to group hdcnLeden`
- `ADMIN_NOTIFICATION: New user signup - {name} ({email})`

### Error Handling

The Lambda function includes comprehensive error handling:
- **Group Not Found**: Logs error but doesn't block user confirmation
- **User Not Found**: Logs error but doesn't block user confirmation
- **Permission Errors**: Logs error but doesn't block user confirmation
- **Unexpected Errors**: Logs error but returns original event to prevent authentication failure

## Permissions

### Lambda Execution Role

**Role**: `CognitoLambdaRole`

**Required Permissions**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:AdminAddUserToGroup",
        "cognito-idp:AdminGetUser",
        "cognito-idp:ListUsers"
      ],
      "Resource": "arn:aws:cognito-idp:eu-west-1:*:userpool/*"
    }
  ]
}
```

## Troubleshooting

### Common Issues

1. **Role Not Assigned**
   - Check Lambda function logs in CloudWatch
   - Verify `hdcnLeden` group exists in User Pool
   - Confirm Lambda has correct permissions

2. **Lambda Not Triggered**
   - Verify post-confirmation trigger is configured in User Pool
   - Check that user completed email verification (not admin creation)
   - Confirm Lambda function is deployed and active

3. **Permission Errors**
   - Verify Lambda execution role has `cognito-idp:AdminAddUserToGroup` permission
   - Check User Pool ARN in IAM policy
   - Confirm Lambda function can access the User Pool

### Verification Commands

```bash
# List all users and their groups
aws cognito-idp list-users --user-pool-id eu-west-1_OAT3oPCIm --region eu-west-1

# Check specific user's groups
aws cognito-idp admin-list-groups-for-user \
  --user-pool-id eu-west-1_OAT3oPCIm \
  --username user@example.com \
  --region eu-west-1

# List all groups in User Pool
aws cognito-idp list-groups --user-pool-id eu-west-1_OAT3oPCIm --region eu-west-1
```

## Security Considerations

### Role Assignment Security

1. **Automatic Assignment**: Only basic member role is assigned automatically
2. **Administrative Roles**: Must be assigned manually by administrators
3. **Error Handling**: Failures don't block user authentication
4. **Audit Trail**: All role assignments are logged

### Best Practices

1. **Minimal Permissions**: Default role has minimal required permissions
2. **Explicit Assignment**: Administrative roles require explicit assignment
3. **Regular Audits**: Periodically review user role assignments
4. **Monitoring**: Monitor Lambda function logs for errors

## Maintenance

### Regular Tasks

1. **Monitor Lambda Logs**: Check for errors in role assignment
2. **Audit User Roles**: Verify all users have appropriate roles
3. **Update Documentation**: Keep documentation current with changes
4. **Test Role Assignment**: Periodically test with new user accounts

### Deployment Updates

When updating the Lambda function:
1. Update code in `backend/handler/cognito_post_confirmation/app.py`
2. Deploy using `sam build && sam deploy`
3. Test role assignment with new user
4. Monitor CloudWatch logs for errors

## Configuration

### Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `DEFAULT_MEMBER_GROUP` | `hdcnLeden` | Default role assigned to new users |
| `ORGANIZATION_NAME` | `Harley-Davidson Club Nederland` | Organization name for notifications |
| `ORGANIZATION_WEBSITE` | `https://h-dcn.nl` | Organization website URL |
| `ORGANIZATION_EMAIL` | `webhulpje@h-dcn.nl` | Contact email for support |
| `ORGANIZATION_SHORT_NAME` | `H-DCN` | Short organization name |

### Customization

To change the default role:
1. Update `DEFAULT_MEMBER_GROUP` environment variable in SAM template
2. Ensure the target group exists in the User Pool
3. Deploy changes using `sam deploy`
4. Test with new user registration

## Support

For issues with automatic role assignment:
1. Check CloudWatch logs for Lambda function
2. Verify User Pool configuration
3. Test with the provided test scripts
4. Contact system administrator if issues persist

---

**Last Updated**: December 25, 2025  
**Version**: 1.0  
**Author**: H-DCN Development Team