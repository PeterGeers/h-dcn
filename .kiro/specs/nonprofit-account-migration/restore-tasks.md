# Restoration Plan: Nonprofit Account (506221081911)

## Status Summary

| Task                                                        | Status      |
| ----------------------------------------------------------- | ----------- |
| 1. DynamoDB tables + data                                   | DONE        |
| 2. Cognito (pool, client, domain, Google, groups, triggers) | DONE        |
| 3. Monitoring                                               | Not started |
| 4. SAM template fix (DeletionPolicy)                        | Not started |
| 5. Frontend config (new Cognito IDs)                        | Not started |
| 6. Verification                                             | Not started |

## New Resource IDs

- **Cognito User Pool ID**: eu-west-1_fcUkvwjH5
- **Cognito Client ID**: 6jhvk853b0lfg9q1m861qs0cug
- **Cognito Domain**: h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com

## Completed

### 1. DynamoDB tables recreated and data restored

All 7 tables created with DeletionProtection enabled, PITR enabled, on-demand billing:

| Table       | Items | GSIs                                  |
| ----------- | ----- | ------------------------------------- |
| Members     | 1229  | none                                  |
| Memberships | 8     | none                                  |
| Orders      | 58    | CustomerOrdersIndex, OrderStatusIndex |
| Payments    | 2     | MemberPaymentsIndex                   |
| Events      | 11    | none                                  |
| Carts       | 77    | CustomerCartsIndex                    |
| Producten   | 25    | none                                  |

### 2. Cognito fully restored

- User Pool: eu-west-1_fcUkvwjH5
- Client: 6jhvk853b0lfg9q1m861qs0cug (OAuth code flow, email/openid/profile)
- Domain: h-dcn-auth-506221081911
- Google Identity Provider: configured
- 29 groups created
- Lambda triggers attached (CustomMessage, PostConfirmation, PostAuthentication, PreSignUp)
- Lambda invoke permissions granted
- Users migrate on first login via Migration Lambda Trigger

## Remaining

### 3. Monitoring (low priority)

- [ ] CloudWatch Dashboard
- [ ] Lambda error alarm + SNS topic

### 4. SAM template fix

- [ ] Add DeletionPolicy: Retain to all stateful resources in template.yaml
- [ ] Keep deploy-backend.yml disabled until verified

### 5. Frontend configuration

- [ ] Update GitHub Secrets for the frontend deploy:
  - REACT_APP_USER_POOL_ID = eu-west-1_fcUkvwjH5
  - REACT_APP_USER_POOL_WEB_CLIENT_ID = 6jhvk853b0lfg9q1m861qs0cug
  - REACT_APP_COGNITO_DOMAIN = h-dcn-auth-506221081911
- [ ] Update HdcnCognitoAdminFunction environment variable to new pool ID

### 6. Verification

- [ ] Test login (email/password)
- [ ] Test Google SSO
- [ ] Test API returns data
- [ ] Test portal.h-dcn.nl end-to-end
