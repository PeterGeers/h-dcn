/**
 * Local test for og-bot-routing CloudFront Function.
 *
 * Run: node infrastructure/cloudfront-functions/test-og-bot-routing.js
 */

// Load the handler (CloudFront Function format)
eval(require('fs').readFileSync(__dirname + '/og-bot-routing.js', 'utf8'));

function createEvent(uri, userAgent) {
    return {
        request: {
            uri: uri,
            headers: {
                'user-agent': { value: userAgent }
            }
        }
    };
}

function assertEqual(actual, expected, testName) {
    if (actual !== expected) {
        console.error('FAIL: ' + testName);
        console.error('  Expected: ' + expected);
        console.error('  Actual:   ' + actual);
        process.exitCode = 1;
    } else {
        console.log('PASS: ' + testName);
    }
}

// Test: Facebook bot on event info page -> rewrite to og.html
var result1 = handler(createEvent('/events/toerweekend-2026/info', 'facebookexternalhit/1.1'));
assertEqual(result1.uri, '/events/toerweekend-2026/og.html', 'Facebook bot rewrites to og.html');

// Test: Twitter bot on event info page -> rewrite to og.html
var result2 = handler(createEvent('/events/alv-maart/info', 'Twitterbot/1.0'));
assertEqual(result2.uri, '/events/alv-maart/og.html', 'Twitter bot rewrites to og.html');

// Test: LinkedIn bot
var result3 = handler(createEvent('/events/openingsrit-2026/info', 'LinkedInBot/1.0'));
assertEqual(result3.uri, '/events/openingsrit-2026/og.html', 'LinkedIn bot rewrites to og.html');

// Test: Slackbot
var result4 = handler(createEvent('/events/my-event/info', 'Slackbot-LinkExpanding 1.0'));
assertEqual(result4.uri, '/events/my-event/og.html', 'Slackbot rewrites to og.html');

// Test: WhatsApp
var result5 = handler(createEvent('/events/test/info', 'WhatsApp/2.23.1'));
assertEqual(result5.uri, '/events/test/og.html', 'WhatsApp rewrites to og.html');

// Test: Googlebot
var result6 = handler(createEvent('/events/event-x/info', 'Googlebot/2.1'));
assertEqual(result6.uri, '/events/event-x/og.html', 'Googlebot rewrites to og.html');

// Test: Normal browser -> pass through unchanged
var result7 = handler(createEvent('/events/toerweekend-2026/info', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'));
assertEqual(result7.uri, '/events/toerweekend-2026/info', 'Normal browser passes through');

// Test: Bot on non-event page -> pass through
var result8 = handler(createEvent('/members', 'facebookexternalhit/1.1'));
assertEqual(result8.uri, '/members', 'Bot on non-event page passes through');

// Test: Bot on /events (list page) -> pass through (no slug match)
var result9 = handler(createEvent('/events', 'facebookexternalhit/1.1'));
assertEqual(result9.uri, '/events', 'Bot on events list page passes through');

// Test: Bot on event page without /info suffix -> pass through
var result10 = handler(createEvent('/events/toerweekend-2026', 'facebookexternalhit/1.1'));
assertEqual(result10.uri, '/events/toerweekend-2026', 'Bot on event page without /info passes through');

// Test: Bot on /events/slug/info/ (trailing slash) -> rewrite
var result11 = handler(createEvent('/events/toerweekend-2026/info/', 'facebookexternalhit/1.1'));
assertEqual(result11.uri, '/events/toerweekend-2026/og.html', 'Bot with trailing slash rewrites to og.html');

// Test: No user-agent header
var noUaEvent = {
    request: {
        uri: '/events/test/info',
        headers: {}
    }
};
var result12 = handler(noUaEvent);
assertEqual(result12.uri, '/events/test/info', 'Missing user-agent passes through');

console.log('\nAll tests completed.');
