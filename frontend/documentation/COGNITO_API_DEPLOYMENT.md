# Cognito API Deployment Guide

## 📋 API Endpoints

### Users
- `GET /cognito/users` - List all users
- `POST /cognito/users` - Create new user
- `PUT /cognito/users/{username}` - Update user attributes
- `DELETE /cognito/users/{username}` - Delete user

### Groups
- `GET /cognito/groups` - List all groups
- `POST /cognito/groups` - Create new group
- `DELETE /cognito/groups/{groupName}` - Delete group

### User-Group Management
- `GET /cognito/users/{username}/groups` - Get user's groups
- `POST /cognito/users/{username}/groups/{groupName}` - Add user to group
- `DELETE /cognito/users/{username}/groups/{groupName}` - Remove user from group

### Pool Info
- `GET /cognito/pool` - Get user pool information

## 🚀 Deployment Steps

### 1. Create Lambda Function
```bash
# Create new Lambda function
aws lambda create-function \
  --function-name hdcn-cognito-admin \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-cognito-admin-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://cognito-lambda.zip
```

### 2. Required IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:ListUsers",
        "cognito-idp:AdminCreateUser",
        "cognito-idp:AdminDeleteUser",
        "cognito-idp:AdminUpdateUserAttributes",
        "cognito-idp:AdminSetUserPassword",
        "cognito-idp:AdminAddUserToGroup",
        "cognito-idp:AdminRemoveUserFromGroup",
        "cognito-idp:AdminListGroupsForUser",
        "cognito-idp:ListGroups",
        "cognito-idp:CreateGroup",
        "cognito-idp:DeleteGroup",
        "cognito-idp:DescribeUserPool"
      ],
      "Resource": "arn:aws:cognito-idp:eu-west-1:*:userpool/eu-west-1_VtKQHhXGN"
    }
  ]
}
```

### 3. Add to API Gateway
Add these routes to your existing API Gateway:
- `/cognito/{proxy+}` with Lambda proxy integration

### 4. Test Endpoints
```bash
# Test list users
curl https://your-api-gateway-url/prod/cognito/users

# Test create group
curl -X POST https://your-api-gateway-url/prod/cognito/groups \
  -H "Content-Type: application/json" \
  -d '{"groupName": "TestGroup", "description": "Test group"}'
```

## 🔧 Frontend Integration

The frontend is already updated to use these API endpoints. Once deployed:

1. ✅ **Users tab** - Will show all Cognito users
2. ✅ **Groups tab** - Will show all groups with member counts  
3. ✅ **Pool Settings** - Will show user pool configuration
4. ✅ **All CRUD operations** - Create, update, delete users and groups

## 🎯 Benefits

- **Secure**: Admin operations stay on backend
- **Consistent**: Same API pattern as your other endpoints
- **Flexible**: Easy to add business logic, logging, validation
- **Maintainable**: Standard Lambda + API Gateway architecture