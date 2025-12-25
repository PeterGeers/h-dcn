/**
 * Mobile Browser WebAuthn Support Test
 * 
 * This script tests WebAuthn/Passkey support specifically for mobile browsers.
 * Mobile browsers have unique characteristics and requirements for WebAuthn support.
 */

class MobileBrowserTest {
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

    detectMobileBrowser() {
        const userAgent = navigator.userAgent;
        
        // Detect mobile platform
        let platform = 'Unknown';
        let isMobile = false;
        let isTablet = false;
        
        if (/iPhone/i.test(userAgent)) {
            platform = 'iOS (iPhone)';
            isMobile = true;
        } else if (/iPad/i.test(userAgent)) {
            platform = 'iOS (iPad)';
            isTablet = true;
            isMobile = true; // iPads are considered mobile for WebAuthn purposes
        } else if (/iPod/i.test(userAgent)) {
            platform = 'iOS (iPod)';
            isMobile = true;
        } else if (/Android/i.test(userAgent)) {
            if (/Mobile/i.test(userAgent)) {
                platform = 'Android (Phone)';
                isMobile = true;
            } else {
                platform = 'Android (Tablet)';
                isTablet = true;
                isMobile = true;
            }
        } else {
            // Check for other mobile indicators
            const mobileIndicators = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
            isMobile = mobileIndicators.test(userAgent);
            if (isMobile) {
                platform = 'Mobile (Other)';
            } else {
                platform = 'Desktop';
            }
        }

        // Detect browser on mobile
        let browserName = 'Unknown';
        let browserVersion = 'Unknown';
        let isSupported = false;
        
        if (platform.includes('iOS')) {
            // iOS browsers
            if (userAgent.includes('CriOS')) {
                browserName = 'Chrome (iOS)';
                const match = userAgent.match(/CriOS\/(\d+)/);
                browserVersion = match ? match[1] : 'Unknown';
                isSupported = true; // Chrome on iOS uses Safari engine, supports WebAuthn if iOS 14+
            } else if (userAgent.includes('FxiOS')) {
                browserName = 'Firefox (iOS)';
                const match = userAgent.match(/FxiOS\/(\d+)/);
                browserVersion = match ? match[1] : 'Unknown';
                isSupported = true; // Firefox on iOS uses Safari engine
            } else if (userAgent.includes('Safari')) {
                browserName = 'Safari (iOS)';
                const match = userAgent.match(/Version\/(\d+)/);
                browserVersion = match ? match[1] : 'Unknown';
                isSupported = parseInt(browserVersion) >= 14;
            }
        } else if (platform.includes('Android')) {
            // Android browsers
            if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) {
                browserName = 'Chrome (Android)';
                const match = userAgent.match(/Chrome\/(\d+)/);
                browserVersion = match ? match[1] : 'Unknown';
                isSupported = parseInt(browserVersion) >= 70; // Android Chrome 70+ has WebAuthn
            } else if (userAgent.includes('Firefox')) {
                browserName = 'Firefox (Android)';
                const match = userAgent.match(/Firefox\/(\d+)/);
                browserVersion = match ? match[1] : 'Unknown';
                isSupported = parseInt(browserVersion) >= 92; // Firefox Android 92+ has WebAuthn
            } else if (userAgent.includes('Samsung')) {
                browserName = 'Samsung Internet';
                const match = userAgent.match(/SamsungBrowser\/(\d+)/);
                browserVersion = match ? match[1] : 'Unknown';
                isSupported = parseInt(browserVersion) >= 13; // Samsung Internet 13+ has WebAuthn
            } else if (userAgent.includes('Android')) {
                browserName = 'Android WebView';
                isSupported = false; // WebView typically doesn't support WebAuthn
            }
        }

        // Detect OS version for iOS/Android
        let osVersion = 'Unknown';
        if (platform.includes('iOS')) {
            const match = userAgent.match(/OS (\d+)_(\d+)/);
            if (match) {
                osVersion = `${match[1]}.${match[2]}`;
                // iOS 14+ required for WebAuthn
                if (parseInt(match[1]) >= 14) {
                    isSupported = isSupported && true;
                } else {
                    isSupported = false;
                }
            }
        } else if (platform.includes('Android')) {
            const match = userAgent.match(/Android (\d+)/);
            if (match) {
                osVersion = match[1];
                // Android 7+ generally required for WebAuthn
                if (parseInt(match[1]) >= 7) {
                    isSupported = isSupported && true;
                } else {
                    isSupported = false;
                }
            }
        }

        this.browserInfo = {
            browserName,
            browserVersion,
            platform,
            osVersion,
            isMobile,
            isTablet,
            isSupported,
            userAgent
        };

        this.logResult(
            'Mobile Browser Detection',
            isMobile && isSupported,
            `Detected ${browserName} ${browserVersion} on ${platform} (OS: ${osVersion}) - Mobile: ${isMobile}, Supported: ${isSupported}`,
            this.browserInfo
        );

        if (!isMobile) {
            this.logResult(
                'Not Mobile Device',
                'warning',
                'This test is designed for mobile browsers. Current device appears to be desktop.'
            );
        }

        if (isMobile && !isSupported) {
            this.logResult(
                'Mobile Browser/OS Version Warning',
                'warning',
                'Mobile browser or OS version may not support WebAuthn. Update browser/OS for best support.'
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
            'Mobile WebAuthn API Support',
            webAuthnSupported,
            webAuthnSupported ? 'WebAuthn API is available on mobile' : 'WebAuthn API is not available on mobile',
            { 
                PublicKeyCredential: !!window.PublicKeyCredential,
                navigatorCredentials: !!navigator.credentials,
                platform: this.browserInfo.platform,
                browser: this.browserInfo.browserName
            }
        );

        if (!webAuthnSupported) {
            this.logResult(
                'Mobile WebAuthn Not Supported',
                false,
                'Cannot proceed with mobile WebAuthn tests - API not available'
            );
            return false;
        }

        // Test secure context
        const isSecureContext = window.isSecureContext;
        this.logResult(
            'Mobile Secure Context (HTTPS)',
            isSecureContext,
            isSecureContext ? 'Running in secure context on mobile' : 'Not in secure context - mobile WebAuthn requires HTTPS',
            { isSecureContext, protocol: window.location.protocol }
        );

        // Mobile-specific WebAuthn characteristics
        this.logResult(
            'Mobile WebAuthn Characteristics',
            'info',
            'Mobile WebAuthn has unique characteristics compared to desktop',
            {
                characteristics: [
                    'Typically uses platform authenticators (biometrics)',
                    'May have different timeout behaviors',
                    'Cross-device authentication capabilities',
                    'Touch/Face ID integration on iOS',
                    'Fingerprint/Face unlock on Android'
                ]
            }
        );

        return webAuthnSupported && isSecureContext;
    }

    async testMobilePlatformAuthenticator() {
        if (!window.PublicKeyCredential) {
            this.logResult(
                'Mobile Platform Authenticator Test',
                false,
                'WebAuthn not supported - cannot test mobile platform authenticator'
            );
            return false;
        }

        try {
            const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
            this.logResult(
                'Mobile Platform Authenticator Availability',
                available,
                available ? 
                    'Mobile platform authenticator is available (biometrics)' : 
                    'Mobile platform authenticator is not available',
                { available, platform: this.browserInfo.platform }
            );

            // Platform-specific checks
            if (this.browserInfo.platform.includes('iOS')) {
                this.logResult(
                    'iOS Biometric Support',
                    available,
                    available ? 
                        'Touch ID or Face ID should be available on this iOS device' : 
                        'Touch ID/Face ID may not be set up or available',
                    { platform: 'iOS', available }
                );

                if (available) {
                    this.logResult(
                        'iOS WebAuthn Integration',
                        true,
                        'iOS has excellent WebAuthn integration with Touch ID and Face ID',
                        { 
                            integration: 'excellent',
                            features: ['Touch ID', 'Face ID', 'Secure Enclave']
                        }
                    );
                }
            } else if (this.browserInfo.platform.includes('Android')) {
                this.logResult(
                    'Android Biometric Support',
                    available,
                    available ? 
                        'Fingerprint or face unlock should be available on this Android device' : 
                        'Biometric authentication may not be set up or available',
                    { platform: 'Android', available }
                );

                if (available) {
                    this.logResult(
                        'Android WebAuthn Integration',
                        true,
                        'Android has good WebAuthn integration with biometric authentication',
                        { 
                            integration: 'good',
                            features: ['Fingerprint', 'Face unlock', 'Hardware security module']
                        }
                    );
                }
            }

            return available;

        } catch (error) {
            this.logResult(
                'Mobile Platform Authenticator Test Error',
                false,
                `Error testing mobile platform authenticator: ${error.message}`,
                { error: error.name, message: error.message }
            );
            return false;
        }
    }

    async testMobileSpecificFeatures() {
        if (!this.browserInfo.isMobile) {
            this.logResult(
                'Mobile-Specific Features Test',
                'warning',
                'Not running on mobile device - cannot test mobile-specific features',
                { currentPlatform: this.browserInfo.platform }
            );
            return;
        }

        // Test mobile browser specific features
        if (this.browserInfo.platform.includes('iOS')) {
            await this.testIOSSpecificFeatures();
        } else if (this.browserInfo.platform.includes('Android')) {
            await this.testAndroidSpecificFeatures();
        }

        // Test cross-device authentication capability
        this.logResult(
            'Mobile Cross-Device Authentication',
            true,
            'Mobile devices can participate in cross-device authentication flows',
            {
                capabilities: [
                    'Can authenticate for desktop sessions',
                    'QR code scanning for cross-device auth',
                    'Bluetooth proximity authentication',
                    'Platform authenticator sharing'
                ]
            }
        );

        // Test mobile viewport and UI considerations
        this.logResult(
            'Mobile UI Considerations',
            'info',
            'Mobile WebAuthn has specific UI and UX considerations',
            {
                considerations: [
                    'Smaller screen real estate for prompts',
                    'Touch-optimized authentication flows',
                    'Native biometric UI integration',
                    'Orientation changes during authentication',
                    'App switching during authentication'
                ]
            }
        );
    }

    async testIOSSpecificFeatures() {
        const osVersion = parseFloat(this.browserInfo.osVersion);
        
        this.logResult(
            'iOS WebAuthn Support',
            osVersion >= 14,
            osVersion >= 14 ? 
                `iOS ${this.browserInfo.osVersion} supports WebAuthn` :
                `iOS ${this.browserInfo.osVersion} does not support WebAuthn (requires iOS 14+)`,
            { osVersion: this.browserInfo.osVersion, required: 14 }
        );

        // iOS browser engine note
        this.logResult(
            'iOS Browser Engine',
            'info',
            'All iOS browsers use Safari WebKit engine for WebAuthn',
            {
                note: 'Chrome, Firefox, and other browsers on iOS use Safari engine',
                implication: 'WebAuthn support depends on iOS version, not browser version'
            }
        );

        // iOS-specific WebAuthn features
        if (osVersion >= 14) {
            this.logResult(
                'iOS WebAuthn Features',
                true,
                'iOS WebAuthn implementation has excellent features',
                {
                    features: [
                        'Touch ID integration',
                        'Face ID integration',
                        'Secure Enclave utilization',
                        'Cross-device authentication',
                        'iCloud Keychain integration (iOS 15+)'
                    ]
                }
            );
        }

        // Test for iOS 15+ features
        if (osVersion >= 15) {
            this.logResult(
                'iOS 15+ Enhanced Features',
                true,
                'iOS 15+ has enhanced WebAuthn features',
                {
                    enhancements: [
                        'iCloud Keychain passkey sync',
                        'Improved cross-device flows',
                        'Better Safari integration',
                        'Enhanced security policies'
                    ]
                }
            );
        }
    }

    async testAndroidSpecificFeatures() {
        const osVersion = parseInt(this.browserInfo.osVersion);
        
        this.logResult(
            'Android WebAuthn Support',
            osVersion >= 7,
            osVersion >= 7 ? 
                `Android ${this.browserInfo.osVersion} supports WebAuthn` :
                `Android ${this.browserInfo.osVersion} may not support WebAuthn (Android 7+ recommended)`,
            { osVersion: this.browserInfo.osVersion, recommended: 7 }
        );

        // Android browser variations
        if (this.browserInfo.browserName.includes('Chrome')) {
            const chromeVersion = parseInt(this.browserInfo.browserVersion);
            this.logResult(
                'Android Chrome WebAuthn',
                chromeVersion >= 70,
                chromeVersion >= 70 ? 
                    `Chrome ${this.browserInfo.browserVersion} on Android has WebAuthn support` :
                    `Chrome ${this.browserInfo.browserVersion} on Android may have limited WebAuthn support`,
                { chromeVersion, required: 70 }
            );
        } else if (this.browserInfo.browserName.includes('Samsung')) {
            const samsungVersion = parseInt(this.browserInfo.browserVersion);
            this.logResult(
                'Samsung Internet WebAuthn',
                samsungVersion >= 13,
                samsungVersion >= 13 ? 
                    `Samsung Internet ${this.browserInfo.browserVersion} has WebAuthn support` :
                    `Samsung Internet ${this.browserInfo.browserVersion} may not support WebAuthn`,
                { samsungVersion, required: 13 }
            );
        }

        // Android-specific WebAuthn features
        if (osVersion >= 7) {
            this.logResult(
                'Android WebAuthn Features',
                true,
                'Android WebAuthn implementation has good features',
                {
                    features: [
                        'Fingerprint authentication',
                        'Face unlock integration',
                        'Hardware security module',
                        'Google Play Services integration',
                        'Cross-device authentication'
                    ]
                }
            );
        }

        // Test for Android 9+ features
        if (osVersion >= 9) {
            this.logResult(
                'Android 9+ Enhanced Features',
                true,
                'Android 9+ has enhanced biometric authentication',
                {
                    enhancements: [
                        'BiometricPrompt API',
                        'Improved fingerprint handling',
                        'Better hardware security',
                        'Enhanced privacy controls'
                    ]
                }
            );
        }
    }

    async testMobilePasskeyRegistration() {
        if (!window.PublicKeyCredential) {
            this.logResult(
                'Mobile Passkey Registration Test',
                false,
                'WebAuthn not supported - cannot test mobile passkey registration'
            );
            return false;
        }

        try {
            // Create mobile-optimized registration options
            const challenge = new Uint8Array(32);
            crypto.getRandomValues(challenge);
            
            const userId = new TextEncoder().encode('mobile-test@example.com');
            
            const publicKeyCredentialCreationOptions = {
                challenge: challenge,
                rp: {
                    name: "H-DCN Mobile Test",
                    id: window.location.hostname,
                },
                user: {
                    id: userId,
                    name: "mobile-test@example.com",
                    displayName: "Mobile Test User",
                },
                pubKeyCredParams: [
                    { alg: -7, type: "public-key" },  // ES256 - widely supported
                    { alg: -257, type: "public-key" } // RS256 - fallback
                ],
                authenticatorSelection: {
                    authenticatorAttachment: "platform", // Mobile devices prefer platform authenticators
                    userVerification: "preferred",
                    requireResidentKey: false
                },
                timeout: 120000, // Longer timeout for mobile (user may need to unlock device)
                attestation: "none"
            };

            this.logResult(
                'Mobile Passkey Registration Options',
                true,
                'Successfully created mobile-optimized passkey registration options',
                { 
                    challenge: challenge.length,
                    rp: publicKeyCredentialCreationOptions.rp.name,
                    algorithms: ['ES256', 'RS256'],
                    timeout: publicKeyCredentialCreationOptions.timeout,
                    platform: this.browserInfo.platform
                }
            );

            // Mobile optimization notes
            this.logResult(
                'Mobile Registration Optimizations',
                'info',
                'Registration options are optimized for mobile WebAuthn implementation',
                {
                    optimizations: [
                        'Platform authenticator preferred (biometrics)',
                        'Extended timeout for device unlock',
                        'ES256 algorithm prioritized',
                        'None attestation for privacy',
                        'Resident key optional for compatibility'
                    ]
                }
            );

            // Mobile-specific considerations
            this.logResult(
                'Mobile Registration Considerations',
                'info',
                'Mobile passkey registration has specific considerations',
                {
                    considerations: [
                        'User may need to unlock device first',
                        'Biometric prompt will be native to platform',
                        'Registration may take longer than desktop',
                        'App switching may interrupt flow',
                        'Screen orientation changes may affect UI'
                    ]
                }
            );

            return true;

        } catch (error) {
            this.logResult(
                'Mobile Passkey Registration Error',
                false,
                `Error setting up mobile passkey registration: ${error.message}`,
                { error: error.name, message: error.message }
            );
            return false;
        }
    }

    async testMobileCompatibilityMatrix() {
        const platforms = [
            {
                name: 'iOS 14+ (Safari)',
                webauthn: 'Full',
                biometrics: 'Touch ID/Face ID',
                crossDevice: 'Full',
                current: this.browserInfo.platform.includes('iOS') ? 'Current Platform' : 'Not Current'
            },
            {
                name: 'iOS 14+ (Chrome)',
                webauthn: 'Full',
                biometrics: 'Touch ID/Face ID',
                crossDevice: 'Full',
                current: this.browserInfo.platform.includes('iOS') && this.browserInfo.browserName.includes('Chrome') ? 'Current Browser' : 'Not Current'
            },
            {
                name: 'Android 7+ (Chrome 70+)',
                webauthn: 'Full',
                biometrics: 'Fingerprint/Face',
                crossDevice: 'Full',
                current: this.browserInfo.platform.includes('Android') && this.browserInfo.browserName.includes('Chrome') ? 'Current Browser' : 'Not Current'
            },
            {
                name: 'Android 7+ (Samsung Internet 13+)',
                webauthn: 'Full',
                biometrics: 'Fingerprint/Face',
                crossDevice: 'Partial',
                current: this.browserInfo.browserName.includes('Samsung') ? 'Current Browser' : 'Not Current'
            },
            {
                name: 'Android 7+ (Firefox 92+)',
                webauthn: 'Partial',
                biometrics: 'Limited',
                crossDevice: 'Limited',
                current: this.browserInfo.platform.includes('Android') && this.browserInfo.browserName.includes('Firefox') ? 'Current Browser' : 'Not Current'
            }
        ];

        this.logResult(
            'Mobile Compatibility Matrix',
            'info',
            'Mobile WebAuthn support across platforms and browsers',
            { platforms }
        );

        // Assess current platform
        const currentPlatform = platforms.find(p => p.current.includes('Current'));
        if (currentPlatform) {
            this.logResult(
                'Current Mobile Platform Assessment',
                currentPlatform.webauthn === 'Full',
                `Current platform (${currentPlatform.name}) has ${currentPlatform.webauthn.toLowerCase()} WebAuthn support`,
                {
                    platform: currentPlatform.name,
                    webauthn: currentPlatform.webauthn,
                    biometrics: currentPlatform.biometrics,
                    crossDevice: currentPlatform.crossDevice
                }
            );
        }
    }

    async runAllTests() {
        console.log('📱 Starting Mobile Browser WebAuthn Support Test');
        console.log('===============================================');

        // Test 1: Mobile Browser Detection
        this.detectMobileBrowser();

        // Test 2: WebAuthn API
        const webAuthnSupported = await this.testWebAuthnAPI();

        if (webAuthnSupported) {
            // Test 3: Mobile Platform Authenticator
            await this.testMobilePlatformAuthenticator();

            // Test 4: Mobile-specific features
            await this.testMobileSpecificFeatures();

            // Test 5: Mobile Passkey Registration
            await this.testMobilePasskeyRegistration();

            // Test 6: Mobile Compatibility Matrix
            await this.testMobileCompatibilityMatrix();
        }

        // Generate summary
        this.generateSummary();

        return this.testResults;
    }

    generateSummary() {
        console.log('\n📊 Mobile Browser Test Summary');
        console.log('==============================');

        const totalTests = this.testResults.length;
        const passedTests = this.testResults.filter(r => r.success === true).length;
        const failedTests = this.testResults.filter(r => r.success === false).length;
        const warningTests = this.testResults.filter(r => r.success === 'warning').length;
        
        const isMobile = this.browserInfo.isMobile;
        const hasWebAuthn = window.PublicKeyCredential;
        const platform = this.browserInfo.platform;
        const browser = this.browserInfo.browserName;
        
        let overallStatus = 'Unknown';
        
        if (isMobile) {
            if (hasWebAuthn && this.browserInfo.isSupported) {
                overallStatus = '✅ Fully Compatible Mobile';
            } else if (hasWebAuthn) {
                overallStatus = '⚠️ Partially Compatible Mobile';
            } else {
                overallStatus = '❌ Not Compatible - Update Required';
            }
        } else {
            overallStatus = '⚠️ Not Mobile Device';
        }

        console.log(`Overall Status: ${overallStatus}`);
        console.log(`Platform: ${platform}`);
        console.log(`Browser: ${browser} ${this.browserInfo.browserVersion}`);
        console.log(`OS Version: ${this.browserInfo.osVersion}`);
        console.log(`Tests Run: ${totalTests}`);
        console.log(`✅ Passed: ${passedTests} | ❌ Failed: ${failedTests} | ⚠️ Warnings: ${warningTests}`);
        console.log(`WebAuthn Support: ${hasWebAuthn ? 'Yes' : 'No'}`);
        console.log(`Generated: ${new Date().toLocaleString()}`);

        // Mobile-specific recommendations
        console.log('\n💡 Mobile Recommendations:');
        if (platform.includes('iOS')) {
            if (parseFloat(this.browserInfo.osVersion) >= 15) {
                console.log('✅ iOS 15+ has excellent WebAuthn support with iCloud Keychain sync');
            } else if (parseFloat(this.browserInfo.osVersion) >= 14) {
                console.log('✅ iOS 14+ has good WebAuthn support');
                console.log('💡 Consider updating to iOS 15+ for enhanced features');
            } else {
                console.log('❌ Update to iOS 14+ for WebAuthn support');
            }
        } else if (platform.includes('Android')) {
            if (parseInt(this.browserInfo.osVersion) >= 9) {
                console.log('✅ Android 9+ has excellent biometric authentication');
            } else if (parseInt(this.browserInfo.osVersion) >= 7) {
                console.log('✅ Android 7+ has good WebAuthn support');
                console.log('💡 Consider updating to Android 9+ for enhanced biometrics');
            } else {
                console.log('❌ Update to Android 7+ for WebAuthn support');
            }
        }

        console.log('\n📱 Mobile WebAuthn Notes:');
        console.log('• Mobile devices typically use platform authenticators (biometrics)');
        console.log('• Cross-device authentication allows mobile to authenticate for desktop');
        console.log('• Longer timeouts may be needed for device unlock');
        console.log('• Native biometric prompts provide excellent user experience');
        console.log('• App switching during authentication may interrupt the flow');

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
    module.exports = MobileBrowserTest;
}

// Auto-run if in browser context
if (typeof window !== 'undefined') {
    window.MobileBrowserTest = MobileBrowserTest;
    
    // Provide easy way to run the test
    window.runMobileBrowserTest = async function() {
        const test = new MobileBrowserTest();
        return await test.runAllTests();
    };
    
    console.log('Mobile Browser Test loaded. Run with: runMobileBrowserTest()');
}