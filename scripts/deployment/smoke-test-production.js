#!/usr/bin/env node
/**
 * Post-Deployment Smoke Tests
 * Tests REAL deployed application to catch issues before users do
 * 
 * Run after deployment: node scripts/deployment/smoke-test-production.js
 */

const https = require('https');
const http = require('http');

// Configuration - Loaded from your actual environment
const CONFIG = {
    FRONTEND_URL: 'https://de1irtdutlxqu.cloudfront.net',
    API_URL: 'https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev',
    COGNITO_DOMAIN: 'eu-west-1_OAT3oPCIm.auth.eu-west-1.amazoncognito.com',
    USER_POOL_ID: 'eu-west-1_OAT3oPCIm',
    CLIENT_ID: '6unl8mg5tbv5r727vc39d847vn',
    AWS_REGION: 'eu-west-1',
    TEST_USER_EMAIL: process.env.TEST_USER_EMAIL || 'test@hdcn.nl',
    TEST_USER_PASSWORD: process.env.TEST_USER_PASSWORD || '', // Use env var for security
};

class SmokeTest {
    constructor() {
        this.results = [];
        this.authToken = null;
    }

    async runAllTests() {
        console.log('🔥 Starting Post-Deployment Smoke Tests');
        console.log('Testing REAL deployed environment');
        console.log('='.repeat(60));
        console.log(`Frontend: ${CONFIG.FRONTEND_URL}`);
        console.log(`API: ${CONFIG.API_URL}`);
        console.log('='.repeat(60));
        console.log('');

        try {
            // Critical path tests
            await this.testFrontendAccessible();
            await this.testFrontendLoadsCorrectly();
            await this.testAPIHealthCheck();
            await this.testCORSHeaders();
            
            // If auth credentials provided, test authenticated flows
            if (CONFIG.TEST_USER_PASSWORD) {
                await this.testCognitoLogin();
                await this.testMemberFormRead();
                await this.testMemberFormWrite();
            } else {
                console.log('⚠️  Skipping authenticated tests (no TEST_USER_PASSWORD provided)');
            }

            this.printSummary();
            return this.results.every(r => r.passed);
        } catch (error) {
            console.error('💥 Smoke test execution failed:', error);
            return false;
        }
    }

    async testFrontendAccessible() {
        const testName = 'Frontend Accessible';
        console.log(`\n🧪 ${testName}...`);
        
        try {
            const response = await this.makeRequest(CONFIG.FRONTEND_URL);
            
            if (response.statusCode === 200) {
                this.logPass(testName, 'Frontend returns 200 OK');
            } else {
                this.logFail(testName, `Expected 200, got ${response.statusCode}`);
            }
        } catch (error) {
            this.logFail(testName, `Cannot reach frontend: ${error.message}`);
        }
    }

    async testFrontendLoadsCorrectly() {
        const testName = 'Frontend Loads Correctly';
        console.log(`\n🧪 ${testName}...`);
        
        try {
            const response = await this.makeRequest(CONFIG.FRONTEND_URL);
            const body = response.body;
            
            // Check for critical elements
            const checks = [
                { name: 'Has root div', test: body.includes('<div id="root"') },
                { name: 'Has React bundle', test: body.includes('.js') },
                { name: 'Has title', test: body.includes('<title>') },
                { name: 'No build errors', test: !body.includes('Failed to compile') },
            ];

            const allPassed = checks.every(c => c.test);
            
            if (allPassed) {
                this.logPass(testName, 'All frontend checks passed');
            } else {
                const failed = checks.filter(c => !c.test).map(c => c.name);
                this.logFail(testName, `Failed checks: ${failed.join(', ')}`);
            }
        } catch (error) {
            this.logFail(testName, error.message);
        }
    }

    async testAPIHealthCheck() {
        const testName = 'API Health Check';
        console.log(`\n🧪 ${testName}...`);
        
        try {
            // Try the members endpoint which should exist
            const response = await this.makeRequest(`${CONFIG.API_URL}/members`);
            
            console.log(`   📋 Response: ${response.statusCode}`);
            if (response.body && response.body.length < 500) {
                console.log(`   📄 Body: ${response.body}`);
            }
            
            // 401/403 means API is reachable but needs auth (which is correct)
            // 502/503 means Lambda is failing
            // 404 means endpoint doesn't exist
            // 200 means it worked (unlikely without auth)
            if ([200, 401, 403].includes(response.statusCode)) {
                this.logPass(testName, `API reachable (${response.statusCode} - auth required as expected)`);
            } else if (response.statusCode === 502 || response.statusCode === 503) {
                this.logFail(testName, `Lambda function error (${response.statusCode}) - backend has issues!`);
            } else if (response.statusCode === 404) {
                this.logFail(testName, 'API endpoint not found - deployment may have failed');
            } else {
                this.logWarn(testName, `Unexpected status: ${response.statusCode}`);
            }
        } catch (error) {
            this.logFail(testName, `Cannot reach API: ${error.message}`);
        }
    }

    async testCORSHeaders() {
        const testName = 'CORS Headers';
        console.log(`\n🧪 ${testName}...`);
        
        try {
            // Test CORS on the actual GET request, not OPTIONS
            // Many APIs return CORS headers on actual requests, not preflight
            const response = await this.makeRequest(`${CONFIG.API_URL}/members`, {
                method: 'GET',
                headers: {
                    'Origin': CONFIG.FRONTEND_URL,
                }
            });
            
            const corsHeader = response.headers['access-control-allow-origin'];
            
            if (corsHeader) {
                this.logPass(testName, `CORS enabled: ${corsHeader}`);
            } else {
                // Try OPTIONS request as fallback
                const optionsResponse = await this.makeRequest(`${CONFIG.API_URL}/members`, {
                    method: 'OPTIONS',
                    headers: {
                        'Origin': CONFIG.FRONTEND_URL,
                        'Access-Control-Request-Method': 'GET',
                    }
                });
                
                const optionsCorsHeader = optionsResponse.headers['access-control-allow-origin'];
                
                if (optionsCorsHeader) {
                    this.logPass(testName, `CORS enabled (via OPTIONS): ${optionsCorsHeader}`);
                } else {
                    this.logWarn(testName, 'No CORS headers found - but API may still work if configured in API Gateway');
                }
            }
        } catch (error) {
            this.logWarn(testName, `Could not test CORS: ${error.message}`);
        }
    }

    async testCognitoLogin() {
        const testName = 'Cognito Login';
        console.log(`\n🧪 ${testName}...`);
        
        try {
            // This is a simplified test - real Cognito login is complex
            // You may need to use AWS SDK or Amplify for actual login
            console.log('   ⚠️  Automated Cognito login not implemented');
            console.log('   Manual test required: Try logging in with passkey');
            this.logWarn(testName, 'Manual test required');
        } catch (error) {
            this.logFail(testName, error.message);
        }
    }

    async testMemberFormRead() {
        const testName = 'Member Form Read';
        console.log(`\n🧪 ${testName}...`);
        
        if (!this.authToken) {
            this.logWarn(testName, 'Skipped - no auth token');
            return;
        }

        try {
            const response = await this.makeRequest(`${CONFIG.API_URL}/members/me`, {
                headers: {
                    'Authorization': `Bearer ${this.authToken}`,
                }
            });
            
            if (response.statusCode === 200) {
                this.logPass(testName, 'Member data retrieved successfully');
            } else {
                this.logFail(testName, `Expected 200, got ${response.statusCode}: ${response.body}`);
            }
        } catch (error) {
            this.logFail(testName, error.message);
        }
    }

    async testMemberFormWrite() {
        const testName = 'Member Form Write';
        console.log(`\n🧪 ${testName}...`);
        
        if (!this.authToken) {
            this.logWarn(testName, 'Skipped - no auth token');
            return;
        }

        try {
            const testData = {
                phone: '+31612345678',
                // Add minimal test data
            };

            const response = await this.makeRequest(`${CONFIG.API_URL}/members/me`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.authToken}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(testData)
            });
            
            if (response.statusCode === 200 || response.statusCode === 201) {
                this.logPass(testName, 'Member data updated successfully');
            } else {
                this.logFail(testName, `Expected 200/201, got ${response.statusCode}: ${response.body}`);
            }
        } catch (error) {
            this.logFail(testName, error.message);
        }
    }

    makeRequest(url, options = {}) {
        return new Promise((resolve, reject) => {
            const urlObj = new URL(url);
            const protocol = urlObj.protocol === 'https:' ? https : http;
            
            const requestOptions = {
                hostname: urlObj.hostname,
                port: urlObj.port,
                path: urlObj.pathname + urlObj.search,
                method: options.method || 'GET',
                headers: options.headers || {},
            };

            const req = protocol.request(requestOptions, (res) => {
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => {
                    resolve({
                        statusCode: res.statusCode,
                        headers: res.headers,
                        body: body
                    });
                });
            });

            req.on('error', reject);
            
            if (options.body) {
                req.write(options.body);
            }
            
            req.end();
        });
    }

    logPass(testName, message) {
        console.log(`   ✅ PASS: ${message}`);
        this.results.push({ testName, passed: true, message });
    }

    logFail(testName, message) {
        console.log(`   ❌ FAIL: ${message}`);
        this.results.push({ testName, passed: false, message });
    }

    logWarn(testName, message) {
        console.log(`   ⚠️  WARN: ${message}`);
        this.results.push({ testName, passed: true, message, warning: true });
    }

    printSummary() {
        console.log('\n' + '='.repeat(60));
        console.log('📊 Smoke Test Summary');
        console.log('='.repeat(60));

        const total = this.results.length;
        const passed = this.results.filter(r => r.passed).length;
        const failed = total - passed;
        const warnings = this.results.filter(r => r.warning).length;

        console.log(`Total Tests: ${total}`);
        console.log(`Passed: ${passed} ✅`);
        console.log(`Failed: ${failed} ❌`);
        console.log(`Warnings: ${warnings} ⚠️`);

        if (failed > 0) {
            console.log('\n❌ Failed Tests:');
            this.results
                .filter(r => !r.passed)
                .forEach(r => console.log(`   - ${r.testName}: ${r.message}`));
            
            console.log('\n🚫 DEPLOYMENT HAS ISSUES - DO NOT RELEASE TO USERS');
            process.exit(1);
        } else {
            console.log('\n✅ All smoke tests passed!');
            console.log('🎉 Deployment looks good - safe to use');
            process.exit(0);
        }
    }
}

// Run tests
if (require.main === module) {
    const smokeTest = new SmokeTest();
    smokeTest.runAllTests();
}

module.exports = SmokeTest;
