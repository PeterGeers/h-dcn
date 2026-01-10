/**
 * Quick test using the authorization code you already received
 */

const https = require('https');
const fs = require('fs');
const querystring = require('querystring');

class QuickGoogleTest {
  constructor() {
    this.credentials = this.loadCredentials();
    this.accessToken = null;
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

  async exchangeCodeForTokens(authCode) {
    console.log('🔄 Exchanging authorization code for access tokens...');
    
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

      console.log('✅ Tokens received successfully');
      console.log(`   Access Token: ${this.accessToken.substring(0, 20)}...`);
      console.log(`   Expires In: ${tokens.expires_in} seconds`);

      return tokens;
    } catch (error) {
      throw new Error(`Token exchange failed: ${error.message}`);
    }
  }

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

      const userInfo = JSON.parse(response.data);
      
      console.log('✅ User info retrieved successfully');
      console.log(`   Email: ${userInfo.email}`);
      console.log(`   Name: ${userInfo.name}`);
      console.log(`   ID: ${userInfo.id}`);

      return userInfo;
    } catch (error) {
      throw new Error(`User info test failed: ${error.message}`);
    }
  }

  async testPeopleAPI() {
    console.log('\n👥 Testing Google People API...');
    
    try {
      const response = await this.makeHttpsRequest({
        hostname: 'people.googleapis.com',
        path: '/v1/contactGroups',
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });

      if (response.statusCode !== 200) {
        throw new Error(`Contact groups request failed: ${response.statusCode}`);
      }

      const groupsData = JSON.parse(response.data);
      console.log(`✅ Contact groups retrieved: ${groupsData.contactGroups?.length || 0} groups found`);
      
      return groupsData;
    } catch (error) {
      throw new Error(`People API test failed: ${error.message}`);
    }
  }

  async testGmailAPI() {
    console.log('\n📧 Testing Gmail API...');
    
    try {
      const response = await this.makeHttpsRequest({
        hostname: 'gmail.googleapis.com',
        path: '/gmail/v1/users/me/profile',
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });

      if (response.statusCode === 200) {
        const profileData = JSON.parse(response.data);
        console.log(`✅ Gmail profile accessible`);
        console.log(`   Email: ${profileData.emailAddress}`);
        console.log(`   Messages Total: ${profileData.messagesTotal}`);
        
        return profileData;
      } else {
        throw new Error(`Gmail profile request failed: ${response.statusCode}`);
      }
    } catch (error) {
      throw new Error(`Gmail API test failed: ${error.message}`);
    }
  }

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

  async runTest(authCode) {
    console.log('🚀 Quick Google API Test');
    console.log('='.repeat(50));

    try {
      await this.exchangeCodeForTokens(authCode);
      await this.testUserInfo();
      await this.testPeopleAPI();
      await this.testGmailAPI();
      
      console.log('\n🎉 SUCCESS: All Google APIs are working!');
      console.log('✅ Your OAuth setup is fully functional');
      
    } catch (error) {
      console.error(`\n❌ Test failed: ${error.message}`);
    }
  }
}

// Usage: node test-with-auth-code.js "your-auth-code-here"
if (require.main === module) {
  const authCode = process.argv[2];
  if (!authCode) {
    console.log('Usage: node test-with-auth-code.js "your-auth-code"');
    console.log('Use the authorization code from the OAuth callback URL');
    process.exit(1);
  }
  
  const tester = new QuickGoogleTest();
  tester.runTest(authCode).catch(console.error);
}

module.exports = QuickGoogleTest;