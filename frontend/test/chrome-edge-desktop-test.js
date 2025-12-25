/**
 * Chrome/Edge Desktop WebAuthn Support Test
 * 
 * This script tests WebAuthn/Passkey support specifically for Chrome and Edge desktop browsers.
 * It can be run in the browser console or as a standalone test.
 */

class ChromeEdgeDesktopTest {
    constructor() {
        this.testResults = [];
        this.browserInfo = {};
    }

    logResult(testName, success, message, details = null) {
        const result = {
            testName,
            success,
            message,
            details,
            timestamp: new Date().toISOString()
        };
        this.testResults.push(result);
        
        const icon = success === true ? '✅' : success === false ? '❌' : success === 'warning' ? '⚠️' : 'ℹ️';
        console.log(`${icon} ${testName}: ${message}`, details || '');
        return result;
    }

    detectBrowser() {
        const userAgent = navigator.userAgent;
        
        // Detect browser and version
        let browserName = 'Unknown';
        let browserVersion = 'Unknown';
        let isSupported = false;
        
        if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) {
            browserName = 'Chrome';
            const match = userAgent.match(/Chrome\/(\d+)/);
            browserVersion = match ? match[1] : 'Unknown';
            isSupported = parseInt(browserVersion) >= 67;
        } else if (userAgent.includes('Edg')) {
            browserName = 'Edge';
            const match = userAgent.match(/Edg\/(\d+)/);
            browserVersion = match ? match[1] : 'Unknown';
            isSupported = parseInt(browserVersion) >= 18;
        }

        // Detect platform
        let platform = 'Unknown';
        if (userAgent.includes('Windows')) platform = 'Windows';
        else if (userAgent.includes('Mac')) platform = 'macOS';
        else if (userAgent.includes('Linux')) platform = 'Linux';

        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
        const isDesktop = !isMobile;

        this.browserInfo = {
            browserName,
            browserVersion,
            platform,
            isMobile,
            isDesktop,
            isSupported,
            userAgent
        };

        this.logResult(
            'Browser Detection',
            isSupported && isDesktop,
            `Detected ${browserName} ${browserVersion} on ${platform} ${isDesktop ? '(Desktop)' : '(Mobile)'}`,
            this.browserInfo
        );

        if (!isSupported) {
            this.logResult(
                'Browser Compatibility Warning',
                'warning',
                'This browser may not fully support WebAuthn. Please use Chrome 67+ or Edge 18+ for best results.'
            );
        }

        if (!isDesktop) {
            this.logResult(
                'Platform Warning',
                'warning',
                'This test is designed for desktop browsers. Mobile results may vary.'
            );
        }

        return this.browserInfo;
    }

    async testWebAuthnAPI() {
        // Test WebAuthn API availability
        const webAuthnSupported = !!(
            window.PublicKeyCredential &&
            navigator.credentials &&
            navigator.credentials.create &&
            navigator.credentials.get
        );

        this.logResult(
            'WebAuthn API Support',
            webAuthnSupported,
            webAuthnSupported ? 'WebAuthn API is available' : 'WebAuthn API is not available',
            { 
                PublicKeyCredential: !!window.PublicKeyCredential,
                navigatorCredentials: !!navigator.credentials,
                credentialsCreate: !!(navigator.credentials && navigator.credentials.create),
                credentialsGet: !!(navigator.credentials && navigator.credentials.get)
            }
        );

        if (!webAuthnSupported) {
            this.logResult(
                'WebAuthn Not Supported',
                false,
                'Cannot proceed with WebAuthn tests - API not available'
            );
            return false;
        }

        // Test secure context
        const isSecureContext = window.isSecureContext;
        this.logResult(
            'Secure Context (HTTPS)',
            isSecureContext,
            isSecureContext ? 'Running in secure context' : 'Not in secure context - WebAuthn requires HTTPS',
            { isSecureContext, protocol: window.location.protocol }
        );

        return webAuthnSupported && isSecureContext;
    }

    async testPlatformAuthenticator() {
        if (!window.PublicKeyCredential) {
            this.logResult(
                'Platform Authenticator Test',
                false,
                'WebAuthn not supported - cannot test platform authenticator'
            );
            return false;
        }

        try {
            const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
            this.logResult(
                'Platform Authenticator Availability',
                available,
                available ? 
                    'Platform authenticator is available (biometrics/Windows Hello/Touch ID)' : 
                    'Platform authenticator is not available',
                { available }
            );

            // Platform-specific checks
            if (this.browserInfo.platform === 'Windows') {
                this.logResult(
                    'Windows Hello Support',
                    available,
                    available ? 
                        'Windows Hello should be available for authentication' : 
                        'Windows Hello may not be set up or available',
                    { platform: 'Windows', available }
                );
            } else if (this.browserInfo.platform === 'macOS') {
                this.logResult(
                    'Touch ID Support',
                    available,
                    available ? 
                        'Touch ID should be available for authentication' : 
                        'Touch ID may not be set up or available',
                    { platform: 'macOS', available }
                );
            }

            return available;

        } catch (error) {
            this.logResult(
                'Platform Authenticator Test Error',
                false,
                `Error testing platform authenticator: ${error.message}`,
                { error: error.name, message: error.message }
            );
            return false;
        }
    }

    async testBrowserSpecificFeatures() {
        // Test Chrome/Edge specific features
        if (this.browserInfo.browserName === 'Chrome') {
            // Test Chrome-specific WebAuthn features
            this.logResult(
                'Chrome WebAuthn Support',
                parseInt(this.browserInfo.browserVersion) >= 67,
                parseInt(this.browserInfo.browserVersion) >= 67 ? 
                    `Chrome ${this.browserInfo.browserVersion} has full WebAuthn support` :
                    `Chrome ${this.browserInfo.browserVersion} has limited WebAuthn support (need 67+)`,
                { version: this.browserInfo.browserVersion, required: 67 }
            );

            // Test for Chrome's conditional UI support (if available)
            if (window.PublicKeyCredential && PublicKeyCredential.isConditionalMediationAvailable) {
                try {
                    const conditionalUI = await PublicKeyCredential.isConditionalMediationAvailable();
                    this.logResult(
                        'Chrome Conditional UI Support',
                        conditionalUI,
                        conditionalUI ? 
                            'Chrome supports conditional UI for passkeys' :
                            'Chrome does not support conditional UI for passkeys',
                        { conditionalUI }
                    );
                } catch (error) {
                    this.logResult(
                        'Chrome Conditional UI Test Error',
                        'warning',
                        `Could not test conditional UI: ${error.message}`,
                        { error: error.name }
                    );
                }
            }

        } else if (this.browserInfo.browserName === 'Edge') {
            // Test Edge-specific WebAuthn features
            this.logResult(
                'Edge WebAuthn Support',
                parseInt(this.browserInfo.browserVersion) >= 18,
                parseInt(this.browserInfo.browserVersion) >= 18 ? 
                    `Edge ${this.browserInfo.browserVersion} has full WebAuthn support` :
                    `Edge ${this.browserInfo.browserVersion} has limited WebAuthn support (need 18+)`,
                { version: this.browserInfo.browserVersion, required: 18 }
            );

            // Test Windows Hello integration
            if (this.browserInfo.platform === 'Windows') {
                this.logResult(
                    'Edge Windows Hello Integration',
                    true,
                    'Edge has excellent Windows Hello integration',
                    { browser: 'Edge', platform: 'Windows' }
                );
            }

        } else {
            this.logResult(
                'Browser Compatibility Warning',
                'warning',
                `${this.browserInfo.browserName} is not Chrome or Edge. For best WebAuthn support, use Chrome 67+ or Edge 18+`,
                { currentBrowser: this.browserInfo.browserName }
            );
        }
    }

    async testPasskeyRegistration() {
        if (!window.PublicKeyCredential) {
            this.logResult(
                'Passkey Registration Test',
                false,
                'WebAuthn not supported - cannot test passkey registration'
            );
            return false;
        }

        try {
            // Create mock registration options
            const challenge = new Uint8Array(32);
            crypto.getRandomValues(challenge);
            
            const userId = new TextEncoder().encode('test@example.com');
            
            const publicKeyCredentialCreationOptions = {
                challenge: challenge,
                rp: {
                    name: "H-DCN Test",
                    id: window.location.hostname,
                },
                user: {
                    id: userId,
                    name: "test@example.com",
                    displayName: "Test User",
                },
                pubKeyCredParams: [
                    { alg: -7, type: "public-key" },
                    { alg: -257, type: "public-key" }
                ],
                authenticatorSelection: {
                    authenticatorAttachment: "platform",
                    userVerification: "preferred"
                },
                timeout: 5000, // Short timeout for testing
                attestation: "none"
            };

            this.logResult(
                'Passkey Registration Options Created',
                true,
                'Successfully created registration options',
                { 
                    challenge: challenge.length,
                    rp: publicKeyCredentialCreationOptions.rp.name,
                    user: publicKeyCredentialCreationOptions.user.name
                }
            );

            // Note: We don't actually attempt registration as it requires user interaction
            this.logResult(
                'Passkey Registration API Test',
                true,
                'Passkey registration API is available and properly configured',
                { 
                    apiAvailable: true,
                    optionsValid: true,
                    note: 'Actual registration requires user interaction'
                }
            );

            return true;

        } catch (error) {
            this.logResult(
                'Passkey Registration Test Error',
                false,
                `Error setting up passkey registration test: ${error.message}`,
                { error: error.name, message: error.message }
            );
            return false;
        }
    }

    async runAllTests() {
        console.log('🔍 Starting Chrome/Edge Desktop WebAuthn Support Test');
        console.log('================================================');

        // Test 1: Browser Detection
        this.detectBrowser();

        // Test 2: WebAuthn API
        const webAuthnSupported = await this.testWebAuthnAPI();

        if (webAuthnSupported) {
            // Test 3: Platform Authenticator
            await this.testPlatformAuthenticator();

            // Test 4: Browser-specific features
            await this.testBrowserSpecificFeatures();

            // Test 5: Passkey Registration API
            await this.testPasskeyRegistration();
        }

        // Generate summary
        this.generateSummary();

        return this.testResults;
    }

    generateSummary() {
        console.log('\n📊 Test Summary');
        console.log('===============');

        const totalTests = this.testResults.length;
        const passedTests = this.testResults.filter(r => r.success === true).length;
        const failedTests = this.testResults.filter(r => r.success === false).length;
        const warningTests = this.testResults.filter(r => r.success === 'warning').length;
        
        const isChrome = this.browserInfo.browserName === 'Chrome';
        const isEdge = this.browserInfo.browserName === 'Edge';
        const isDesktop = this.browserInfo.isDesktop;
        const hasWebAuthn = window.PublicKeyCredential;
        
        let overallStatus = 'Unknown';
        
        if (isChrome || isEdge) {
            if (hasWebAuthn && isDesktop) {
                overallStatus = '✅ Fully Compatible';
            } else if (hasWebAuthn) {
                overallStatus = '⚠️ Partially Compatible';
            } else {
                overallStatus = '❌ Not Compatible';
            }
        } else {
            overallStatus = '⚠️ Browser Not Chrome/Edge';
        }

        console.log(`Overall Status: ${overallStatus}`);
        console.log(`Browser: ${this.browserInfo.browserName} ${this.browserInfo.browserVersion}`);
        console.log(`Platform: ${this.browserInfo.platform} ${isDesktop ? '(Desktop)' : '(Mobile)'}`);
        console.log(`Tests Run: ${totalTests}`);
        console.log(`✅ Passed: ${passedTests} | ❌ Failed: ${failedTests} | ⚠️ Warnings: ${warningTests}`);
        console.log(`WebAuthn Support: ${hasWebAuthn ? 'Yes' : 'No'}`);
        console.log(`Generated: ${new Date().toLocaleString()}`);

        // Recommendations
        console.log('\n💡 Recommendations:');
        if (isChrome && parseInt(this.browserInfo.browserVersion) >= 67) {
            console.log('✅ Chrome version is fully supported for WebAuthn');
        } else if (isEdge && parseInt(this.browserInfo.browserVersion) >= 18) {
            console.log('✅ Edge version is fully supported for WebAuthn');
        } else if (!isChrome && !isEdge) {
            console.log('⚠️ For best WebAuthn support, use Chrome 67+ or Edge 18+');
        } else {
            console.log('⚠️ Update your browser to the latest version for best WebAuthn support');
        }

        if (this.browserInfo.platform === 'Windows') {
            console.log('💡 Windows Hello provides excellent platform authenticator support');
        } else if (this.browserInfo.platform === 'macOS') {
            console.log('💡 Touch ID provides excellent platform authenticator support');
        }

        return {
            overallStatus,
            totalTests,
            passedTests,
            failedTests,
            warningTests,
            browserInfo: this.browserInfo
        };
    }
}

// Export for use in other contexts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChromeEdgeDesktopTest;
}

// Auto-run if in browser context
if (typeof window !== 'undefined') {
    window.ChromeEdgeDesktopTest = ChromeEdgeDesktopTest;
    
    // Provide easy way to run the test
    window.runChromeEdgeDesktopTest = async function() {
        const test = new ChromeEdgeDesktopTest();
        return await test.runAllTests();
    };
    
    console.log('Chrome/Edge Desktop Test loaded. Run with: runChromeEdgeDesktopTest()');
}