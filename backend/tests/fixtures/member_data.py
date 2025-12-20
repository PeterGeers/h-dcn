# Test fixtures for member data

SAMPLE_MEMBERS = [
    {
        'id': 'member-1',
        'username': 'john.doe',
        'email': 'john.doe@hdcn.nl',
        'firstName': 'John',
        'lastName': 'Doe',
        'region': 'Noord',
        'status': 'active',
        'membershipType': 'full'
    },
    {
        'id': 'member-2', 
        'username': 'jane.smith',
        'email': 'jane.smith@hdcn.nl',
        'firstName': 'Jane',
        'lastName': 'Smith',
        'region': 'Zuid',
        'status': 'active',
        'membershipType': 'associate'
    }
]

SAMPLE_MEMBER_CREATE_REQUEST = {
    'username': 'new.member',
    'email': 'new.member@hdcn.nl',
    'firstName': 'New',
    'lastName': 'Member',
    'region': 'Oost',
    'membershipType': 'full',
    'tempPassword': 'TempPass123!',
    'groups': 'hdcnLeden'
}