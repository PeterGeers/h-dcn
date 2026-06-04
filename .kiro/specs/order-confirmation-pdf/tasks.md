# Implementation Plan: Order Confirmation PDF

## Overview

Herschrijf de `render_order_html()` functie en voeg helperfuncties toe zodat de PDF-output visueel overeenkomt met de frontend `OrderConfirmation.tsx` layout. Gebruik WeasyPrint-compatibele CSS (geen flexbox) met oranje branding.

## Tasks

## Task Dependency Graph

```json
{
  "waves": [
    {
      "tasks": ["1"],
      "description": "Refactor render_order_html met helperfuncties"
    },
    { "tasks": ["2"], "description": "Checkpoint - handmatig verifiëren" },
    { "tasks": ["3"], "description": "Tests schrijven" },
    { "tasks": ["4"], "description": "Eindcontrole" }
  ]
}
```

- [x] 1. Refactor render_order_html() met helperfuncties
  - [x] 1.1 Voeg `build_css()` functie toe die de nieuwe styling retourneert
    - Oranje branding (#FF6B35) voor titel, lichtgrijze headers (#F9FAFB)
    - Twee-kolom layout via `display: inline-block` (geen flexbox)
    - @page A4 met 20mm marges, Arial font
    - Rechts-uitgelijnde numerieke kolommen via `.right` class
    - "Totaal betaald" als 18px bold
    - _Requirements: 1.1, 1.2, 4.1, 4.3, 5.1, 7.1, 7.2, 7.3_

  - [x] 1.2 Voeg `build_header_html()` functie toe
    - Logo naast "H-DCN Webshop" titel (#FF6B35) en "Orderbevestiging" ondertitel
    - Order-meta blok: ordernummer, datum, klant, status "Betaald" (groen #22C55E)
    - Klantnaam fallback: name → voornaam+achternaam → "Niet beschikbaar"
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 8.1, 8.2, 8.3_

  - [x] 1.3 Voeg `build_addresses_html()` functie toe
    - Twee kolommen: Factuuradres (links) + Verzendadres (rechts)
    - Verzendadres fallback naar customer_info als shipping_address ontbreekt
    - Gebruik `display: inline-block; width: 48%` voor WeasyPrint-compatibiliteit
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 1.4 Voeg `build_products_table_html()` functie toe
    - Leveringssectie (indien aanwezig) BOVEN de producttabel
    - Tabelheader: lichtgrijs (#F9FAFB), bold, niet-uppercase
    - Kolommen: Product, Optie (links), Aantal, Prijs, Totaal (rechts)
    - Productnaam fallback: name → naam
    - selectedOption fallback naar "-"
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 6.1, 6.2, 9.1, 9.2, 9.3_

  - [x] 1.5 Voeg `build_totals_html()` functie toe
    - Subtotaal, optioneel verzendkosten, scheidingslijn, "Totaal betaald:" (18px bold)
    - Alle bedragen in €X.XX formaat
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 1.6 Herschrijf `render_order_html()` als assemblagefunctie
    - Extraheert data uit order dict
    - Roept helperfuncties aan voor elke sectie
    - Assembleert HTML document met CSS, header, adressen, producten, totalen
    - Verwijder alle oude #2c3e50 styling en donkerblauwe thema-code
    - _Requirements: 1.1, 1.2_

- [x] 2. Checkpoint - Handmatig verifiëren
  - Controleer dat de bestaande `lambda_handler` nog correct werkt met de nieuwe `render_order_html()`
  - 21/22 tests pass (1 pre-existing auth test failure, onrelated to our changes)

- [x] 3. Tests schrijven
  - [x]\* 3.1 Property test: branding en afwezigheid oud kleurenschema
    - **Property 2: Oranje branding en afwezigheid oud kleurenschema**
    - **Validates: Requirements 1.1, 1.2**

  - [x]\* 3.2 Property test: twee-kolom adres layout
    - **Property 3: Twee-kolom adres layout**
    - **Validates: Requirements 3.1**

  - [x]\* 3.3 Property test: tabel header styling en uitlijning
    - **Property 4: Tabel header styling en uitlijning**
    - **Validates: Requirements 4.1, 4.3**

  - [x]\* 3.4 Property test: totaal betaald presentatie
    - **Property 5: Totaal betaald presentatie**
    - **Validates: Requirements 5.1**

  - [x]\* 3.5 Property test: leveringssectie positie
    - **Property 6: Leveringssectie positie**
    - **Validates: Requirements 6.1**

  - [x]\* 3.6 Property test: bedragen formattering
    - **Property 7: Bedragen correct geformateerd**
    - **Validates: Requirements 5.2**

  - [x]\* 3.7 Property test: klantnaam resolutie
    - **Property 8: Klantnaam resolutie**
    - **Validates: Requirements 8.1, 8.2**

  - [x]\* 3.8 Property test: WeasyPrint CSS compatibiliteit
    - **Property 9: WeasyPrint CSS compatibiliteit**
    - **Validates: Requirements 7.1, 7.3**

  - [x]\* 3.9 Unit tests voor edge cases
    - Lege order (geen items, geen customer_info)
    - Order zonder logo_data_uri
    - Item met `naam` i.p.v. `name`
    - Item zonder selectedOption
    - Klantnaam fallback (geen name, wel voornaam+achternaam)
    - _Requirements: 8.3, 9.2, 9.3_

- [x] 4. Eindcontrole
  - 31/31 tests pass (excluding 1 pre-existing unrelated auth test)

## Notes

- Tasks gemarkeerd met `*` zijn optioneel en kunnen overgeslagen worden voor een snellere MVP
- Property tests gebruiken `hypothesis` (al aanwezig in het project)
- Testbestand: `backend/tests/unit/test_generate_order_pdf.py`
- De `lambda_handler` en `fetch_logo_as_data_uri` functies worden NIET aangepast
