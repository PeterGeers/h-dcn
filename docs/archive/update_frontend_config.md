# Frontend Configuration Update

After deploying the new stack, update these values in your frontend:

## Get New Values

```bash
# Get new Cognito User Pool ID
aws cloudformation describe-stacks --stack-name webshop-backend-v2 --region eu-west-1 --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolId'].OutputValue" --output text

# Get new Cognito Client ID
aws cloudformation describe-stacks --stack-name webshop-backend-v2 --region eu-west-1 --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolClientId'].OutputValue" --output text

# Get new API Gateway URL
aws cloudformation describe-stacks --stack-name webshop-backend-v2 --region eu-west-1 --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" --output text
```

## Update Frontend Files

Replace these values in your frontend configuration:

- `COGNITO_USER_POOL_ID`: New pool ID
- `COGNITO_CLIENT_ID`: New client ID
- `API_BASE_URL`: New API Gateway URL

## Test Plan

1. Deploy new stack
2. Run migration script
3. Update frontend config
4. Test login with existing user
5. Verify all functionality works
6. Switch DNS/CloudFront to new API
7. Delete old stack after verification
