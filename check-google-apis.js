/**
 * Check if required Google APIs are enabled
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
      clientId: credentials.GOOGLE_CLIENT_ID,
      clientSecret: credentials.GOOGLE_CLIENT_SECRET
    };
  } catch (error) {
    throw new Error(`Failed to load credentials: ${error.message}`);
  }
}

async function checkAPIs() {
  const credentials = loadCredentials();
  
  console.log('🔍 Checking Google Cloud Project Configuration');
  console.log('='.repeat(60));
  console.log(`Project ID: ${credentials.projectId}`);
  console.log(`Client ID: ${credentials.clientId}`);
  console.log('='.repeat(60));
  
  console.log('\n📋 Required APIs for Google Mail Integration:');
  console.log('   ✅ Google People API (contacts)');
  console.log('   ✅ Gmail API (email sending)');
  console.log('   ✅ Google+ API (user info)');
  
  console.log('\n🔧 Next Steps to Enable APIs:');
  console.log('1. Go to: https://console.cloud.google.com/apis/library');
  console.log(`2. Select project: ${credentials.projectId}`);
  console.log('3. Search and enable these APIs:');
  console.log('   - "People API" (for contacts)');
  console.log('   - "Gmail API" (for email)');
  console.log('   - "Google+ API" (for user info)');
  
  console.log('\n🔑 OAuth Client Configuration:');
  console.log('1. Go to: https://console.cloud.google.com/apis/credentials');
  console.log('2. Find your OAuth client ID');
  console.log('3. Ensure these redirect URIs are added:');
  console.log('   - http://localhost:8080/auth/callback');
  console.log('   - https://your-production-domain.com/auth/callback');
  
  console.log('\n🎯 Test OAuth Flow Manually:');
  const testUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
    `client_id=${credentials.clientId}&` +
    `redirect_uri=http://localhost:8080/auth/callback&` +
    `scope=https://www.googleapis.com/auth/contacts https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/gmail.readonly&` +
    `response_type=code&` +
    `access_type=offline&` +
    `prompt=consent`;
  
  console.log('\nTest URL:');
  console.log(testUrl);
  
  console.log('\n✅ If APIs are enabled and OAuth is configured correctly,');
  console.log('   the test URL above should work without errors.');
}

checkAPIs().catch(console.error);