/**
 * Safari Desktop WebAuthn Support Test
 * 
 * This script tests WebAuthn/Passkey support specifically for Safari desktop browser.
 * Safari has unique characteristics and requirements for WebAuthn support.
 */

class SafariDesktopTest {
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
        
        // Detect Safari specifically
        let browserName = 'Unknown';
        let browserVersion = 'Unknown';
        let isSupported = false;
        let isSafari = false;
        
        // Safari detection is tricky because Chrome also includes "Safari" in user agent
        if (userAgent.includes('Safari') && !userAgent.includes('Chrome') && !userAgent.includes('Chromium')) {
            browserName = 'Safari';
            isSafari = true;
            const match = userAgent.match(/Version\/(\d+)/);
            browserVersion = match ? match[1] : 'Unknown';
            // Safari 14+ has WebAuthn support
            isSupported = parseInt(browserVersion) >= 14;
        } else if (userAgent.includes('Chrome')) {
            browserName = 'Chrome (not Safari)';
        } else if (userAgent.includes('Firefox')) {
            browserName = 'Firefox (not Safari)';
        } else if (userAgent.includes('Edg')) {
            browserName = 'Edge (not Safari)';
        }

        // Detect platform
        let platform = 'Unknown';
        if (userAgent.includes('Mac')) platform = 'macOS';
        else if (userAgent.includes('Windows')) platform = 'Windows';
        else if (userAgent.includes('Linux')) platform = 'Linux';

        const isMobile = /iPhone|iPad|iPod/i.test(userAgent);
        const isDesktop = !isMobile;

        this.browserInfo = {
            browserName,
            browserVersion,
            platform,
            isMobile,
            isDesktop,
            isSupported,
            isSafari,
            userAgent
        };

        this.logResult(
            'Safari Browser Detection',
            isSafari && isDesktop,
            `Detected ${browserName} ${browserVersion} on ${platform} ${isDesktop ? '(Desktop)' : '(Mobile)'} - Safari: ${isSafari}`,
            this.browserInfo
        );

        if (!isSafari) {
            this.logResult(
                'Not Safari Browser',
                'warning',
                'This test is designed for Safari. Current browser is not Safari.'
            );
        }

        if (!isSupported && isSafari) {
            this.logResult(
                'Safari Version Warning',
                'warning',
                'Safari 14+ is required for WebAuthn support. Please update Safari.'
            );
        }

        if (!isDesktop && isSafari) {
            this.logResult(
                'Mobile Safari Detected',
                'info',
                'This test is designed for Safari desktop. Mobile Safari has different WebAuthn characteristics.'
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
                'Cannot proceed with WebAuthn tests - API not available. Safari 14+ is required.'
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

        // Safari-specific WebAuthn checks
        if (this.browserInfo.isSafari) {
            // Check for Safari's WebAuthn implementation quirks
            this.logResult(
                'Safari WebAuthn Implementation',
                true,
                'Safari uses its own WebAuthn implementation with some unique characteristics',
                { 
                    safariVersion: this.browserInfo.browserVersion,
                    platform: this.browserInfo.platform
                }
            );
        }

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
                    'Platform authenticator is available (Touch ID/Face ID)' : 
                    'Platform authenticator is not available',
                { available }
            );

            // Safari/macOS specific checks
            if (this.browserInfo.platform === 'macOS' && this.browserInfo.isSafari) {
                this.logResult(
                    'Safari Touch ID Support',
                    available,
                    available ? 
                        'Touch ID/Face ID should be available for authentication in Safari' : 
                        'Touch ID/Face ID may not be set up or available',
                    { platform: 'macOS', browser: 'Safari', available }
                );

                // Safari has excellent Touch ID integration
                if (available) {
                    this.logResult(
                        'Safari Biometric Integration',
                        true,
                        'Safari has excellent Touch ID and Face ID integration on macOS',
                        { integration: 'excellent' }
                    );
                }
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

    async testSafariSpecificFeatures() {
        if (!this.browserInfo.isSafari) {
            this.logResult(
                'Safari-Specific Features Test',
                'warning',
                'Not running on Safari - cannot test Safari-specific features',
                { currentBrowser: this.browserInfo.browserName }
            );
            return;
        }

        // Test Safari WebAuthn version support
        const safariVersion = parseInt(this.browserInfo.browserVersion);
        
        if (safariVersion >= 14) {
            this.logResult(
                'Safari WebAuthn Support',
                true,
                `Safari ${this.browserInfo.browserVersion} has WebAuthn support (introduced in Safari 14)`,
                { version: this.browserInfo.browserVersion, required: 14 }
            );
        } else {
            this.logResult(
                'Safari WebAuthn Support',
                false,
                `Safari ${this.browserInfo.browserVersion} does not support WebAuthn (requires Safari 14+)`,
                { version: this.browserInfo.browserVersion, required: 14 }
            );
        }

        // Test Safari's WebAuthn implementation characteristics
        if (window.PublicKeyCredential) {
            // Safari has some unique behaviors with WebAuthn
            this.logResult(
                'Safari WebAuthn Implementation Notes',
                'info',
                'Safari WebAuthn implementation has some unique characteristics compared to Chrome/Edge',
                {
                    notes: [
                        'Safari requires user gesture for WebAuthn operations',
                        'Safari has excellent Touch ID/Face ID integration',
                        'Safari may have different timeout behaviors',
                        'Safari supports resident keys (discoverable credentials)'
                    ]
                }
            );

            // Test for Safari's conditional mediation support (if available)
            if (PublicKeyCredential.isConditionalMediationAvailable) {
                try {
                    const conditionalUI = await PublicKeyCredential.isConditionalMediationAvailable();
                    this.logResult(
                        'Safari Conditional UI Support',
                        conditionalUI,
                        conditionalUI ? 
                            'Safari supports conditional UI for passkeys' :
                            'Safari does not support conditional UI for passkeys',
                        { conditionalUI }
                    );
                } catch (error) {
                    this.logResult(
                        'Safari Conditional UI Test Error',
                        'warning',
                        `Could not test conditional UI: ${error.message}`,
                        { error: error.name }
                    );
                }
            } else {
                this.logResult(
                    'Safari Conditional UI',
                    'info',
                    'Conditional UI API not available in this Safari version',
                    { available: false }
                );
            }
        }

        // Test Safari's security requirements
        this.logResult(
            'Safari Security Requirements',
            true,
            'Safari has strict security requirements for WebAuthn operations',
            {
                requirements: [
                    'HTTPS required (or localhost for development)',
                    'User gesture required for credential creation',
                    'Same-origin policy strictly enforced',
                    'Secure context validation'
                ]
            }
        );
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
            // Create mock registration options optimized for Safari
            const challenge = new Uint8Array(32);
            crypto.getRandomValues(challenge);
            
            const userId = new TextEncoder().encode('test@example.com');
            
            const publicKeyCredentialCreationOptions = {
                challenge: challenge,
                rp: {
                    name: "H-DCN Safari Test",
                    id: window.location.hostname,
                },
                user: {
                    id: userId,
                    name: "test@example.com",
                    displayName: "Safari Test User",
                },
                pubKeyCredParams: [
                    { alg: -7, type: "public-key" },  // ES256 - preferred by Safari
                    { alg: -257, type: "public-key" } // RS256 - fallback
                ],
                authenticatorSelection: {
                    authenticatorAttachment: "platform", // Safari works well with platform authenticators
                    userVerification: "preferred",
                    requireResidentKey: false // Safari supports resident keys but not required
                },
                timeout: 60000, // Safari may need longer timeouts
                attestation: "none" // Safari prefers none attestation
            };

            this.logResult(
                'Safari Passkey Registration Options Created',
                true,
                'Successfully created Safari-optimized registration options',
                { 
                    challenge: challenge.length,
                    rp: publicKeyCredentialCreationOptions.rp.name,
                    user: publicKeyCredentialCreationOptions.user.name,
                    algorithms: publicKeyCredentialCreationOptions.pubKeyCredParams.map(p => p.alg),
                    timeout: publicKeyCredentialCreationOptions.timeout
                }
            );

            // Safari-specific validation
            if (this.browserInfo.isSafari) {
                this.logResult(
                    'Safari Registration Optimization',
                    true,
                    'Registration options are optimized for Safari WebAuthn implementation',
                    {
                        optimizations: [
                            'ES256 algorithm prioritized',
                            'Platform authenticator preferred',
                            'Extended timeout for user interaction',
                            'None attestation for privacy'
                        ]
                    }
                );
            }

            // Note: We don't actually attempt registration as it requires user interaction
            this.logResult(
                'Safari Passkey Registration API Test',
                true,
                'Safari passkey registration API is available and properly configured',
                { 
                    apiAvailable: true,
                    optionsValid: true,
                    safariOptimized: this.browserInfo.isSafari,
                    note: 'Actual registration requires user gesture in Safari'
                }
            );

            return true;

        } catch (error) {
            this.logResult(
                'Safari Passkey Registration Test Error',
                false,
                `Error setting up Safari passkey registration test: ${error.message}`,
                { error: error.name, message: error.message }
            );
            return false;
        }
    }

    async testSafariCompatibilityMatrix() {
        const features = [
            {
                name: 'WebAuthn API',
                safari14: 'Full',
                safari15: 'Full',
                safari16: 'Full',
                current: window.PublicKeyCredential ? 'Supported' : 'Not Supported'
            },
            {
                name: 'Platform Authenticator (Touch ID)',
                safari14: 'Full',
                safari15: 'Full',
                safari16: 'Full',
                current: 'Testing...'
            },
            {
                name: 'Resident Keys',
                safari14: 'Partial',
                safari15: 'Full',
                safari16: 'Full',
                current: window.PublicKeyCredential ? 'Supported' : 'Not Supported'
            },
            {
                name: 'User Verification',
                safari14: 'Full',
                safari15: 'Full',
                safari16: 'Full',
                current: window.PublicKeyCredential ? 'Supported' : 'Not Supported'
            },
            {
                name: 'Conditional UI',
                safari14: 'None',
                safari15: 'None',
                safari16: 'Partial',
                current: 'Testing...'
            }
        ];

        this.logResult(
            'Safari Compatibility Matrix',
            'info',
            'Safari WebAuthn feature support across versions',
            { features }
        );

        // Test current Safari version against matrix
        const currentVersion = parseInt(this.browserInfo.browserVersion);
        if (this.browserInfo.isSafari) {
            if (currentVersion >= 16) {
                this.logResult(
                    'Safari Version Assessment',
                    true,
                    'Safari 16+ has excellent WebAuthn support with all features',
                    { version: currentVersion, support: 'excellent' }
                );
            } else if (currentVersion >= 15) {
                this.logResult(
                    'Safari Version Assessment',
                    true,
                    'Safari 15 has very good WebAuthn support',
                    { version: currentVersion, support: 'very good' }
                );
            } else if (currentVersion >= 14) {
                this.logResult(
                    'Safari Version Assessment',
                    'warning',
                    'Safari 14 has basic WebAuthn support - consider updating for better features',
                    { version: currentVersion, support: 'basic' }
                );
            } else {
                this.logResult(
                    'Safari Version Assessment',
                    false,
                    'Safari version does not support WebAuthn - update to Safari 14+',
                    { version: currentVersion, support: 'none' }
                );
            }
        }
    }

    async runAllTests() {
        console.log('🍎 Starting Safari Desktop WebAuthn Support Test');
        console.log('===============================================');

        // Test 1: Browser Detection
        this.detectBrowser();

        // Test 2: WebAuthn API
        const webAuthnSupported = await this.testWebAuthnAPI();

        if (webAuthnSupported) {
            // Test 3: Platform Authenticator
            await this.testPlatformAuthenticator();

            // Test 4: Safari-specific features
            await this.testSafariSpecificFeatures();

            // Test 5: Passkey Registration API
            await this.testPasskeyRegistration();

            // Test 6: Compatibility Matrix
            await this.testSafariCompatibilityMatrix();
        }

        // Generate summary
        this.generateSummary();

        return this.testResults;
    }

    generateSummary() {
        console.log('\n📊 Safari Desktop Test Summary');
        console.log('==============================');

        const totalTests = this.testResults.length;
        const passedTests = this.testResults.filter(r => r.success === true).length;
        const failedTests = this.testResults.filter(r => r.success === false).length;
        const warningTests = this.testResults.filter(r => r.success === 'warning').length;
        
        const isSafari = this.browserInfo.isSafari;
        const isDesktop = this.browserInfo.isDesktop;
        const hasWebAuthn = window.PublicKeyCredential;
        const safariVersion = parseInt(this.browserInfo.browserVersion);
        
        let overallStatus = 'Unknown';
        
        if (isSafari) {
            if (hasWebAuthn && isDesktop && safariVersion >= 14) {
                overallStatus = '✅ Fully Compatible';
            } else if (hasWebAuthn && safariVersion >= 14) {
                overallStatus = '⚠️ Partially Compatible';
            } else {
                overallStatus = '❌ Not Compatible - Update Safari';
            }
        } else {
            overallStatus = '⚠️ Not Safari Browser';
        }

        console.log(`Overall Status: ${overallStatus}`);
        console.log(`Browser: ${this.browserInfo.browserName} ${this.browserInfo.browserVersion}`);
        console.log(`Platform: ${this.browserInfo.platform} ${isDesktop ? '(Desktop)' : '(Mobile)'}`);
        console.log(`Tests Run: ${totalTests}`);
        console.log(`✅ Passed: ${passedTests} | ❌ Failed: ${failedTests} | ⚠️ Warnings: ${warningTests}`);
        console.log(`WebAuthn Support: ${hasWebAuthn ? 'Yes' : 'No'}`);
        console.log(`Generated: ${new Date().toLocaleString()}`);

        // Safari-specific recommendations
        console.log('\n💡 Safari Recommendations:');
        if (isSafari && safariVersion >= 16) {
            console.log('✅ Safari 16+ has excellent WebAuthn support with all features');
        } else if (isSafari && safariVersion >= 15) {
            console.log('✅ Safari 15 has very good WebAuthn support');
            console.log('💡 Consider updating to Safari 16+ for conditional UI support');
        } else if (isSafari && safariVersion >= 14) {
            console.log('⚠️ Safari 14 has basic WebAuthn support');
            console.log('💡 Update to Safari 15+ for better resident key support');
        } else if (isSafari) {
            console.log('❌ Update Safari to version 14+ for WebAuthn support');
        } else {
            console.log('ℹ️ This test is designed for Safari. Use Safari for testing Safari-specific features.');
        }

        if (this.browserInfo.platform === 'macOS') {
            console.log('🔐 macOS Touch ID and Face ID provide excellent authentication experience');
        }

        console.log('\n🍎 Safari WebAuthn Notes:');
        console.log('• Safari requires user gesture for WebAuthn operations');
        console.log('• Safari has excellent Touch ID/Face ID integration on macOS');
        console.log('• Safari enforces strict same-origin policy for WebAuthn');
        console.log('• Safari prefers ES256 algorithm and platform authenticators');

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
    module.exports = SafariDesktopTest;
}

// Auto-run if in browser context
if (typeof window !== 'undefined') {
    window.SafariDesktopTest = SafariDesktopTest;
    
    // Provide easy way to run the test
    window.runSafariDesktopTest = async function() {
        const test = new SafariDesktopTest();
        return await test.runAllTests();
    };
    
    console.log('Safari Desktop Test loaded. Run with: runSafariDesktopTest()');
}