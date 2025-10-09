// Test script to check Cognito API
const baseUrl = 'http://localhost:3001'; // Adjust if different

async function testCreateUser() {
  try {
    const response = await fetch(`${baseUrl}/cognito/users`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: 'test@h-dcn.nl',
        email: 'test@h-dcn.nl',
        tempPassword: 'WelkomHDCN2024!',
        attributes: {
          given_name: 'Test',
          family_name: 'User'
        },
        groups: 'hdcnLeden'
      })
    });

    const result = await response.text();
    console.log('Status:', response.status);
    console.log('Response:', result);
    
    if (!response.ok) {
      console.error('API Error:', response.status, result);
    } else {
      console.log('✅ User created successfully');
    }
  } catch (error) {
    console.error('Network error:', error.message);
  }
}

testCreateUser();