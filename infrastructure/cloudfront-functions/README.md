# CloudFront Functions

## og-bot-routing.js

Routes social media bot crawlers to static OG HTML files for event pages.
Non-bot traffic passes through to the SPA unchanged.

### How it works

1. On event publish, `scripts/generate_og_html.py` generates a minimal HTML file with OG meta tags
2. The HTML file is uploaded to S3: `s3://h-dcn-frontend-506221081911/events/{slug}/og.html`
3. The CloudFront Function intercepts viewer-request events
4. If User-Agent matches a known bot AND the path is `/events/{slug}/info`:
   - Rewrite the URI to `/events/{slug}/og.html`
5. Non-bot traffic passes through unchanged (SPA handles client-side routing)

### Detected bots

- `facebookexternalhit` (Facebook/Meta crawler)
- `Twitterbot` (X/Twitter crawler)
- `LinkedInBot` (LinkedIn crawler)
- `Slackbot` (Slack link previews)
- `WhatsApp` (WhatsApp link previews)
- `Googlebot` (Google search crawler)

### Deployment

See `infrastructure/cloudfront-og-function.yaml` for full CLI deployment steps.

Quick reference:

```bash
# Create
aws cloudfront create-function \
  --name og-bot-routing \
  --function-config '{"Comment":"OG bot routing for H-DCN event pages","Runtime":"cloudfront-js-2.0"}' \
  --function-code fileb://infrastructure/cloudfront-functions/og-bot-routing.js \
  --profile nonprofit-deploy

# Publish (use ETag from create response)
aws cloudfront publish-function \
  --name og-bot-routing \
  --if-match <ETag> \
  --profile nonprofit-deploy

# Then associate with the distribution (see cloudfront-og-function.yaml for details)
```

### Testing

After deployment, verify with curl:

```bash
# Bot request — should return OG HTML content
curl -s -H "User-Agent: facebookexternalhit/1.1" \
  https://portal.h-dcn.nl/events/toerweekend-2026/info

# Twitter bot
curl -s -H "User-Agent: Twitterbot/1.0" \
  https://portal.h-dcn.nl/events/toerweekend-2026/info

# LinkedIn bot
curl -s -H "User-Agent: LinkedInBot/1.0" \
  https://portal.h-dcn.nl/events/toerweekend-2026/info

# Normal browser — should return SPA (index.html)
curl -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
  https://portal.h-dcn.nl/events/toerweekend-2026/info

# Verify OG tags are present in bot response
curl -s -H "User-Agent: facebookexternalhit/1.1" \
  https://portal.h-dcn.nl/events/toerweekend-2026/info | grep "og:title"
```

### Generating OG HTML files

```bash
# Single event
python scripts/generate_og_html.py --slug toerweekend-2026 --profile nonprofit-deploy

# All published events
python scripts/generate_og_html.py --slug dummy --all-published --profile nonprofit-deploy

# Dry run (print HTML without uploading)
python scripts/generate_og_html.py --slug toerweekend-2026 --dry-run --profile nonprofit-deploy
```

### Integration with event handlers

When an event status changes to `published`, call:

```python
from scripts.generate_og_html import generate_and_upload

# In update_event handler or sync_google_calendar handler:
if new_status == 'published':
    session = boto3.Session()
    generate_and_upload(event_record, session)
```

When an event is archived/deleted:

```python
from scripts.generate_og_html import delete_og_html

if new_status == 'archived' or is_delete:
    session = boto3.Session()
    delete_og_html(event['slug'], session)
```
