# Screenshots voor de evenementen-handleidingen

Deze map bevat de afbeeldingen (screenshots) die in de evenementen-handleidingen
worden gebruikt. In de Markdown-bronnen staan op de juiste plekken
**placeholders** met een vaste bestandsnaam. Plaats hier een afbeelding met
exact die naam en render opnieuw; de screenshot verschijnt dan automatisch in de
HTML/PDF (het renderscript vervangt de placeholder door de afbeelding als het
bestand bestaat).

## Hoe werkt het

In de handleidingen staan placeholders in dit formaat:

```
> 📷 **[Screenshot: korte omschrijving]** — bestand: `assets/evenement-landing.png`
```

Plaats een PNG met die naam in deze map en draai:

```bash
node scripts/docs/render-manuals.mjs
```

Zolang een bestand ontbreekt, toont de HTML/PDF een net grijs placeholder-kader.

## Aanbevelingen

- **Formaat:** PNG (scherpe UI-tekst). Breedte ± 1200–1600 px is ruim voldoende.
- **Inhoud:** toon alleen het relevante schermdeel; vermijd persoonsgegevens van
  echte leden (gebruik testdata of maak gevoelige gegevens onleesbaar).
- **Taal:** maak de screenshots in de Nederlandse weergave van de portal.

## Verwachte bestandsnamen

### Ledenhandleiding (`handleiding-evenementen.md`)

| Bestandsnaam                       | Wat het toont                                        |
| ---------------------------------- | ---------------------------------------------------- |
| `evenement-landing.png`            | Evenement-landingspagina met poster en CTA-knop      |
| `evenement-wachtwoord.png`         | Wachtwoordscherm van een evenement                   |
| `evenement-inloggen.png`           | Inloggen/aanmelden met evenementcontext              |
| `evenement-clubselectie.png`       | Clublijst met beschikbaar/bezet                      |
| `evenement-claim.png`              | Registratie voltooien / claim-scherm                 |
| `evenement-booking.png`            | Bookingpagina met personen en gekozen onderdelen     |
| `evenement-ingediend.png`          | Bevestiging na indienen van de booking               |
| `evenement-betaling.png`           | Betaalpaneel met totaal/betaald/openstaand           |
| `evenement-delegate.png`           | Mede-delegate uitnodigen                             |
| `evenement-pdf.png`                | Knop om bookingsamenvatting (PDF) te downloaden      |
| `evenement-foutmelding.png`        | Voorbeeld van een validatie-/foutmelding             |

### Beheerdershandleiding (`handleiding-evenementen-beheer.md`)

| Bestandsnaam                          | Wat het toont                                     |
| ------------------------------------- | ------------------------------------------------- |
| `beheer-evenementen-overzicht.png`    | Evenementenadministratie met de tabbladen         |
| `beheer-evenementen-lijst.png`        | Evenementenlijst met filters en statuskolom       |
| `beheer-evenement-formulier.png`      | Formulier Evenement bewerken (uitklapbare secties)|
| `beheer-evenement-financien.png`      | Tabblad Financiën of Analytics                    |
| `beheer-toegangsbeheer.png`           | Toegangsbeheer met ledenlijst                     |
| `beheer-event-dashboard.png`          | Event Dashboard met voortgang en betalingen       |
| `beheer-rapporten.png`                | Rapportknoppen en snelle filters                  |
| `beheer-vergrendelen.png`             | Bookings vergrendelen/ontgrendelen                |
| `beheer-handmatige-betaling.png`      | Handmatige betaling registreren                   |
| `beheer-voorbereiding-pdf.png`        | Voorbereidings-PDF met modus en productfilter     |
| `beheer-claimbeheer.png`              | Claimbeheer met rijen, status en acties           |
| `beheer-producten-koppelen.png`       | Producten koppelen in het evenementformulier      |
