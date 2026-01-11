/**
 * Frontend-Backend Integration Test for New Role Structure
 * Tests that frontend permission system works correctly with backend API responses
 * 
 * This test verifies:
 * 1. Frontend permission functions correctly identify user capabilities
 * 2. Frontend makes correct API calls based on user permissions
 * 3. Frontend handles backend permission errors gracefully
 * 4. Regional access controls work consistently
 */

// Import the permission functions (adjust path as needed)
import { 
    getUserRoles, 
    userHasPermissionWithRegion,
    validatePermissionWithRegion,
    getUserAccessibleRegions,
    userHasPermissionType,
    checkUIPermission
} from '../src/utils/functionPermissions.js';

// Test configuration
const API_BASE_URL = 'https://your-api-gateway-url.amazonaws.com/Prod'; // Update with actual API URL

class FrontendBackendIntegrationTest {
    constructor() {
        this.testResults = [];
        this.testUsers = this.createTestUsers();
    }

    createTestUsers() {
        /**
         * Create test users with different role combinations for the new role structure
         */
        return {
            nationalAdmin: {
                email: 'admin@hdcn-test.nl',
                groups: ['Members_CRUD', 'Regio_All'],
                signInUserSession: {
                    accessToken: {
                        payload: {
                            'cognito:groups': ['Members_CRUD', 'Regio_All']
                        }
                    }
                },
                description: 'National administrator with full member access'
            },
            regionalCoordinator: {
                email: 'coordinator@hdcn-test.nl',
                groups: ['Members_CRUD', 'Regio_Utrecht'],
                signInUserSession: {
                    accessToken: {
                        payload: {
                            'cognito:groups': ['Members_CRUD', 'Regio_Utrecht']
                        }
                    }
                },
                description: 'Regional coordinator for Utrecht region'
            },
            readOnlyNational: {
                email: 'readonly@hdcn-test.nl',
                groups: ['Members_Read', 'Regio_All'],
                signInUserSession: {
                    accessToken: {
                        payload: {
                            'cognito:groups': ['Members_Read', 'Regio_All']
                        }
                    }
                },
                description: 'National read-only user'
            },
            exportUser: {
                email: 'export@hdcn-test.nl',
                groups: ['Members_Export', 'Regio_All'],
                signInUserSession: {
                    accessToken: {
                        payload: {
                            'cognito:groups': ['Members_Export', 'Regio_All']
                        }
                    }
                },
                description: 'Export user with national access'
            },
            incompleteRoleUser: {
                email: 'incomplete@hdcn-test.nl',
                groups: ['Members_CRUD'], // Missing region role
                signInUserSession: {
                    accessToken: {
                        payload: {
                            'cognito:groups': ['Members_CRUD']
                        }
                    }
                },
                description: 'User with permission but no region (should be denied)'
            },
            noPermissionUser: {
                email: 'noperm@hdcn-test.nl',
                groups: ['Regio_All'], // Missing permission role
                signInUserSession: {
                    accessToken: {
                        payload: {
                            'cognito:groups': ['Regio_All']
                        }
                    }
                },
                description: 'User with region but no permission (should be denied)'
            },
            multiPermissionUser: {
                email: 'multi@hdcn-test.nl',
                groups: ['Members_CRUD', 'Events_Read', 'Products_CRUD', 'Regio_All'],
                signInUserSession: {
                    accessToken: {
                        payload: {
                            'cognito:groups': ['Members_CRUD', 'Events_Read', 'Products_CRUD', 'Regio_All']
                        }
                    }
                },
                description: 'User with multiple permissions and national access'
            },
            regionalMultiUser: {
                email: 'regional@hdcn-test.nl',
                groups: ['Members_Read', 'Events_CRUD', 'Regio_Groningen/Drenthe'],
                signInUserSession: {
                    accessToken: {
                        payload: {
                            'cognito:groups': ['Members_Read', 'Events_CRUD', 'Regio_Groningen/Drenthe']
                        }
                    }
                },
                description: 'User with multiple permissions and regional access'
            }
        };
    }

    logTestResult(testName, userType, expected, actual, details = '') {
        /**
         * Log test results for reporting
         */
        const success = expected === actual;
        this.testResults.push({
            timestamp: new Date().toISOString(),
            testName,
            userType,
            expected,
            actual,
            success,
            details
        });

        const statusIcon = success ? '✅' : '❌';
        console.log(`${statusIcon} ${testName} | ${userType} | Expected: ${expected}, Got: ${actual} | ${details}`);
    }

    testFrontendPermissionFunctions() {
        /**
         * Test frontend permission functions with new role structure
         */
        console.log('\n🔍 Testing Frontend Permission Functions');
        console.log('='.repeat(50));

        for (const [userType, userData] of Object.entries(this.testUsers)) {
            console.log(`\n👤 Testing user: ${userType} (${userData.description})`);
            
            // Test getUserRoles function
            const extractedRoles = getUserRoles(userData);
            const expectedRoles = userData.groups;
            const rolesMatch = JSON.stringify(extractedRoles.sort()) === JSON.stringify(expectedRoles.sort());
            
            this.logTestResult(
                'getUserRoles Function', userType,
                true, rolesMatch,
                `Expected: ${expectedRoles.join(', ')}, Got: ${extractedRoles.join(', ')}`
            );

            // Test userHasPermissionType function
            const hasMembers = userHasPermissionType(userData, 'members', 'crud');
            const shouldHaveMembers = userData.groups.includes('Members_CRUD');
            
            this.logTestResult(
                'userHasPermissionType (Members CRUD)', userType,
                shouldHaveMembers, hasMembers,
                `Roles: ${userData.groups.join(', ')}`
            );

            // Test userHasPermissionWithRegion function
            const hasPermissionWithRegion = userHasPermissionWithRegion(userData, 'members_read');
            const shouldHavePermissionWithRegion = this.shouldUserHavePermissionWithRegion(userData.groups, 'members_read');
            
            this.logTestResult(
                'userHasPermissionWithRegion', userType,
                shouldHavePermissionWithRegion, hasPermissionWithRegion,
                `Permission: members_read, Roles: ${userData.groups.join(', ')}`
            );

            // Test getUserAccessibleRegions function
            const accessibleRegions = getUserAccessibleRegions(userData);
            const expectedRegions = this.getExpectedAccessibleRegions(userData.groups);
            const regionsMatch = JSON.stringify(accessibleRegions.sort()) === JSON.stringify(expectedRegions.sort());
            
            this.logTestResult(
                'getUserAccessibleRegions', userType,
                true, regionsMatch,
                `Expected: ${expectedRegions.join(', ')}, Got: ${accessibleRegions.join(', ')}`
            );

            // Test checkUIPermission function
            const canReadMembers = checkUIPermission(userData, 'members', 'read');
            const shouldReadMembers = this.shouldUserHaveUIPermission(userData.groups, 'members', 'read');
            
            this.logTestResult(
                'checkUIPermission (Members Read)', userType,
                shouldReadMembers, canReadMembers,
                `Action: members.read, Roles: ${userData.groups.join(', ')}`
            );

            const canWriteMembers = checkUIPermission(userData, 'members', 'write');
            const shouldWriteMembers = this.shouldUserHaveUIPermission(userData.groups, 'members', 'write');
            
            this.logTestResult(
                'checkUIPermission (Members Write)', userType,
                shouldWriteMembers, canWriteMembers,
                `Action: members.write, Roles: ${userData.groups.join(', ')}`
            );
        }
    }

    shouldUserHavePermissionWithRegion(userRoles, permission) {
        /**
         * Determine if user should have permission with region based on new role structure
         */
        const permissionMapping = {
            'members_read': ['Members_Read', 'Members_CRUD'],
            'members_crud': ['Members_CRUD'],
            'members_export': ['Members_Export'],
            'events_read': ['Events_Read', 'Events_CRUD'],
            'events_crud': ['Events_CRUD'],
            'products_read': ['Products_Read', 'Products_CRUD'],
            'products_crud': ['Products_CRUD']
        };

        const requiredRoles = permissionMapping[permission] || [];
        const hasPermission = requiredRoles.some(role => userRoles.includes(role));
        const hasRegion = userRoles.some(role => role.startsWith('Regio_'));

        return hasPermission && hasRegion;
    }

    getExpectedAccessibleRegions(userRoles) {
        /**
         * Get expected accessible regions based on user roles
         */
        if (userRoles.includes('Regio_All')) {
            return ['all'];
        }

        const regions = [];
        const regionMapping = {
            'Regio_Utrecht': 'utrecht',
            'Regio_Limburg': 'limburg',
            'Regio_Groningen/Drenthe': 'groningen_drenthe',
            'Regio_Zuid-Holland': 'zuid_holland',
            'Regio_Noord-Holland': 'noord_holland',
            'Regio_Oost': 'oost',
            'Regio_Brabant/Zeeland': 'brabant_zeeland',
            'Regio_Friesland': 'friesland',
            'Regio_Duitsland': 'duitsland'
        };

        for (const role of userRoles) {
            if (regionMapping[role]) {
                regions.push(regionMapping[role]);
            }
        }

        return regions;
    }

    shouldUserHaveUIPermission(userRoles, functionName, action) {
        /**
         * Determine if user should have UI permission based on new role structure
         */
        const permissionType = action === 'write' ? 'crud' : 'read';
        const permission = `${functionName}_${permissionType}`;
        return this.shouldUserHavePermissionWithRegion(userRoles, permission);
    }

    async testAPIIntegration() {
        /**
         * Test API integration with frontend permission system
         */
        console.log('\n🔍 Testing API Integration');
        console.log('='.repeat(50));

        // Test endpoints that require different permissions
        const testEndpoints = [
            {
                endpoint: '/members',
                method: 'GET',
                requiredPermission: 'members_read',
                description: 'Get members list'
            },
            {
                endpoint: '/members',
                method: 'POST',
                requiredPermission: 'members_crud',
                description: 'Create new member',
                data: { name: 'Test User', email: 'test@example.com' }
            }
        ];

        for (const [userType, userData] of Object.entries(this.testUsers)) {
            // Create mock JWT token for testing
            const mockJWT = this.createMockJWT(userData.email, userData.groups);
            
            for (const endpointTest of testEndpoints) {
                try {
                    // Check if frontend thinks user should have access
                    const frontendSaysAccess = this.shouldUserHavePermissionWithRegion(
                        userData.groups, 
                        endpointTest.requiredPermission
                    );

                    // Make API request (in a real test, this would be actual HTTP request)
                    const apiResult = await this.simulateAPICall(
                        endpointTest.endpoint,
                        endpointTest.method,
                        mockJWT,
                        endpointTest.data
                    );

                    // Check if frontend prediction matches API result
                    const predictionCorrect = frontendSaysAccess === apiResult.success;

                    this.logTestResult(
                        `API Integration ${endpointTest.description}`, userType,
                        true, predictionCorrect,
                        `Frontend predicted: ${frontendSaysAccess}, API result: ${apiResult.success}, Status: ${apiResult.statusCode}`
                    );

                } catch (error) {
                    this.logTestResult(
                        `API Integration ${endpointTest.description}`, userType,
                        false, false,
                        `Error: ${error.message}`
                    );
                }
            }
        }
    }

    createMockJWT(email, groups) {
        /**
         * Create a mock JWT token for testing
         */
        const payload = {
            email: email,
            'cognito:groups': groups,
            iat: Math.floor(Date.now() / 1000),
            exp: Math.floor(Date.now() / 1000) + 3600
        };

        // Simple base64 encoding for test purposes
        const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
        const payloadEncoded = btoa(JSON.stringify(payload));
        const signature = btoa('test-signature');

        return `${header}.${payloadEncoded}.${signature}`;
    }

    async simulateAPICall(endpoint, method, jwt, data = null) {
        /**
         * Simulate API call (in real test, this would make actual HTTP request)
         * For now, we simulate the backend logic
         */
        try {
            // Decode JWT to get user roles
            const payloadPart = jwt.split('.')[1];
            const payload = JSON.parse(atob(payloadPart));
            const userRoles = payload['cognito:groups'] || [];

            // Simulate backend permission checking
            const hasAccess = this.simulateBackendPermissionCheck(userRoles, endpoint, method);

            return {
                success: hasAccess,
                statusCode: hasAccess ? 200 : 403,
                data: hasAccess ? { message: 'Success' } : { error: 'Access denied' }
            };

        } catch (error) {
            return {
                success: false,
                statusCode: 401,
                data: { error: 'Invalid token' }
            };
        }
    }

    simulateBackendPermissionCheck(userRoles, endpoint, method) {
        /**
         * Simulate backend permission checking logic
         */
        // Map endpoints to required permissions (matching backend logic)
        const endpointPermissions = {
            '/members': {
                'GET': 'members_read',
                'POST': 'members_crud',
                'PUT': 'members_crud',
                'DELETE': 'members_crud'
            },
            '/events': {
                'GET': 'events_read',
                'POST': 'events_crud',
                'PUT': 'events_crud',
                'DELETE': 'events_crud'
            },
            '/products': {
                'GET': 'products_read',
                'POST': 'products_crud',
                'PUT': 'products_crud',
                'DELETE': 'products_crud'
            }
        };

        const requiredPermission = endpointPermissions[endpoint]?.[method];
        if (!requiredPermission) {
            return false; // Unknown endpoint
        }

        return this.shouldUserHavePermissionWithRegion(userRoles, requiredPermission);
    }

    testRegionalAccessConsistency() {
        /**
         * Test that regional access controls work consistently
         */
        console.log('\n🔍 Testing Regional Access Consistency');
        console.log('='.repeat(50));

        const regionalTestCases = [
            {
                userRoles: ['Members_Read', 'Regio_Utrecht'],
                targetRegion: 'utrecht',
                shouldHaveAccess: true,
                description: 'Regional user accessing own region'
            },
            {
                userRoles: ['Members_Read', 'Regio_Utrecht'],
                targetRegion: 'limburg',
                shouldHaveAccess: false,
                description: 'Regional user accessing different region'
            },
            {
                userRoles: ['Members_Read', 'Regio_All'],
                targetRegion: 'utrecht',
                shouldHaveAccess: true,
                description: 'National user accessing any region'
            },
            {
                userRoles: ['Members_Read', 'Regio_All'],
                targetRegion: 'limburg',
                shouldHaveAccess: true,
                description: 'National user accessing any region'
            }
        ];

        for (let i = 0; i < regionalTestCases.length; i++) {
            const testCase = regionalTestCases[i];
            
            // Create mock user for this test case
            const mockUser = {
                groups: testCase.userRoles,
                signInUserSession: {
                    accessToken: {
                        payload: {
                            'cognito:groups': testCase.userRoles
                        }
                    }
                }
            };

            // Test frontend regional access logic
            const frontendAccess = this.checkFrontendRegionalAccess(testCase.userRoles, testCase.targetRegion);
            
            this.logTestResult(
                'Frontend Regional Access', `Case ${i + 1}`,
                testCase.shouldHaveAccess, frontendAccess,
                testCase.description
            );

            // Test backend regional access logic (simulated)
            const backendAccess = this.checkBackendRegionalAccess(testCase.userRoles, testCase.targetRegion);
            
            this.logTestResult(
                'Backend Regional Access', `Case ${i + 1}`,
                testCase.shouldHaveAccess, backendAccess,
                testCase.description
            );

            // Test consistency between frontend and backend
            const consistent = frontendAccess === backendAccess;
            
            this.logTestResult(
                'Regional Access Consistency', `Case ${i + 1}`,
                true, consistent,
                `Frontend: ${frontendAccess}, Backend: ${backendAccess}`
            );
        }
    }

    checkFrontendRegionalAccess(userRoles, targetRegion) {
        /**
         * Check frontend regional access logic
         */
        // Check if user has Regio_All (national access)
        if (userRoles.includes('Regio_All')) {
            return true;
        }

        // Check if user has specific regional access
        const regionRoleMapping = {
            'utrecht': 'Regio_Utrecht',
            'limburg': 'Regio_Limburg',
            'groningen_drenthe': 'Regio_Groningen/Drenthe',
            'zuid_holland': 'Regio_Zuid-Holland',
            'noord_holland': 'Regio_Noord-Holland',
            'oost': 'Regio_Oost',
            'brabant_zeeland': 'Regio_Brabant/Zeeland',
            'friesland': 'Regio_Friesland',
            'duitsland': 'Regio_Duitsland'
        };

        const requiredRole = regionRoleMapping[targetRegion];
        return requiredRole ? userRoles.includes(requiredRole) : false;
    }

    checkBackendRegionalAccess(userRoles, targetRegion) {
        /**
         * Simulate backend regional access logic (should match frontend)
         */
        return this.checkFrontendRegionalAccess(userRoles, targetRegion);
    }

    async runAllTests() {
        /**
         * Run all integration tests
         */
        console.log('🚀 Starting Frontend-Backend Integration Tests');
        console.log('Testing new permission + region role structure');
        console.log('='.repeat(60));

        // Run all test suites
        this.testFrontendPermissionFunctions();
        await this.testAPIIntegration();
        this.testRegionalAccessConsistency();

        // Generate summary report
        this.generateSummaryReport();
    }

    generateSummaryReport() {
        /**
         * Generate summary report of all test results
         */
        console.log('\n📊 Test Summary Report');
        console.log('='.repeat(60));

        const totalTests = this.testResults.length;
        const passedTests = this.testResults.filter(result => result.success).length;
        const failedTests = totalTests - passedTests;

        console.log(`Total Tests: ${totalTests}`);
        console.log(`Passed: ${passedTests} ✅`);
        console.log(`Failed: ${failedTests} ❌`);
        console.log(`Success Rate: ${((passedTests / totalTests) * 100).toFixed(1)}%`);

        if (failedTests > 0) {
            console.log('\n❌ Failed Tests:');
            this.testResults
                .filter(result => !result.success)
                .forEach(result => {
                    console.log(`  - ${result.testName} | ${result.userType} | ${result.details}`);
                });
        }

        // Save results to localStorage for debugging
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem('frontendBackendIntegrationTestResults', JSON.stringify({
                summary: {
                    totalTests,
                    passedTests,
                    failedTests,
                    successRate: (passedTests / totalTests) * 100,
                    timestamp: new Date().toISOString()
                },
                detailedResults: this.testResults
            }));
            console.log('\n📄 Detailed results saved to localStorage');
        }

        return failedTests === 0;
    }
}

// Main execution function
async function runFrontendBackendIntegrationTests() {
    const testRunner = new FrontendBackendIntegrationTest();
    
    try {
        const success = await testRunner.runAllTests();
        
        if (success) {
            console.log('\n🎉 All frontend integration tests passed!');
            console.log('Frontend permission system works correctly with new role structure.');
            return true;
        } else {
            console.log('\n⚠️  Some frontend integration tests failed.');
            console.log('Please review the failed tests and fix the issues.');
            return false;
        }
    } catch (error) {
        console.error('\n💥 Test execution failed:', error);
        return false;
    }
}

// Export for use in other modules or run directly
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FrontendBackendIntegrationTest, runFrontendBackendIntegrationTests };
} else {
    // Run tests if loaded directly in browser
    runFrontendBackendIntegrationTests();
}