/**
 * CloudFront Function: OG Bot Routing (viewer-request)
 *
 * Routes social media bot crawlers to static OG HTML files.
 * Non-bot traffic is passed through unchanged to the SPA.
 *
 * Behavior:
 *   - Bot + /events/{slug}/info → rewrite to /events/{slug}/og.html
 *   - Everything else → pass through (SPA handles routing)
 *
 * Detected bots:
 *   facebookexternalhit, Twitterbot, LinkedInBot, Slackbot, WhatsApp, Googlebot
 *
 * Constraints (CloudFront Functions):
 *   - ES5.1 subset (no let/const, no arrow functions, no template literals)
 *   - <1ms execution time
 *   - No network calls
 *   - 10KB max package size
 *
 * Deploy via AWS Console or CLI:
 *   aws cloudfront create-function \
 *     --name og-bot-routing \
 *     --function-config '{"Comment":"OG bot routing for event pages","Runtime":"cloudfront-js-2.0"}' \
 *     --function-code fileb://infrastructure/cloudfront-functions/og-bot-routing.js \
 *     --profile nonprofit-deploy
 */
function handler(event) {
    var request = event.request;
    var headers = request.headers;
    var uri = request.uri;
    var userAgent = headers['user-agent'] ? headers['user-agent'].value : '';

    var botPattern = /facebookexternalhit|Twitterbot|LinkedInBot|Slackbot|WhatsApp|Googlebot/i;
    var eventPattern = /^\/events\/([^\/]+)\/info\/?$/;

    if (botPattern.test(userAgent) && eventPattern.test(uri)) {
        var match = uri.match(eventPattern);
        request.uri = '/events/' + match[1] + '/og.html';
    }

    return request;
}
