"""
One-time script to link existing Google federated users to their native Cognito accounts.
After running this, the Google user will be merged into the native user.

Usage: python scripts/link_google_to_native_users.py
"""

import boto3

cognito = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'


def get_all_users():
    """Get all users from the user pool"""
    users = []
    params = {'UserPoolId': USER_POOL_ID}
    while True:
        response = cognito.list_users(**params)
        users.extend(response['Users'])
        if 'PaginationToken' in response:
            params['PaginationToken'] = response['PaginationToken']
        else:
            break
    return users


def main():
    users = get_all_users()

    # Group users by email
    by_email = {}
    for user in users:
        email = None
        for attr in user.get('Attributes', []):
            if attr['Name'] == 'email':
                email = attr['Value']
                break
        if email:
            by_email.setdefault(email.lower(), []).append(user)

    linked = 0
    for email, accounts in by_email.items():
        if len(accounts) < 2:
            continue

        # Find native and federated accounts
        native = None
        federated = []
        for acc in accounts:
            username = acc['Username']
            if username.startswith('Google_') or username.startswith('Facebook_'):
                federated.append(acc)
            else:
                native = acc

        if not native or not federated:
            continue

        native_username = native['Username']
        print(f"\n{'='*60}")
        print(f"Email: {email}")
        print(f"  Native user: {native_username}")

        for fed in federated:
            fed_username = fed['Username']
            # Parse provider
            if fed_username.startswith('Google_'):
                provider_name = 'Google'
                provider_user_id = fed_username[len('Google_'):]
            elif fed_username.startswith('Facebook_'):
                provider_name = 'Facebook'
                provider_user_id = fed_username[len('Facebook_'):]
            else:
                continue

            print(f"  Federated user: {fed_username} ({provider_name})")

            try:
                # First delete the federated user (required before linking)
                cognito.admin_delete_user(
                    UserPoolId=USER_POOL_ID,
                    Username=fed_username
                )
                print(f"  Deleted federated user: {fed_username}")

                # Now link the provider to the native user
                cognito.admin_link_provider_for_user(
                    UserPoolId=USER_POOL_ID,
                    DestinationUser={
                        'ProviderName': 'Cognito',
                        'ProviderAttributeValue': native_username
                    },
                    SourceUser={
                        'ProviderName': provider_name,
                        'ProviderAttributeName': 'Cognito_Subject',
                        'ProviderAttributeValue': provider_user_id
                    }
                )
                print(f"  ✅ Linked {provider_name} to native user {native_username}")
                linked += 1

            except Exception as e:
                print(f"  ❌ Error linking: {str(e)}")

    print(f"\n{'='*60}")
    print(f"Done. Linked {linked} federated account(s) to native users.")
    if linked > 0:
        print("Users can now log in with Google and it will use their native account.")


if __name__ == '__main__':
    main()
