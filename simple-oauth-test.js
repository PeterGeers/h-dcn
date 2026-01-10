/**
 * Simple OAuth URL generator for testing
 */

const fs = require('fs');
const querystring = require('querystring');

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

function generateOAuthURL() {
  const credentials = loadCredentials();
  
  const scopes = [
    'https://www.googleapis.com/auth/contacts',
    'https://www.googleapis.com/auth/contacts.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
  ];

  const authUrl = 'https://accounts.google.com/o/oauth2/v2/auth?' +
    querystring.stringify({
      client_id: credentials.clientId,
      redirect_uri: 'http://localhost:8080/auth/callback',
      scope: scopes.join(' '),
      response_type: 'code',
      access_type: 'offline',
      prompt: 'consent',
      state: 'test-' + Date.now()
    });

  console.log('🚀 Google OAuth Test URL Generator');
  console.log('='.repeat(60));
  console.log(`Project: ${credentials.projectId}`);
  console.log(`Client ID: ${credentials.clientId}`);
  console.log('='.repeat(60));
  
  console.log('\n📋 Required APIs (must be enabled first):');
  console.log('   - People API (contacts)');
  console.log('   - Gmail API (email)');
  console.log('   - Google+ API (user info)');
  
  console.log('\n🔗 OAuth URL:');
  console.log(authUrl);
  
  console.log('\n📖 Instructions:');
  console.log('1. Enable the required APIs in Google Cloud Console');
  console.log('2. Copy the URL above and open in browser');
  console.log('3. Sign in and grant permissions');
  console.log('4. Copy the authorization code from callback URL');
  console.log('5. Use: node test-with-auth-code.js "your-code"');
  
  console.log('\n⚠️  Note: Authorization codes expire in ~10 minutes');
}

generateOAuthURL();