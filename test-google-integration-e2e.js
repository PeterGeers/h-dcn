/**
 * Google Mail Integration - End-to-End Test
 * Tests the complete authentication and API workflow using actual credentials
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const { URL } = require('url');
const querystring = require('querystring');

class GoogleIntegrationTester {
  constructor() {
    this.credentials = this.loadCredentials();
    this.accessToken = null;
    this.refreshToken = null;
    this.userInfo = null;
  }

  loadCredentials() {
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
        clientSecret: credentials.GOOGLE_CLIENT_SECRET,
        redirectUri: 'http://localhost:8080/auth/callback'
      };
    } catch (error) {
      throw new Error(`Failed to load credentials: ${error.message}`);
    }
  }

  // Step 1: Generate OAuth URL and start local server
  async startAuthFlow() {
    console.log('🚀 Starting OAuth Authentication Flow...\n');
    
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
        client_id: this.credentials.clientId,
        redirect_uri: this.credentials.redirectUri,
        scope: scopes.join(' '),
        response_type: 'code',
        access_type: 'offline',
        prompt: 'consent',
        state: 'test-state-' + Date.now(),
        include_granted_scopes: 'true'
      });

    console.log('📋 OAuth URL generated:');
    console.log(authUrl);
    console.log('\n🌐 Starting local callback server on port 8080...');

    return new Promise((resolve, reject) => {
      const server = http.createServer(async (req, res) => {
        const url = new URL(req.url, `http://localhost:8080`);
        
        if (url.pathname === '/auth/callback') {
          const code = url.searchParams.get('code');
          const error = url.searchParams.get('error');
          
          if (error) {
            res.writeHead(400, { 'Content-Type': 'text/html' });
            res.end(`<h1>Authentication Error</h1><p>${error}</p>`);
            server.close();
            reject(new Error(`OAuth error: ${error}`));
            return;
          }
          
          if (code) {
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(`
              <h1>✅ Authentication Successful!</h1>
              <p>Authorization code received. You can close this window.</p>
              <p>Code: <code>${code.substring(0, 20)}...</code></p>
              <script>setTimeout(() => window.close(), 3000);</script>
            `);
            
            server.close();
            resolve(code);
            return;
          }
        }
        
        // Default response
        res.writeHead(404, { 'Content-Type': 'text/html' });
        res.end('<h1>404 - Not Found</h1>');
      });

      server.listen(8080, () => {
        console.log('✅ Callback server started on http://localhost:8080');
        console.log('\n📖 Instructions:');
        console.log('1. Copy the OAuth URL above');
        console.log('2. Open it in your browser');
        console.log('3. Sign in with your Google account');
        console.log('4. Grant the requested permissions');
        console.log('5. Wait for the callback...\n');
        console.log('⏳ Waiting for OAuth callback (timeout: 5 minutes)...');
      });

      // Timeout after 5 minutes
      setTimeout(() => {
        server.close();
        reject(new Error('OAuth flow timeout - no callback received within 5 minutes'));
      }, 5 * 60 * 1000);
    });
  }

  // Step 2: Exchange authorization code for tokens
  async exchangeCodeForTokens(authCode) {
    console.log('\n🔄 Exchanging authorization code for access tokens...');
    
    const tokenData = querystring.stringify({
      client_id: this.credentials.clientId,
      client_secret: this.credentials.clientSecret,
      code: authCode,
      grant_type: 'authorization_code',
      redirect_uri: this.credentials.redirectUri
    });

    try {
      const response = await this.makeHttpsRequest({
        hostname: 'oauth2.googleapis.com',
        path: '/token',
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Content-Length': Buffer.byteLength(tokenData)
        }
      }, tokenData);

      if (response.statusCode !== 200) {
        throw new Error(`Token exchange failed: ${response.statusCode} - ${response.data}`);
      }

      const tokens = JSON.parse(response.data);
      this.accessToken = tokens.access_token;
      this.refreshToken = tokens.refresh_token;

      console.log('✅ Tokens received successfully');
      console.log(`   Access Token: ${this.accessToken.substring(0, 20)}...`);
      console.log(`   Refresh Token: ${this.refreshToken ? this.refreshToken.substring(0, 20) + '...' : 'Not provided'}`);
      console.log(`   Expires In: ${tokens.expires_in} seconds`);
      console.log(`   Token Type: ${tokens.token_type}`);

      return tokens;
    } catch (error) {
      throw new Error(`Token exchange failed: ${error.message}`);
    }
  }

  // Step 3: Test user info API
  async testUserInfo() {
    console.log('\n👤 Testing User Info API...');
    
    try {
      const response = await this.makeHttpsRequest({
        hostname: 'www.googleapis.com',
        path: '/oauth2/v2/userinfo',
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });

      if (response.statusCode !== 200) {
        throw new Error(`User info request failed: ${response.statusCode}`);
      }

      this.userInfo = JSON.parse(response.data);
      
      console.log('✅ User info retrieved successfully');
      console.log(`   Email: ${this.userInfo.email}`);
      console.log(`   Name: ${this.userInfo.name}`);
      console.log(`   ID: ${this.userInfo.id}`);
      console.log(`   Verified Email: ${this.userInfo.verified_email}`);

      return this.userInfo;
    } catch (error) {
      throw new Error(`User info test failed: ${error.message}`);
    }
  }

  // Step 4: Test Google People API (contacts)
  async testPeopleAPI() {
    console.log('\n👥 Testing Google People API...');
    
    try {
      // Test 1: List contact groups (this is what we'll use for distribution lists)
      console.log('   Testing contact groups list...');
      const groupsResponse = await this.makeHttpsRequest({
        hostname: 'people.googleapis.com',
        path: '/v1/contactGroups',
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });

      if (groupsResponse.statusCode !== 200) {
        throw new Error(`Contact groups request failed: ${groupsResponse.statusCode}`);
      }

      const groupsData = JSON.parse(groupsResponse.data);
      console.log(`   ✅ Contact groups retrieved: ${groupsData.contactGroups?.length || 0} groups found`);
      
      if (groupsData.contactGroups && groupsData.contactGroups.length > 0) {
        console.log('   📋 Existing groups:');
        groupsData.contactGroups.slice(0, 3).forEach(group => {
          console.log(`      - ${group.name} (${group.memberCount || 0} members)`);
        });
      }

      // Test 2: Get user's own contact info
      console.log('\n   Testing people connections...');
      const connectionsResponse = await this.makeHttpsRequest({
        hostname: 'people.googleapis.com',
        path: '/v1/people/me/connections?personFields=names,emailAddresses&pageSize=1',
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });

      if (connectionsResponse.statusCode === 200) {
        const connectionsData = JSON.parse(connectionsResponse.data);
        console.log(`   ✅ Connections accessible: ${connectionsData.totalItems || 0} total contacts`);
      } else {
        console.log(`   ⚠️  Connections request returned: ${connectionsResponse.statusCode}`);
      }

      return { groups: groupsData, connectionsStatus: connectionsResponse.statusCode };
    } catch (error) {
      throw new Error(`People API test failed: ${error.message}`);
    }
  }

  // Step 5: Test Gmail API
  async testGmailAPI() {
    console.log('\n📧 Testing Gmail API...');
    
    try {
      // Test 1: Get user's Gmail profile
      console.log('   Testing Gmail profile access...');
      const profileResponse = await this.makeHttpsRequest({
        hostname: 'gmail.googleapis.com',
        path: '/gmail/v1/users/me/profile',
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });

      if (profileResponse.statusCode === 200) {
        const profileData = JSON.parse(profileResponse.data);
        console.log(`   ✅ Gmail profile accessible`);
        console.log(`      Email: ${profileData.emailAddress}`);
        console.log(`      Messages Total: ${profileData.messagesTotal}`);
        console.log(`      Threads Total: ${profileData.threadsTotal}`);
      } else {
        throw new Error(`Gmail profile request failed: ${profileResponse.statusCode}`);
      }

      // Test 2: List labels (basic read access)
      console.log('\n   Testing Gmail labels access...');
      const labelsResponse = await this.makeHttpsRequest({
        hostname: 'gmail.googleapis.com',
        path: '/gmail/v1/users/me/labels',
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });

      if (labelsResponse.statusCode === 200) {
        const labelsData = JSON.parse(labelsResponse.data);
        console.log(`   ✅ Gmail labels accessible: ${labelsData.labels?.length || 0} labels found`);
        
        // Show some common labels
        const commonLabels = labelsData.labels?.filter(label => 
          ['INBOX', 'SENT', 'DRAFT', 'SPAM'].includes(label.id)
        ) || [];
        
        if (commonLabels.length > 0) {
          console.log('   📋 Common labels found:');
          commonLabels.forEach(label => {
            console.log(`      - ${label.name} (${label.id})`);
          });
        }
      } else {
        throw new Error(`Gmail labels request failed: ${labelsResponse.statusCode}`);
      }

      return { profileStatus: profileResponse.statusCode, labelsStatus: labelsResponse.statusCode };
    } catch (error) {
      throw new Error(`Gmail API test failed: ${error.message}`);
    }
  }

  // Step 6: Test creating a test contact group (distribution list)
  async testCreateContactGroup() {
    console.log('\n📝 Testing Contact Group Creation...');
    
    const testGroupName = `H-DCN Test Group ${new Date().toISOString().split('T')[0]}`;
    
    try {
      const createData = JSON.stringify({
        contactGroup: {
          name: testGroupName
        }
      });

      const response = await this.makeHttpsRequest({
        hostname: 'people.googleapis.com',
        path: '/v1/contactGroups',
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`,
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(createData)
        }
      }, createData);

      if (response.statusCode === 200 || response.statusCode === 201) {
        const groupData = JSON.parse(response.data);
        console.log(`✅ Test contact group created successfully`);
        console.log(`   Name: ${groupData.name}`);
        console.log(`   Resource Name: ${groupData.resourceName}`);
        console.log(`   Group Type: ${groupData.groupType}`);

        // Clean up - delete the test group
        await this.deleteTestContactGroup(groupData.resourceName);
        
        return groupData;
      } else {
        throw new Error(`Group creation failed: ${response.statusCode} - ${response.data}`);
      }
    } catch (error) {
      throw new Error(`Contact group creation test failed: ${error.message}`);
    }
  }

  // Helper: Delete test contact group
  async deleteTestContactGroup(resourceName) {
    try {
      console.log('   🧹 Cleaning up test group...');
      
      const response = await this.makeHttpsRequest({
        hostname: 'people.googleapis.com',
        path: `/v1/${resourceName}`,
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });

      if (response.statusCode === 200 || response.statusCode === 204) {
        console.log('   ✅ Test group deleted successfully');
      } else {
        console.log(`   ⚠️  Test group deletion returned: ${response.statusCode}`);
      }
    } catch (error) {
      console.log(`   ⚠️  Failed to delete test group: ${error.message}`);
    }
  }

  // Step 6: Test token refresh
  async testTokenRefresh() {
    if (!this.refreshToken) {
      console.log('\n🔄 Skipping token refresh test (no refresh token available)');
      return;
    }

    console.log('\n🔄 Testing Token Refresh...');
    
    try {
      const refreshData = querystring.stringify({
        client_id: this.credentials.clientId,
        client_secret: this.credentials.clientSecret,
        refresh_token: this.refreshToken,
        grant_type: 'refresh_token'
      });

      const response = await this.makeHttpsRequest({
        hostname: 'oauth2.googleapis.com',
        path: '/token',
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Content-Length': Buffer.byteLength(refreshData)
        }
      }, refreshData);

      if (response.statusCode === 200) {
        const newTokens = JSON.parse(response.data);
        console.log('✅ Token refresh successful');
        console.log(`   New Access Token: ${newTokens.access_token.substring(0, 20)}...`);
        console.log(`   Expires In: ${newTokens.expires_in} seconds`);
        
        // Update our access token for any remaining tests
        this.accessToken = newTokens.access_token;
        
        return newTokens;
      } else {
        throw new Error(`Token refresh failed: ${response.statusCode} - ${response.data}`);
      }
    } catch (error) {
      console.log(`❌ Token refresh test failed: ${error.message}`);
    }
  }

  // Helper function for HTTPS requests
  makeHttpsRequest(options, data = null) {
    return new Promise((resolve, reject) => {
      const req = https.request(options, (res) => {
        let responseData = '';
        
        res.on('data', (chunk) => {
          responseData += chunk;
        });
        
        res.on('end', () => {
          resolve({
            statusCode: res.statusCode,
            data: responseData,
            headers: res.headers
          });
        });
      });

      req.on('error', (error) => {
        reject(error);
      });

      req.setTimeout(30000, () => {
        req.destroy();
        reject(new Error('Request timeout'));
      });

      if (data) {
        req.write(data);
      }
      
      req.end();
    });
  }

  // Main test runner
  async runFullTest() {
    console.log('🚀 Google Mail Integration - End-to-End Test');
    console.log('='.repeat(70));
    console.log(`Project ID: ${this.credentials.projectId}`);
    console.log(`Client ID: ${this.credentials.clientId}`);
    console.log('='.repeat(70));

    const results = {
      auth: false,
      tokens: false,
      userInfo: false,
      peopleAPI: false,
      gmailAPI: false,
      createGroup: false,
      tokenRefresh: false
    };

    try {
      // Step 1: OAuth Flow
      const authCode = await this.startAuthFlow();
      results.auth = true;
      
      // Step 2: Token Exchange
      await this.exchangeCodeForTokens(authCode);
      results.tokens = true;
      
      // Step 3: User Info
      await this.testUserInfo();
      results.userInfo = true;
      
      // Step 4: People API
      await this.testPeopleAPI();
      results.peopleAPI = true;
      
      // Step 5: Gmail API
      await this.testGmailAPI();
      results.gmailAPI = true;
      
      // Step 6: Create Contact Group
      await this.testCreateContactGroup();
      results.createGroup = true;
      
      // Step 7: Token Refresh
      await this.testTokenRefresh();
      results.tokenRefresh = true;
      
      // Final Summary
      this.printFinalSummary(results);
      
    } catch (error) {
      console.error(`\n❌ Test failed: ${error.message}`);
      this.printFinalSummary(results, error);
    }
  }

  printFinalSummary(results, error = null) {
    console.log('\n' + '='.repeat(70));
    console.log('📊 END-TO-END TEST SUMMARY');
    console.log('='.repeat(70));

    const tests = [
      { name: 'OAuth Authentication', key: 'auth', critical: true },
      { name: 'Token Exchange', key: 'tokens', critical: true },
      { name: 'User Info API', key: 'userInfo', critical: true },
      { name: 'Google People API', key: 'peopleAPI', critical: true },
      { name: 'Gmail API', key: 'gmailAPI', critical: true },
      { name: 'Contact Group Creation', key: 'createGroup', critical: true },
      { name: 'Token Refresh', key: 'tokenRefresh', critical: false }
    ];

    console.log('\n📋 Test Results:');
    tests.forEach(test => {
      const status = results[test.key] ? '✅' : '❌';
      const critical = test.critical ? ' (Critical)' : ' (Optional)';
      console.log(`   ${status} ${test.name}${critical}`);
    });

    const criticalTests = tests.filter(t => t.critical);
    const passedCritical = criticalTests.filter(t => results[t.key]).length;
    const totalCritical = criticalTests.length;

    console.log(`\n🎯 Critical Tests: ${passedCritical}/${totalCritical} passed`);

    if (passedCritical === totalCritical) {
      console.log('\n🎉 SUCCESS: Your Google credentials are fully functional!');
      console.log('\n✅ Ready for Google Mail Integration:');
      console.log('   - OAuth authentication works');
      console.log('   - Google People API is accessible');
      console.log('   - Gmail API is accessible');
      console.log('   - Contact group creation is functional');
      console.log('   - All required permissions are granted');
      
      console.log('\n🚀 Next Steps:');
      console.log('   1. Configure redirect URIs for your production domain');
      console.log('   2. Test the integration in your React application');
      console.log('   3. Create distribution lists from your member data');
    } else {
      console.log('\n⚠️  ISSUES FOUND: Some critical tests failed');
      
      if (error) {
        console.log(`\n❌ Last Error: ${error.message}`);
      }
      
      console.log('\n🔧 Troubleshooting:');
      console.log('   1. Check Google Cloud Console API enablement');
      console.log('   2. Verify OAuth client configuration');
      console.log('   3. Ensure correct redirect URIs are set');
      console.log('   4. Check if account has necessary permissions');
    }

    console.log('\n' + '='.repeat(70));
  }
}

// Run the test
if (require.main === module) {
  const tester = new GoogleIntegrationTester();
  tester.runFullTest().catch(console.error);
}

module.exports = GoogleIntegrationTester;