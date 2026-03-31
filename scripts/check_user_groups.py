import boto3

cognito = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'
USERNAME = 'c24584c4-5071-70e3-e44e-d3786b406450'

response = cognito.admin_list_groups_for_user(
    UserPoolId=USER_POOL_ID,
    Username=USERNAME
)

groups = [g['GroupName'] for g in response.get('Groups', [])]
print(f"User: {USERNAME}")
print(f"Groups: {groups}")

if not groups:
    print("\nNo groups assigned! Adding hdcnLeden...")
    cognito.admin_add_user_to_group(
        UserPoolId=USER_POOL_ID,
        Username=USERNAME,
        GroupName='hdcnLeden'
    )
    print("Added hdcnLeden group")
