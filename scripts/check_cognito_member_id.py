import boto3

cognito = boto3.client('cognito-idp', region_name='eu-west-1')
user_pool_id = 'eu-west-1_OAT3oPCIm'

# List users with this email
response = cognito.list_users(
    UserPoolId=user_pool_id,
    Filter='email = "peter@pgeers.nl"'
)

for user in response.get('Users', []):
    print(f"Username: {user['Username']}")
    print(f"Status: {user.get('UserStatus')}")
    print(f"Enabled: {user.get('Enabled')}")
    for attr in user.get('Attributes', []):
        print(f"  {attr['Name']}: {attr['Value']}")
    print()
