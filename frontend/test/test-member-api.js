const axios = require('axios');

const API_BASE_URL = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function testMemberAPI() {
  // Test with a sample member_id - replace with actual member_id from Cognito
  const testMemberId = '12345'; // Replace with real member_id
  
  console.log('Testing member API...');
  console.log('API Base URL:', API_BASE_URL);
  console.log('Testing member_id:', testMemberId);
  
  try {
    // Test 1: Get member by ID
    console.log('\n--- Test 1: GET /members/{member_id} ---');
    const response1 = await axios.get(`${API_BASE_URL}/members/${testMemberId}`);
    console.log('Status:', response1.status);
    console.log('Data:', response1.data);
  } catch (error1) {
    console.log('Error:', error1.response?.status, error1.response?.data || error1.message);
  }
  
  try {
    // Test 2: Get all members (if endpoint exists)
    console.log('\n--- Test 2: GET /members ---');
    const response2 = await axios.get(`${API_BASE_URL}/members`);
    console.log('Status:', response2.status);
    console.log('Data:', response2.data);
  } catch (error2) {
    console.log('Error:', error2.response?.status, error2.response?.data || error2.message);
  }
  
  try {
    // Test 3: Get member by email (if endpoint exists)
    console.log('\n--- Test 3: GET /members?email=test@example.com ---');
    const response3 = await axios.get(`${API_BASE_URL}/members?email=test@example.com`);
    console.log('Status:', response3.status);
    console.log('Data:', response3.data);
  } catch (error3) {
    console.log('Error:', error3.response?.status, error3.response?.data || error3.message);
  }
}

testMemberAPI();