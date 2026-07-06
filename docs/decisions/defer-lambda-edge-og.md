# Decision: CloudFront Function for Open Graph Pre-rendering

**Date:** 2025-07-14 (original), 2026-07 (updated)  
**Status:** Accepted — CloudFront Function  
**Related:** Public Event Calendar spec, Task 25.2

## Context

SPA retourneert lege HTML — social media bots (Facebook, LinkedIn) kunnen geen content scrapen voor link previews. Events moeten deelbaar zijn met correcte poster, titel en datum.

## Decision

Gebruik een **CloudFront Function** (viewer-request) voor OG tag injection bij bot traffic.

### Waarom CloudFront Function (niet Lambda@Edge)

| Aspect             | Lambda@Edge                        | CloudFront Function             |
| ------------------ | ---------------------------------- | ------------------------------- |
| Cold start         | 50-200ms                           | Geen (<1ms)                     |
| Deploy regio       | Verplicht us-east-1                | Automatisch alle edge locations |
| Max execution time | 5s (viewer) / 30s (origin)         | <1ms                            |
| Max package size   | 50MB                               | 10KB                            |
| Kosten             | Per request + duration             | ~1/6e van Lambda@Edge           |
| Network calls      | Ja (fetch mogelijk)                | Nee (alleen request/response)   |
| Complexiteit       | Hoog (cross-region deploy, layers) | Laag (inline JS, geen deps)     |

### Beperking: geen network calls

CloudFront Functions kunnen geen externe API calls doen. De OG data moet dus beschikbaar zijn **zonder** een fetch naar de backend.

### Oplossing: event metadata in de URL/path + S3 manifest

Twee opties:

**Optie A — S3 manifest file (aanbevolen):**

- Bij publish/update van een event: schrijf een klein JSON manifest naar S3 (`og-manifests/{slug}.json`)
- CloudFront Function leest dit manifest via een KeyValueStore of via S3 origin redirect
- Bevat: title, description, image URL, canonical URL

**Optie B — Encoded metadata in response headers:**

- Backend zet OG-relevante metadata als custom headers bij de S3 object
- CloudFront Function leest headers en injecteert in HTML response

**Optie C — Statische HTML per event:**

- Bij publish: genereer een statische `events/{slug}/index.html` met OG tags
- CloudFront Function routeert bots naar deze statische file
- Browsers krijgen de SPA

### Aanbeveling: Optie C (simpelst)

Bij publish van een event wordt een minimale HTML file gegenereerd:

```html
<!DOCTYPE html>
<html>
  <head>
    <meta property="og:title" content="Toerweekend 2026" />
    <meta
      property="og:description"
      content="17-20 juli 2026 • Holysloot Amsterdam"
    />
    <meta
      property="og:image"
      content="https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/event-posters/toerweekend-2026.jpg"
    />
    <meta
      property="og:url"
      content="https://portal.h-dcn.nl/events/toerweekend-2026"
    />
    <meta property="og:type" content="event" />
  </head>
  <body>
    <script>
      window.location.href = "/events/toerweekend-2026";
    </script>
  </body>
</html>
```

De CloudFront Function detecteert bots en routeert naar deze file. Browsers krijgen een redirect naar de SPA.

### Bot detectie (in CloudFront Function)

```javascript
function handler(event) {
  var request = event.request;
  var ua =
    (request.headers["user-agent"] && request.headers["user-agent"].value) ||
    "";
  var bots =
    /facebookexternalhit|Twitterbot|LinkedInBot|Slackbot|WhatsApp|Googlebot/i;

  if (bots.test(ua) && request.uri.startsWith("/events/")) {
    // Route to static OG HTML
    request.uri = request.uri + "/og.html";
  }
  return request;
}
```

## Supersedes

Dit besluit vervangt het originele "Deferred" status. Lambda@Edge is definitief afgewezen vanwege disproportionele complexiteit voor de use case.

## Originele overwegingen (2025-07)

- React Helmet dekt crawlers die JS uitvoeren (Twitter/X, Slack, Discord, WhatsApp)
- Facebook en LinkedIn hebben verbeterde JS rendering maar zijn nog niet 100% betrouwbaar
- Lambda@Edge complexiteit (us-east-1 deploy, cross-region SAM, Puppeteer layer) is disproportioneel
- CloudFront Functions hadden destijds geen fetch capability — maar statische file routing lost dit op
