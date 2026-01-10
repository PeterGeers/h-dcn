/**
 * Check which Google APIs are enabled by testing discovery endpoints
 */

const https = require('https');
const fs = require('fs');

function loadCredentials() {
  try {
    const secretsContent = fs.readFileSync('.secrets', 'utf8');
    const credentials = {};
    
    secretsContent.split('\n').forEach(line => {
      if (line.includes('=') && !line.startsWith('#')) {
        const [key, value] = line.split('=');
        credentials[key.trim()] = value.trim();
      }
    });
    
    return {
      projectId: credentials.GOOGLE_PROJECT_ID,
      clientId: credentials.GOOGLE_CLIENT_ID
    };
  } catch (error) {
    throw new Error(`Failed to load credentials: ${error.message}`);
  }
}

function makeHttpsRequest(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          data: data
        });
      });
    }).on('error', reject);
  });
}

async function checkAPIs() {
  const credentials = loadCredentials();
  
  console.log('🔍 Checking Google API Status');
  console.log('='.repeat(50));
  console.log(`Project: ${credentials.projectId}`);
  console.log('='.repeat(50));

  const apis = [
    {
      name: 'People API',
      url: 'https://people.googleapis.com/$discovery/rest?version=v1',
      description: 'Modern contacts and user profiles'
    },
    {
      name: 'Gmail API', 
      url: 'https://gmail.googleapis.com/$discovery/rest?version=v1',
      description: 'Email sending and reading'
    },
    {
      name: 'Contacts API',
      url: 'https://www.google.com/m8/feeds/contacts/default/full?max-results=1',
      description: 'Legacy contacts API'
    }
  ];

  console.log('\n📋 Testing API Discovery Endpoints:\n');

  for (const api of apis) {
    try {
      console.log(`Testing ${api.name}...`);
      const response = await makeHttpsRequest(api.url);
      
      if (response.statusCode === 200) {
        console.log(`✅ ${api.name} - Available`);
      } else if (response.statusCode === 403) {
        console.log(`❌ ${api.name} - Not enabled (403 Forbidden)`);
      } else {
        console.log(`⚠️  ${api.name} - Status: ${response.statusCode}`);
      }
    } catch (error) {
      console.log(`❌ ${api.name} - Error: ${error.message}`);
    }
  }

  console.log('\n📖 How to Enable APIs:');
  console.log('1. Go to: https://console.cloud.google.com/apis/library?project=' + credentials.projectId);
  console.log('2. Search for each API name and click "Enable"');
  console.log('3. Required APIs:');
  apis.forEach(api => {
    console.log(`   - ${api.name}: ${api.description}`);
  });

  console.log('\n🔗 Direct Links:');
  console.log(`- API Dashboard: https://console.cloud.google.com/apis/dashboard?project=${credentials.projectId}`);
  console.log(`- API Library: https://console.cloud.google.com/apis/library?project=${credentials.projectId}`);
}

checkAPIs().catch(console.error);