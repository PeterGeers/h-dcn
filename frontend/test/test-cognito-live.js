// Test live Cognito connection
import { CognitoIdentityProviderClient, ListUsersCommand, ListGroupsCommand } from '@aws-sdk/client-cognito-identity-provider';

const client = new CognitoIdentityProviderClient({
  region: 'eu-west-1'
});

const userPoolId = 'eu-west-1_VtKQHhXGN';

async function testCognitoAccess() {
  console.log('🧪 Testing live Cognito access...\n');

  try {
    // Test listing users
    console.log('1️⃣ Testing ListUsers...');
    const usersCommand = new ListUsersCommand({
      UserPoolId: userPoolId,
      Limit: 5
    });
    const usersResponse = await client.send(usersCommand);
    console.log(`✅ Found ${usersResponse.Users?.length || 0} users`);

    // Test listing groups
    console.log('\n2️⃣ Testing ListGroups...');
    const groupsCommand = new ListGroupsCommand({
      UserPoolId: userPoolId
    });
    const groupsResponse = await client.send(groupsCommand);
    console.log(`✅ Found ${groupsResponse.Groups?.length || 0} groups`);
    
    if (groupsResponse.Groups?.length > 0) {
      console.log('Groups:', groupsResponse.Groups.map(g => g.GroupName).join(', '));
    }

    console.log('\n🎉 Cognito access working! You can use the management interface.');
    
  } catch (error) {
    console.log('❌ Error:', error.message);
    
    if (error.name === 'AccessDeniedException') {
      console.log('\n🔐 Permission issue - check IAM policies');
    } else if (error.name === 'ResourceNotFoundException') {
      console.log('\n🔍 User pool not found - check pool ID');
    } else {
      console.log('\n⚠️ Other error - check AWS credentials');
    }
  }
}

testCognitoAccess();