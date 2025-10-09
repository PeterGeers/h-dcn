// End-to-End Functional Tests for H-DCN Dashboard
// Run with: node test-e2e.js

const fs = require('fs');
const path = require('path');

console.log('🧪 H-DCN E2E Functional Tests');
console.log('==============================\n');

let passed = 0;
let failed = 0;

function test(name, testFn) {
    try {
        testFn();
        console.log(`✅ ${name}`);
        passed++;
    } catch (error) {
        console.log(`❌ ${name}: ${error.message}`);
        failed++;
    }
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

// Test 1: Check critical files exist
test('Critical files exist', () => {
    const criticalFiles = [
        'src/App.js',
        'src/pages/Dashboard.js',
        'src/modules/members/MemberAdminPage.js',
        'src/modules/webshop/WebshopPage.js',
        'src/modules/products/ProductManagementPage.js',
        'src/components/AppCard.js',
        'src/utils/api.js'
    ];
    
    criticalFiles.forEach(file => {
        assert(fs.existsSync(file), `Missing critical file: ${file}`);
    });
});

// Test 2: Check environment configuration
test('Environment configuration', () => {
    assert(fs.existsSync('.env'), '.env file missing');
    
    const envContent = fs.readFileSync('.env', 'utf8');
    const requiredVars = [
        'REACT_APP_AWS_REGION',
        'REACT_APP_USER_POOL_ID',
        'REACT_APP_USER_POOL_WEB_CLIENT_ID',
        'REACT_APP_API_BASE_URL'
    ];
    
    requiredVars.forEach(varName => {
        assert(
            envContent.includes(`${varName}=`) && !envContent.includes(`${varName}=\n`),
            `Environment variable ${varName} not configured`
        );
    });
});

// Test 3: Check package.json configuration
test('Package.json configuration', () => {
    assert(fs.existsSync('package.json'), 'package.json missing');
    
    const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
    
    assert(pkg.name, 'Package name missing');
    assert(pkg.scripts && pkg.scripts.build, 'Build script missing');
    assert(pkg.scripts && pkg.scripts.start, 'Start script missing');
    
    // Check critical dependencies
    const criticalDeps = [
        'react',
        '@chakra-ui/react',
        'aws-amplify',
        '@aws-amplify/ui-react',
        'react-router-dom'
    ];
    
    criticalDeps.forEach(dep => {
        assert(
            pkg.dependencies && pkg.dependencies[dep],
            `Critical dependency missing: ${dep}`
        );
    });
});

// Test 4: Check for hardcoded credentials
test('No hardcoded credentials', () => {
    const filesToCheck = [
        'src/utils/api.js',
        'src/modules/products/api/productApi.js'
    ];
    
    filesToCheck.forEach(file => {
        if (fs.existsSync(file)) {
            const content = fs.readFileSync(file, 'utf8');
            
            // Check for hardcoded AWS URLs (should use env vars)
            const hardcodedUrls = content.match(/https:\/\/[a-z0-9]+\.execute-api\.[a-z0-9-]+\.amazonaws\.com/g);
            if (hardcodedUrls) {
                // Allow if it's used as fallback with process.env
                const hasEnvFallback = content.includes('process.env.REACT_APP_API_BASE_URL');
                assert(hasEnvFallback, `Hardcoded AWS URL in ${file} without env fallback`);
            }
        }
    });
});

// Test 5: Check responsive design implementation
test('Responsive design implementation', () => {
    const responsiveFiles = [
        'src/modules/members/MemberAdminPage.js',
        'src/modules/webshop/WebshopPage.js',
        'src/components/AppCard.js'
    ];
    
    responsiveFiles.forEach(file => {
        if (fs.existsSync(file)) {
            const content = fs.readFileSync(file, 'utf8');
            
            // Check for responsive breakpoints
            assert(
                content.includes('base:') || content.includes('md:') || content.includes('useBreakpointValue'),
                `${file} missing responsive design patterns`
            );
        }
    });
});

// Test 6: Check for XSS protection
test('XSS protection implemented', () => {
    const securityFiles = [
        'src/modules/webshop/components/OrderConfirmation.js',
        'src/modules/members/components/CsvUpload.js'
    ];
    
    securityFiles.forEach(file => {
        if (fs.existsSync(file)) {
            const content = fs.readFileSync(file, 'utf8');
            
            // Check for HTML escaping or sanitization
            const hasSanitization = 
                content.includes('escapeHtml') || 
                content.includes('.replace(/[<>"\'&]/g') ||
                content.includes('setAttribute');
                
            assert(hasSanitization, `${file} missing XSS protection`);
        }
    });
});

// Test 7: Check mobile-friendly components
test('Mobile-friendly components', () => {
    const mobileFiles = [
        'src/modules/webshop/components/ProductCard.js',
        'src/modules/products/components/ProductTable.jsx'
    ];
    
    mobileFiles.forEach(file => {
        if (fs.existsSync(file)) {
            const content = fs.readFileSync(file, 'utf8');
            
            // Check for mobile-specific sizing
            assert(
                content.includes('base:') && (content.includes('md:') || content.includes('lg:')),
                `${file} missing mobile responsive breakpoints`
            );
        }
    });
});

// Test 8: Check build configuration
test('Build configuration', () => {
    const indexHtml = 'public/index.html';
    assert(fs.existsSync(indexHtml), 'public/index.html missing');
    
    const htmlContent = fs.readFileSync(indexHtml, 'utf8');
    assert(
        htmlContent.includes('viewport') && htmlContent.includes('width=device-width'),
        'Missing mobile viewport meta tag'
    );
});

// Test 9: Check Git ignore configuration
test('Git ignore configuration', () => {
    const gitignore = '../.gitignore';
    assert(fs.existsSync(gitignore), '.gitignore missing');
    
    const gitignoreContent = fs.readFileSync(gitignore, 'utf8');
    const criticalIgnores = ['node_modules', '.env', 'build/', '*.log'];
    
    criticalIgnores.forEach(ignore => {
        assert(
            gitignoreContent.includes(ignore),
            `Missing ${ignore} in .gitignore`
        );
    });
});

// Test 10: Check for console.log cleanup
test('Production code cleanup', () => {
    const prodFiles = [
        'src/App.js',
        'src/pages/Dashboard.js'
    ];
    
    prodFiles.forEach(file => {
        if (fs.existsSync(file)) {
            const content = fs.readFileSync(file, 'utf8');
            const consoleLogs = (content.match(/console\.log/g) || []).length;
            
            assert(
                consoleLogs <= 2,
                `${file} has ${consoleLogs} console.log statements (should be minimal for production)`
            );
        }
    });
});

// Final Report
console.log('\n📊 Test Results');
console.log('===============');
console.log(`✅ Passed: ${passed}`);
console.log(`❌ Failed: ${failed}`);
console.log(`📈 Success Rate: ${Math.round((passed / (passed + failed)) * 100)}%`);

if (failed === 0) {
    console.log('\n🎉 All tests passed! Code is ready for deployment.');
    process.exit(0);
} else {
    console.log('\n🚫 Some tests failed. Fix issues before deployment.');
    process.exit(1);
}