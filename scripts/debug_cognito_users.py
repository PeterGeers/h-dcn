import boto3

cognito = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Get all users
users = []
params = {'UserPoolId': USER_POOL_ID}
while True:
    response = cognito.list_users(**params)
    users.extend(response['Users'])
    if 'PaginationToken' in response:
        params['PaginationToken'] = response['PaginationToken']
    else:
        break

print(f"Total users: {len(users)}")
print()

# Group by email
by_email = {}
for user in users:
    email = None
    for attr in user.get('Attributes', []):
        if attr['Name'] == 'email':
            email = attr['Value']
            break
    key = (email or 'NO_EMAIL').lower()
    by_email.setdefault(key, []).append(user)

# Show emails with multiple accounts
for email, accounts in sorted(by_email.items()):
    if len(accounts) >= 2:
        print(f"DUPLICATE: {email} ({len(accounts)} accounts)")
        for acc in accounts:
            print(f"  - {acc['Username']}  (status: {acc.get('UserStatus')})")
        print()

# Also show peter specifically
print("--- peter@pgeers.nl ---")
for user in users:
    username = user['Username']
    email = None
    for attr in user.get('Attributes', []):
        if attr['Name'] == 'email':
            email = attr['Value']
    if email and 'pgeers' in email.lower():
        print(f"  Username: {username}  Status: {user.get('UserStatus')}")
        for attr in user.get('Attributes', []):
            print(f"    {attr['Name']}: {attr['Value']}")
        print()
