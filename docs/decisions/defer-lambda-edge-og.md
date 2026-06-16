# Decision: Defer Lambda@Edge for Open Graph Pre-rendering

**Date:** 2025-07-14  
**Status:** Deferred  
**Related task:** 25.2 (Optional) Lambda@Edge for non-JS crawlers

## What was considered

Lambda@Edge to intercept requests from social media crawlers (Facebook, LinkedIn) that historically don't execute JavaScript. The function would detect bot user-agents at the CloudFront edge, render the page server-side, and return HTML with pre-populated `<meta property="og:...">` tags so link previews display correct event titles, descriptions, and images.

## Why it's deferred

1. **React Helmet covers most crawlers.** Task 25.1 implements dynamic OG meta tags via React Helmet. Crawlers that execute JavaScript (Twitter/X, Slack, Discord, WhatsApp) will pick up the tags without any edge infrastructure.

2. **Facebook and LinkedIn have improved JS rendering.** Both platforms have significantly improved their crawler capabilities in recent years and can now execute basic JavaScript for meta tag extraction.

3. **Complexity vs. value.** Lambda@Edge introduces:
   - Mandatory deployment to `us-east-1` (regardless of app region)
   - CloudFront distribution association and cache behavior configuration
   - A separate deployment pipeline or cross-region SAM setup
   - Ongoing maintenance of a rendering service (Puppeteer/Chromium layer or external service)

4. **Context of the feature.** The event landing page is a supplementary sharing feature for an internal club tool (~hundreds of members). The effort to maintain edge infrastructure is disproportionate to the audience size.

## When to reconsider

- If Facebook or LinkedIn link previews consistently fail to render event details (title, image, description missing or showing fallback values)
- If the club starts running public marketing campaigns where accurate social previews are critical for reach
- If a lightweight pre-rendering solution becomes available (e.g., CloudFront Functions gain fetch capability, or a managed service reduces the operational burden)

## Alternatives if needed later

- **CloudFront Functions** (lighter weight, but currently limited to simple request/response manipulation)
- **Pre-rendering service** (e.g., Prerender.io) as a CloudFront origin failover for bot traffic
- **Static meta tag injection at build time** for a limited set of featured events
