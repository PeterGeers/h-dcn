# Requirements Document

## Introduction

Dit document beschrijft de vereisten voor het aanpassen van de `render_order_html()` functie in de backend PDF-generator zodat de gegenereerde PDF visueel overeenkomt met de frontend `OrderConfirmation.tsx` layout en styling.

## Glossary

- **PDF_Generator**: De `render_order_html()` functie en bijbehorende helperfuncties in `backend/handler/generate_order_pdf/app.py`
- **WeasyPrint**: De Python-library die HTML omzet naar PDF, met beperkte CSS-ondersteuning
- **Factuuradres**: Het adres van de klant voor facturering (customer_info)
- **Verzendadres**: Het afleveradres voor de bestelling (shipping_address)
- **Order**: Een DynamoDB-record met bestelgegevens inclusief items, bedragen en klantinformatie

## Requirements

### Requirement 1: Kleurenschema wijzigen naar oranje branding

**User Story:** Als klant wil ik dat de PDF dezelfde oranje H-DCN branding heeft als de website, zodat er visuele consistentie is tussen online en offline documenten.

#### Acceptance Criteria

1. THE PDF_Generator SHALL de kleur #FF6B35 gebruiken voor de "H-DCN Webshop" titel
2. THE PDF_Generator SHALL GEEN verwijzingen naar de kleur #2c3e50 bevatten in de gegenereerde HTML

### Requirement 2: Header layout met logo en ordergegevens

**User Story:** Als klant wil ik een duidelijke header met het H-DCN logo, de winkelnaam en mijn ordergegevens, zodat ik direct kan zien wat het document is.

#### Acceptance Criteria

1. WHEN een logo_data_uri beschikbaar is, THE PDF_Generator SHALL het logo tonen naast de titeltekst
2. THE PDF_Generator SHALL de tekst "H-DCN Webshop" tonen als hoofdtitel en "Orderbevestiging" als ondertitel
3. THE PDF_Generator SHALL ordernummer, datum, klantnaam en status "Betaald" tonen in de ordergegevens sectie
4. THE PDF_Generator SHALL de status "Betaald" in het groen (#22C55E) weergeven

### Requirement 3: Twee-kolom adres layout

**User Story:** Als klant wil ik mijn factuuradres en verzendadres naast elkaar zien in de PDF, zodat ik beide adressen snel kan controleren.

#### Acceptance Criteria

1. THE PDF_Generator SHALL een "Factuuradres" kolom en een "Verzendadres" kolom naast elkaar tonen
2. WHEN een shipping_address aanwezig is in de order, THE PDF_Generator SHALL het verzendadres uit shipping_address gebruiken
3. WHEN geen shipping_address aanwezig is, THE PDF_Generator SHALL het customer_info adres als verzendadres tonen (fallback)
4. THE PDF_Generator SHALL WeasyPrint-compatibele CSS gebruiken voor de twee-kolom layout (geen onondersteunde flexbox)

### Requirement 4: Producttabel styling

**User Story:** Als klant wil ik een overzichtelijke producttabel met lichte kleuren en goed uitgelijnde kolommen, zodat ik mijn bestelling makkelijk kan lezen.

#### Acceptance Criteria

1. THE PDF_Generator SHALL de tabelheader een achtergrondkleur van #F9FAFB (lichtgrijs) geven
2. THE PDF_Generator SHALL de tabelheader tekst in zwart/donker weergeven met bold font-weight
3. THE PDF_Generator SHALL de kolommen Aantal, Prijs en Totaal rechts uitlijnen (text-align: right)
4. THE PDF_Generator SHALL elke tabelrij een border-bottom van #E5E7EB geven

### Requirement 5: Totalen sectie met "Totaal betaald"

**User Story:** Als klant wil ik een duidelijk eindtotaal zien dat opvalt door grootte en gewicht, zodat ik direct weet wat ik betaald heb.

#### Acceptance Criteria

1. THE PDF_Generator SHALL "Totaal betaald:" weergeven met font-size 18px en font-weight bold
2. THE PDF_Generator SHALL alle bedragen formatteren met euroteken en twee decimalen (€X.XX)
3. WHEN verzendkosten aanwezig zijn, THE PDF_Generator SHALL een aparte regel voor verzendkosten tonen tussen subtotaal en eindtotaal

### Requirement 6: Leveringssectie positie

**User Story:** Als klant wil ik de leveringsmethode boven de producttabel zien, zodat ik direct weet hoe mijn bestelling wordt verzonden voordat ik de productdetails bekijk.

#### Acceptance Criteria

1. WHEN een delivery_option aanwezig is, THE PDF_Generator SHALL de leveringssectie BOVEN de producttabel plaatsen
2. THE PDF_Generator SHALL het delivery_option label en de verzendkosten tonen in de leveringssectie

### Requirement 7: WeasyPrint-compatibele CSS

**User Story:** Als ontwikkelaar wil ik dat de HTML-template correct rendert in WeasyPrint, zodat de PDF er goed uitziet zonder rendering-fouten.

#### Acceptance Criteria

1. THE PDF_Generator SHALL geen CSS flexbox met `display: flex` en `justify-content` gebruiken voor layout-elementen die door WeasyPrint niet volledig ondersteund worden
2. THE PDF_Generator SHALL `float`, `display: inline-block` of `table` layout gebruiken voor twee-kolom structuren
3. THE PDF_Generator SHALL een `@page` directive bevatten met A4 formaat en 20mm marges

### Requirement 8: Klantnaam fallback logica

**User Story:** Als systeem wil ik altijd een klantnaam kunnen tonen, ook als het `name` veld ontbreekt, zodat de PDF nooit een lege naam toont.

#### Acceptance Criteria

1. WHEN customer_info een `name` veld bevat, THE PDF_Generator SHALL dat als klantnaam gebruiken
2. WHEN customer_info geen `name` veld bevat maar wel `voornaam` en `achternaam`, THE PDF_Generator SHALL deze combineren tot een volledige naam
3. WHEN geen naam beschikbaar is, THE PDF_Generator SHALL "Niet beschikbaar" tonen als klantnaam

### Requirement 9: Productnaam fallback logica

**User Story:** Als systeem wil ik zowel het `name` als `naam` veld ondersteunen voor productnamen, zodat bestaande en nieuwe orders correct worden weergegeven.

#### Acceptance Criteria

1. WHEN een item een `name` veld heeft, THE PDF_Generator SHALL dat als productnaam gebruiken
2. WHEN een item geen `name` veld heeft maar wel `naam`, THE PDF_Generator SHALL dat als productnaam gebruiken
3. WHEN een item geen `selectedOption` heeft, THE PDF_Generator SHALL "-" tonen in de Optie kolom
