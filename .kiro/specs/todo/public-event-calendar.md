# Spec: Publieke Event Calendar

## Context

H-DCN wil een event calendar die:

- Zonder inloggen raadpleegbaar is door iedereen
- Deelbaar is op Facebook/social media (met poster, titel, datum)
- Inpasbaar is in de bestaande h-dcn.nl website
- Onderdeel is van de bestaande SPA (portal.h-dcn.nl)

## Scope

### In scope

- Publieke route `/events` (calendar overzicht) en `/events/:slug` (event detail/landing)
- Backend endpoint zonder auth die published events retourneert
- Open Graph meta tags voor social media sharing
- Responsive: 1 card per rij (mobile), 4 per rij (desktop)
- Gesorteerd op startdatum, alleen toekomstige events

### Out of scope

- Booking flow (vereist login, apart systeem)
- Event admin (bestaand)
- Zoeken/filteren op categorie (toekomstige iteratie)

---

## Routes

| Route                      | Auth          | Inhoud                                                              |
| -------------------------- | ------------- | ------------------------------------------------------------------- |
| `/events`                  | Geen          | Calendar overzicht: alle published events met `end_date >= vandaag` |
| `/events/:slug`            | Geen          | Landing page: poster, naam, datum, locatie, beschrijving            |
| `/events/:eventId/booking` | Cognito login | Booking flow (bestaand)                                             |

De `/events` en `/events/:slug` routes zijn publiek — geen Cognito token vereist.

---

## Backend

### Endpoint: `GET /events-public`

- Geen authenticatie
- Retourneert: events met `status === 'published'` en `end_date >= vandaag`
- Excludeert: `event_type === 'webshop'`
- Velden: `event_id`, `name`, `slug`, `event_type`, `location`, `start_date`, `end_date`, `poster_url`, `description`
- Geen admin-velden (cost, revenue, allowed_events, etc.)

Handler: `backend/handler/get_event_public/app.py` (bestaat al — uitbreiden of valideren)

---

## Frontend

### EventCalendarPage

- Route: `/events`
- Toont grid van event cards
- Mobile: 1 per rij, desktop: 4 per rij
- Gesorteerd op `start_date` ascending
- Elk card toont: poster (of placeholder), naam, datum, locatie
- Klikbaar → navigeert naar `/events/:slug`

### EventLandingPage

- Route: `/events/:slug`
- Toont: poster (groot), naam, start/end datum, locatie, beschrijving
- CTA button: "Aanmelden" → navigeert naar `/events/:eventId/booking` (vereist login)
- Als `participation === 'open'`: toon "Open voor iedereen"
- Als `participation === 'members'`: toon "Alleen voor H-DCN leden"
- Als `participation === 'closed'`: toon "Op uitnodiging"

### Slug veld

Het `slug` veld (al in Field Registry) wordt gebruikt als URL-friendly identifier:

- Gegenereerd vanuit `name` bij aanmaken event (admin)
- Formaat: `toerweekend-2026`, `alv-maart-2027`
- Uniek per event

---

## Social Media Deelbaarheid (OG Tags)

### Probleem

SPA retourneert lege HTML — Facebook/Twitter/LinkedIn kunnen geen content scrapen.

### Oplossing: CloudFront Function

CloudFront Function vóór de S3 origin:

1. Detecteert bot User-Agents (facebookexternalhit, Twitterbot, LinkedInBot, Googlebot)
2. Bij bot: fetch event data via `get_event_public` → retourneer minimale HTML met OG tags
3. Bij gewone browser: serve SPA normaal

```html
<!-- Gegenereerde HTML voor bots -->
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

### Relatie tot eerder besluit

`docs/decisions/defer-lambda-edge-og.md` stelde Lambda@Edge uit. CloudFront Functions zijn lichter (max 10KB, <1ms runtime, geen cold start, goedkoper). Heroverweging is gerechtvaardigd.

---

## Inpassen in bestaande website

### Optie 1: Directe link (simpelst)

Bestaande h-dcn.nl website linkt naar `https://portal.h-dcn.nl/events`. Publieke route, geen login nodig.

### Optie 2: API-driven widget

Bestaande website fetcht `GET /events-public` en rendert zelf een compacte event-lijst. Click-through gaat naar de portal.

### Optie 3: Iframe (fallback)

```html
<iframe src="https://portal.h-dcn.nl/events" width="100%" height="600"></iframe>
```

Aanbeveling: start met optie 1, overweeg optie 2 als de hoofdsite meer controle wil over styling.

---

## Afhankelijkheden

- `slug` veld moet gevuld zijn op events (admin UI moet dit genereren bij aanmaken)
- `poster_url` moet gevuld zijn voor social media previews
- `get_event_public` handler moet published + toekomstige events retourneren
- CloudFront distributie moet een Function association krijgen

---

## Prioriteit

Laag-medium. Functioneel niet blokkerend voor de booking flow die nu gebouwd wordt. Wel belangrijk voor zichtbaarheid en marketing van events naar niet-leden en op social media.

Suggested sequence:

1. Publieke route + page in SPA (zonder OG tags) — snel werkend
2. CloudFront Function voor OG tags — deelbaarheid
3. Widget/API voor externe site — integratie
