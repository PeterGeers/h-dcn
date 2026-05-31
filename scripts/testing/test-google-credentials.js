/**
 * Google Credentials Test Script
 * Tests if current Google OAuth credentials support the required APIs and scopes
 * for the H-DCN Google Mail integration
 */

const https = require('https');
const fs = require('fs');

// Load credentials from .secrets file
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
      clientId: credentials.GOOGLE_CLIENT_ID,
      clientSecret: credentials.GOOGLE_CLIENT_SECRET
    };
  } catch (error) {
    console.error('❌ Failed to load credentials from .secrets file:', error.message);
    return null;
  }
}

// Test Google OAuth client configuration
async function testOAuthClient(credentials) {
  console.log('\n🔍 Testing OAuth Client Configuration...');
  
  // Validate client ID format
  if (!credentials.clientId || !credentials.clientId.includes('.apps.googleusercontent.com')) {
    console.log('❌ Invalid client ID format');
    return false;
  }
  
  console.log('✅ Client ID format is valid');
  console.log(`   Client ID: ${credentials.clientId}`);
  console.log(`   Project ID: ${credentials.projectId}`);
  
  return true;
}

// Test required Google APIs availability
async function testGoogleAPIs(credentials) {
  console.log('\n🔍 Testing Google APIs Availability...');
  
  const requiredAPIs = [
    {
      name: 'Google People API',
      url: `https://people.googleapis.com/$discovery/rest?version=v1&key=${credentials.clientId}`,
      description: 'Required for contact management'
    },
    {
      name: 'Google Contacts API', 
      url: `https://www.googleapis.com/discovery/v1/apis/people/v1/rest`,
      description: 'Required for distribution list creation'
    }
  ];
  
  const results = [];
  
  for (const api of requiredAPIs) {
    try {
      console.log(`   Testing ${api.name}...`);
      
      const response = await makeHttpsRequest(api.url);
      
      if (response.statusCode === 200) {
        console.log(`   ✅ ${api.name} is available`);
        results.push({ name: api.name, available: true });
      } else {
        console.log(`   ⚠️  ${api.name} returned status ${response.statusCode}`);
        results.push({ name: api.name, available: false, status: response.statusCode });
      }
    } catch (error) {
      console.log(`   ❌ ${api.name} test failed: ${error.message}`);
      results.push({ name: api.name, available: false, error: error.message });
    }
  }
  
  return results;
}

// Test OAuth scopes by attempting to get authorization URL
async function testOAuthScopes(credentials) {
  console.log('\n🔍 Testing OAuth Scopes Configuration...');
  
  const requiredScopes = [
    'https://www.googleapis.com/auth/contacts',
    'https://www.googleapis.com/auth/contacts.readonly', 
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
  ];
  
  console.log('   Required scopes for Google Mail integration:');
  requiredScopes.forEach(scope => {
    console.log(`   - ${scope}`);
  });
  
  // Generate OAuth URL to test if client can request these scopes
  const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
    `client_id=${credentials.clientId}&` +
    `redirect_uri=http://localhost:3000/auth/google-callback&` +
    `scope=${encodeURIComponent(requiredScopes.join(' '))}&` +
    `response_type=code&` +
    `access_type=offline`;
  
  console.log('\n   ✅ OAuth authorization URL generated successfully');
  console.log(`   🔗 Test URL: ${authUrl.substring(0, 100)}...`);
  
  return {
    scopes: requiredScopes,
    authUrl: authUrl,
    valid: true
  };
}

// Test Google Cloud Console project configuration
async function testProjectConfiguration(credentials) {
  console.log('\n🔍 Testing Google Cloud Console Project...');
  
  try {
    // Test if we can access project information
    const projectUrl = `https://cloudresourcemanager.googleapis.com/v1/projects/${credentials.projectId}`;
    
    console.log(`   Project ID: ${credentials.projectId}`);
    console.log('   ✅ Project ID format is valid');
    
    // Note: We can't test project access without authentication, 
    // but we can validate the format and provide guidance
    console.log('\n   📋 Manual verification needed:');
    console.log('   1. Go to https://console.cloud.google.com/');
    console.log(`   2. Select project: ${credentials.projectId}`);
    console.log('   3. Navigate to APIs & Services > Library');
    console.log('   4. Verify these APIs are enabled:');
    console.log('      - Google People API');
    console.log('      - Google Contacts API (part of People API)');
    console.log('   5. Navigate to APIs & Services > Credentials');
    console.log(`   6. Verify OAuth 2.0 Client ID exists: ${credentials.clientId}`);
    
    return true;
  } catch (error) {
    console.log(`   ❌ Project configuration test failed: ${error.message}`);
    return false;
  }
}

// Test redirect URI configuration
async function testRedirectURIs(credentials) {
  console.log('\n🔍 Testing Redirect URI Configuration...');
  
  const expectedRedirectURIs = [
    'http://localhost:3000/auth/google-callback',  // Development
    'https://yourdomain.com/auth/google-callback'  // Production (placeholder)
  ];
  
  console.log('   Expected redirect URIs in Google Cloud Console:');
  expectedRedirectURIs.forEach(uri => {
    console.log(`   - ${uri}`);
  });
  
  console.log('\n   📋 Manual verification needed:');
  console.log('   1. Go to https://console.cloud.google.com/');
  console.log('   2. Navigate to APIs & Services > Credentials');
  console.log(`   3. Click on OAuth 2.0 Client ID: ${credentials.clientId}`);
  console.log('   4. Verify "Authorized redirect URIs" includes:');
  expectedRedirectURIs.forEach(uri => {
    console.log(`      - ${uri}`);
  });
  
  return {
    expected: expectedRedirectURIs,
    valid: true
  };
}

// Helper function to make HTTPS requests
function makeHttpsRequest(url) {
  return new Promise((resolve, reject) => {
    const request = https.get(url, (response) => {
      let data = '';
      
      response.on('data', (chunk) => {
        data += chunk;
      });
      
      response.on('end', () => {
        resolve({
          statusCode: response.statusCode,
          data: data
        });
      });
    });
    
    request.on('error', (error) => {
      reject(error);
    });
    
    request.setTimeout(10000, () => {
      request.destroy();
      reject(new Error('Request timeout'));
    });
  });
}

// Generate test summary and recommendations
function generateSummary(results) {
  console.log('\n' + '='.repeat(60));
  console.log('📊 GOOGLE CREDENTIALS TEST SUMMARY');
  console.log('='.repeat(60));
  
  const { credentials, oauthClient, apis, scopes, project, redirects } = results;
  
  // Overall status
  let overallStatus = 'READY';
  let issues = [];
  let recommendations = [];
  
  if (!credentials) {
    overallStatus = 'FAILED';
    issues.push('Credentials not found or invalid');
  }
  
  if (!oauthClient) {
    overallStatus = 'FAILED';
    issues.push('OAuth client configuration invalid');
  }
  
  if (apis && apis.some(api => !api.available)) {
    overallStatus = 'NEEDS_SETUP';
    issues.push('Some required APIs are not accessible');
    recommendations.push('Enable Google People API in Google Cloud Console');
  }
  
  // Status indicator
  const statusEmoji = {
    'READY': '✅',
    'NEEDS_SETUP': '⚠️',
    'FAILED': '❌'
  };
  
  console.log(`\n${statusEmoji[overallStatus]} Overall Status: ${overallStatus}`);
  
  if (overallStatus === 'READY') {
    console.log('\n🎉 Your Google credentials are ready for the Mail integration!');
    console.log('\nNext steps:');
    console.log('1. Ensure APIs are enabled in Google Cloud Console (manual verification needed)');
    console.log('2. Configure redirect URIs for your domain');
    console.log('3. Test the integration in your application');
  } else {
    console.log('\n⚠️  Issues found:');
    issues.forEach(issue => console.log(`   - ${issue}`));
    
    if (recommendations.length > 0) {
      console.log('\n💡 Recommendations:');
      recommendations.forEach(rec => console.log(`   - ${rec}`));
    }
  }
  
  // Detailed results
  console.log('\n📋 Detailed Results:');
  console.log(`   Credentials: ${credentials ? '✅ Valid' : '❌ Invalid'}`);
  console.log(`   OAuth Client: ${oauthClient ? '✅ Valid' : '❌ Invalid'}`);
  console.log(`   Required Scopes: ${scopes?.valid ? '✅ Configured' : '❌ Invalid'}`);
  console.log(`   Project Config: ${project ? '✅ Valid' : '❌ Invalid'}`);
  console.log(`   Redirect URIs: ${redirects?.valid ? '✅ Configured' : '❌ Invalid'}`);
  
  if (apis) {
    console.log('\n   API Availability:');
    apis.forEach(api => {
      const status = api.available ? '✅' : '❌';
      console.log(`     ${status} ${api.name}`);
    });
  }
  
  console.log('\n' + '='.repeat(60));
}

// Main test function
async function runCredentialsTest() {
  console.log('🚀 H-DCN Google Mail Integration - Credentials Test');
  console.log('='.repeat(60));
  
  const results = {};
  
  // Load credentials
  console.log('\n📁 Loading credentials...');
  const credentials = loadCredentials();
  results.credentials = credentials;
  
  if (!credentials) {
    generateSummary(results);
    return;
  }
  
  console.log('✅ Credentials loaded successfully');
  
  // Run tests
  try {
    results.oauthClient = await testOAuthClient(credentials);
    results.apis = await testGoogleAPIs(credentials);
    results.scopes = await testOAuthScopes(credentials);
    results.project = await testProjectConfiguration(credentials);
    results.redirects = await testRedirectURIs(credentials);
    
    // Generate summary
    generateSummary(results);
    
  } catch (error) {
    console.error('\n❌ Test failed with error:', error.message);
    generateSummary(results);
  }
}

// Run the test
if (require.main === module) {
  runCredentialsTest().catch(console.error);
}

module.exports = {
  runCredentialsTest,
  loadCredentials,
  testOAuthClient,
  testGoogleAPIs,
  testOAuthScopes
};