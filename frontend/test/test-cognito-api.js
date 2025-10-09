// Test Cognito API endpoints
const API_BASE = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function testCognitoAPI() {
  console.log('🧪 Testing Cognito API endpoints...\n');

  try {
    // Test 1: GET /cognito/users
    console.log('1️⃣ Testing GET /cognito/users');
    const usersResponse = await fetch(`${API_BASE}/cognito/users`);
    console.log(`Status: ${usersResponse.status}`);
    if (usersResponse.ok) {
      const users = await usersResponse.json();
      console.log(`✅ Found ${users.length} users`);
    } else {
      console.log('❌ Failed:', await usersResponse.text());
    }

    // Test 2: GET /cognito/groups  
    console.log('\n2️⃣ Testing GET /cognito/groups');
    const groupsResponse = await fetch(`${API_BASE}/cognito/groups`);
    console.log(`Status: ${groupsResponse.status}`);
    if (groupsResponse.ok) {
      const groups = await groupsResponse.json();
      console.log(`✅ Found ${groups.length} groups`);
      groups.forEach(group => console.log(`  - ${group.GroupName}: ${group.Description || 'No description'}`));
    } else {
      console.log('❌ Failed:', await groupsResponse.text());
    }

    // Test 3: GET /cognito/pool
    console.log('\n3️⃣ Testing GET /cognito/pool');
    const poolResponse = await fetch(`${API_BASE}/cognito/pool`);
    console.log(`Status: ${poolResponse.status}`);
    if (poolResponse.ok) {
      const pool = await poolResponse.json();
      console.log(`✅ Pool: ${pool.Name} (${pool.Id})`);
    } else {
      console.log('❌ Failed:', await poolResponse.text());
    }

  } catch (error) {
    console.log('❌ Network error:', error.message);
  }

  console.log('\n🏁 API test complete');
}

testCognitoAPI();