// Script om API base URL uit DynamoDB te tonen
const API_BASE_URL = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

async function checkApiUrl() {
  try {
    const response = await fetch(`${API_BASE_URL}/parameters/name/api_base_url`);
    const data = await response.json();
    
    console.log('API Base URL parameter:');
    console.log('======================');
    console.log('Name:', data.name);
    console.log('Value:', data.value);
    
  } catch (error) {
    console.error('Fout bij ophalen API URL:', error);
  }
}

checkApiUrl();