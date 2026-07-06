# H-DCN.nl Events Integration

Documentatie voor het integreren van de evenementenkalender op de h-dcn.nl website.

---

## Optie 1: Direct Link (aanbevolen)

De eenvoudigste aanpak — link rechtstreeks naar de evenementenkalender op het portal:

```
https://portal.h-dcn.nl/events/calendar
```

### Voorbeeld HTML

```html
<a
  href="https://portal.h-dcn.nl/events/calendar"
  target="_blank"
  rel="noopener noreferrer"
>
  Bekijk de evenementenkalender →
</a>
```

### Voordelen

- Geen onderhoud nodig op h-dcn.nl
- Altijd up-to-date
- Volledige filtering, responsive design, en evenement-landingspagina's beschikbaar
- SEO-vriendelijk (statische OG-tags voor social media sharing)

### Deeplinks naar individuele evenementen

```
https://portal.h-dcn.nl/events/{slug}/info
```

Bijvoorbeeld: `https://portal.h-dcn.nl/events/toerweekend-2026/info`

---

## Optie 2: API Widget (voor developers)

Haal evenementen op via de publieke API en render een eigen lijst op h-dcn.nl.

### API Endpoint

```
GET https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod/events-public
```

Geen authenticatie vereist.

### Query Parameters

| Parameter | Type   | Beschrijving                         | Voorbeeld    |
| --------- | ------ | ------------------------------------ | ------------ |
| `type`    | string | Filter op event_type                 | `nationaal`  |
| `regio`   | string | Filter op linked_regio               | `noord`      |
| `from`    | string | Evenementen vanaf datum (YYYY-MM-DD) | `2026-07-01` |
| `to`      | string | Evenementen tot datum (YYYY-MM-DD)   | `2026-12-31` |

### Voorbeeld Response

```json
[
  {
    "event_id": "abc123",
    "name": "Toerweekend 2026",
    "slug": "toerweekend-2026",
    "event_type": "nationaal",
    "location": "Holysloot",
    "start_date": "2026-06-15",
    "end_date": "2026-06-17",
    "poster_url": "https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/event-posters/toerweekend-2026.jpg",
    "description": "Jaarlijks toerweekend voor alle leden",
    "linked_regio": "noord",
    "participation": "open"
  }
]
```

### Beschikbare velden in response

| Veld            | Type   | Beschrijving                                      |
| --------------- | ------ | ------------------------------------------------- |
| `event_id`      | string | Unieke identifier                                 |
| `name`          | string | Evenement naam                                    |
| `slug`          | string | URL-vriendelijke naam                             |
| `event_type`    | string | Type (nationaal, internationaal, diversen, etc.)  |
| `location`      | string | Locatie                                           |
| `start_date`    | string | Startdatum (YYYY-MM-DD)                           |
| `end_date`      | string | Einddatum (YYYY-MM-DD)                            |
| `poster_url`    | string | URL naar poster afbeelding (optioneel)            |
| `description`   | string | Beschrijving (optioneel)                          |
| `landing_page`  | object | Landingspagina configuratie (optioneel)           |
| `linked_regio`  | string | Gekoppelde regio (optioneel)                      |
| `participation` | string | Deelname type (open, members_only, by_invitation) |

### HTML/JavaScript Widget Voorbeeld

```html
<!-- H-DCN Events Widget -->
<div id="hdcn-events"></div>
<script>
  fetch(
    "https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod/events-public",
  )
    .then((r) => r.json())
    .then((events) => {
      const container = document.getElementById("hdcn-events");
      events.forEach((event) => {
        const card = document.createElement("div");
        card.className = "hdcn-event-card";
        card.innerHTML = `
          <a href="https://portal.h-dcn.nl/events/${event.slug}/info">
            ${event.poster_url ? `<img src="${event.poster_url}" alt="${event.name}" style="max-width:200px">` : ""}
            <h3>${event.name}</h3>
            <p>${event.start_date} — ${event.location || ""}</p>
          </a>
        `;
        container.appendChild(card);
      });
    })
    .catch((err) => console.error("Fout bij ophalen evenementen:", err));
</script>
```

### CORS Status

> **Let op:** De API is momenteel geconfigureerd met `Access-Control-Allow-Origin: https://portal.h-dcn.nl` (alleen het portal domein). Cross-origin requests vanuit `https://h-dcn.nl` of `https://www.h-dcn.nl` worden geblokkeerd door de browser.

**Om de API widget te laten werken vanuit h-dcn.nl, is een CORS-aanpassing nodig:**

De `CORS_ALLOWED_ORIGIN` configuratie in `backend/template.yaml` moet worden aangepast. Twee opties:

1. **Wildcard (eenvoudig):** Zet `CorsOrigin` op `*` — staat alle origins toe. Acceptabel voor deze endpoint omdat het geen auth/credentials vereist.

2. **Multi-origin (preciezer):** Pas de `cors_headers()` functie aan in `backend/layers/auth-layer/python/shared/auth_utils.py` om meerdere origins te ondersteunen op basis van de `Origin` header:

```python
ALLOWED_ORIGINS = [
    'https://portal.h-dcn.nl',
    'https://h-dcn.nl',
    'https://www.h-dcn.nl',
]

def cors_headers(event_headers=None):
    origin = (event_headers or {}).get('origin', '')
    allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allowed,
        # ... overige headers
    }
```

> **Advies:** Zolang de widget-benadering niet actief wordt gebruikt, is Optie 1 (direct link) voldoende en is geen CORS-wijziging nodig.

---

## Optie 3: Iframe Embed (fallback)

Embed de kalender als iframe op h-dcn.nl. Geen CORS-problemen (de pagina wordt in z'n geheel geladen).

```html
<iframe
  src="https://portal.h-dcn.nl/events/calendar"
  width="100%"
  height="800"
  frameborder="0"
  title="H-DCN Evenementenkalender"
  style="border: none;"
>
</iframe>
```

### Overwegingen

- ✅ Geen CORS-configuratie nodig
- ✅ Volledige functionaliteit (filters, klikbare kaarten)
- ❌ Geen controle over styling (portal styling wordt getoond)
- ❌ Scrollgedrag kan onprettig zijn
- ❌ Niet SEO-vriendelijk voor h-dcn.nl

---

## Aanbeveling

| Scenario                                     | Aanbevolen aanpak |
| -------------------------------------------- | ----------------- |
| Standaard integratie                         | Optie 1 (link)    |
| Custom styling gewenst op h-dcn.nl           | Optie 2 (widget)  |
| Snelle integratie zonder backend-wijzigingen | Optie 3 (iframe)  |

Voor de meeste situaties is **Optie 1 (direct link)** de beste keuze: zero maintenance, altijd actueel, en de portal biedt al een volledig responsive kalender met social media sharing.
