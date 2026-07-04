# Webshop Order Fulfilment — Requirements

## Context

De webshop betaalflow werkt (Mollie sandbox actief), maar na betaling ontbreekt het hele fulfilment-traject: er is geen klantinfo bij de order, geen verzendkosten-tracking, geen pakbonnen, geen verzendlabels, en de admin kan orders niet effectief verwerken. Dit spec definieert het volledige traject van betaling tot levering.

## Overzicht huidige staat

### Wat werkt

- Order aanmaken (draft) → submit → betalen via Mollie
- Status badges voor alle 14 statussen (gedefinieerd in Field Registry)
- OrderDetailDrawer met "Next Status" knop
- PDF generatie (basis: WeasyPrint, i18n, logo)
- Betaling registreren (admin)

### Wat ontbreekt

- Klantgegevens worden niet opgeslagen bij de order
- Verzendkosten worden niet naar backend gestuurd
- Betaald bedrag (total_paid) wordt niet bijgewerkt door Mollie webhook
- Geen verzendadres / afleveradres bij order
- Geen pakbon, verzendlabel, adressticker PDF's
- Geen fulfilment-specifieke UI (pick → pack → ship workflow)
- Geen status-transitie validatie in backend
- Geen statusgeschiedenis-opbouw (status_history)
- Geen notificaties bij statuswijzigingen

---

## Requirements

### 1. Order Data Completeness

**1.1** Bij het submitten van een order MOET het systeem de volgende klantgegevens opslaan op de order (gekopieerd uit het Members record):

- `customer_name` (voornaam + tussenvoegsel + achternaam)
- `customer_email`
- `customer_phone` (optioneel)

**1.2** Bij het submitten MOET het systeem het afleveradres opslaan als `shipping_address` map op de order. Het afleveradres wordt door de klant bevestigd of aangepast in de checkout (pre-filled vanuit het Member record, maar overschrijfbaar per order):

- `naam` (ontvanger naam — default: customer_name)
- `straat` (straat + huisnummer)
- `postcode`
- `woonplaats`
- `land`

Het Member record wordt NIET gewijzigd — het afleveradres is een snapshot per order.

**1.3** Verzendkosten (`delivery_cost`) en gekozen leveroptie (`delivery_option`) MOETEN door de frontend meegegeven worden bij het submitten en opgeslagen worden op de order.

**1.4** `total_amount` MOET inclusief verzendkosten berekend worden: `sum(item.line_total) + delivery_cost`.

**1.5** Het veld `source_id` MOET aanwezig zijn op elke order (`'webshop'` voor webshop orders, event UUID voor event orders).

**1.6** Bij het opslaan van items (`update_order_items`) MOET de productnaam (`name`) en eventueel `product_type` worden gedenormaliseerd en opgeslagen per item. Dit zodat orders altijd leesbaar zijn, ook als het product later wordt verwijderd of hernoemd.

**1.7** De productnaam wordt opgehaald uit de Producten tabel (veld `naam`) en opgeslagen als `name` op elk item in de order.

---

### 2. Leveropties (Configureerbaar)

**2.1** Leveropties worden op twee niveaus geconfigureerd:

- **Globaal**: Parameters tabel (key: `leveropties`) — geldt als fallback voor alle orders
- **Per event**: optioneel veld `delivery_options` op het Event record — overschrijft de globale opties wanneer gevuld

**2.2** Bij het laden van leveropties bepaalt de frontend welke opties gelden:

- Webshop order (geen event context) → laad globale leveropties uit Parameters
- Event order → laad `event.delivery_options` als die gevuld is, anders globale leveropties

**2.3** Het formaat van leveropties is uniform (zowel globaal als per event):

```json
[
  { "name": "Verzenden (PostNL)", "cost": "6.95" },
  { "name": "Afhalen op locatie", "cost": "0.00" }
]
```

**2.4** De admin MOET per event leveropties kunnen configureren in het Event formulier (Configuratie sectie). Een leeg veld betekent: gebruik de globale opties.

**2.5** Er MOET altijd minimaal één leveroptie beschikbaar zijn (validatie bij submit).

---

### 3. Betaalstatus Synchronisatie

**2.1** De Mollie webhook MOET bij status `'paid'` het veld `total_paid` op de order bijwerken naar het betaalde bedrag.

**2.2** De Mollie webhook MOET bij status `'paid'` het veld `payment_status` updaten naar `'paid'` (als total_paid >= total_amount).

**2.3** De Mollie webhook MOET bij status `'failed'` of `'expired'` het veld `payment_status` updaten naar `'unpaid'` of `'payment_failed'`.

**2.4** Het admin Betalingen-tabblad MOET het correcte `total_paid` tonen (niet 0).

---

### 3. Order Field Registry Uitbreiding

**3.1** Nieuwe velden toevoegen aan de Order Field Registry (groep: `'shipping'`):

- `customer_name` (string, read-only)
- `customer_email` (string, read-only)
- `customer_phone` (string, optioneel, read-only)
- `shipping_address` (map: straat, postcode, woonplaats, land)
- `delivery_option` (string: gekozen leveroptie label)
- `delivery_cost` (number: verzendkosten in EUR)
- `tracking_number` (string, admin-editable)
- `shipping_carrier` (enum: PostNL/DHL/DPD/Anders, admin-editable)
- `shipped_at` (datetime, auto-set bij transitie naar 'shipped')

**3.2** Het veld `customer_name` MOET getoond worden in de kolom "Klant/Club" in de OrdersTab en PaymentsTab.

---

### 4. Status Transitie Model

**4.1** De backend MOET een status-transitie validatie implementeren. Toegestane transities:

```
draft → submitted (door lid, bij submit)
submitted → paid (automatisch, bij Mollie webhook)
submitted → payment_failed (automatisch, bij Mollie webhook)
paid → order_received (admin)
order_received → picked (admin)
picked → packed (admin)
packed → shipped (admin, vereist tracking_number)
shipped → delivered (admin)
delivered → completed (admin)
delivered → return_requested (admin of klant)
return_requested → return_received (admin)
return_received → completed (admin)
payment_failed → submitted (retry, door lid)
```

**4.2** Bij elke transitie MOET een entry worden toegevoegd aan `status_history`:

```json
{
  "from": "paid",
  "to": "order_received",
  "at": "2026-07-01T12:00:00Z",
  "by": "admin@h-dcn.nl",
  "source": "admin"
}
```

**4.3** De transitie naar `'shipped'` MOET geweigerd worden als `tracking_number` leeg is.

**4.4** De transitie naar `'paid'` MAG alleen door het systeem (Mollie webhook of admin_record_payment), niet handmatig via update_order_status.

---

### 5. Admin Order Management UI

**5.1** De Bestellingen-tab MOET de kolom "Klant/Club" vullen met `customer_name` uit de order.

**5.2** De Betalingen-tab MOET het correcte betaalde bedrag tonen en een klikbare link naar de order.

**5.3** De OrderDetailDrawer MOET de volgende secties tonen:

- Klantgegevens (naam, email, telefoon)
- Verzendadres
- Bestelregels (productnaam, variant, aantal, prijs)
- Betaalgeschiedenis
- Statusgeschiedenis
- Verzendinfo (tracking number, carrier, verzonden op)

**5.4** De OrderDetailDrawer MOET een "Volgende status" knop tonen die alleen geldige transities aanbiedt.

**5.5** Bij de transitie naar "shipped" MOET een invoerveld voor tracking_number verschijnen.

---

### 6. PDF Documenten

**6.1** **Orderbevestiging** (bestaand, verbeteren):

- Klantgegevens + verzendadres
- Bestelregels met variant-info
- Subtotaal + verzendkosten + totaal
- Ordernummer + besteldatum
- Download beschikbaar voor klant en admin

**6.2** **Pakbon** (nieuw):

- Ordernummer + datum
- Verzendadres prominent
- Producten met variant (maat/kleur) + aantal
- Geen prijzen (alleen producten + aantallen)
- Checkbox-kolom voor pick-verificatie

**6.3** **Verzendlabel / Adressticker** (nieuw):

- Naam + volledig adres
- Ordernummer als referentie
- Formaat: A6 of standaard label (10x15cm)

**6.4** **Factuur** (nieuw, optioneel fase 2):

- Factuurnummer (uit Counters table)
- Klantgegevens + verzendadres
- Regels met BTW-berekening
- H-DCN organisatiegegevens

**6.5** Alle PDF's MOETEN downloadbaar zijn vanuit de OrderDetailDrawer.

**6.6** Batch-download: admin MOET meerdere pakbonnen/labels tegelijk kunnen downloaden voor geselecteerde orders.

---

### 7. Admin Workflow (Pick → Pack → Ship)

**7.1** De Bestellingen-tab MOET filterbaar zijn op status (bijv. "Alle betaalde orders", "Klaar om te verzenden").

**7.2** De admin MOET vanuit de ordertabel in één klik de status naar "picked" kunnen zetten (voor betaalde orders).

**7.3** Bij het verpakken (packed → shipped) MOET tracking info ingevuld worden.

**7.4** Batch-operaties: admin MOET meerdere orders tegelijk naar de volgende status kunnen zetten.

---

### 8. Klant Zichtbaarheid

**8.1** De klant MOET op de "Mijn bestellingen" pagina de huidige status van de order zien.

**8.2** Bij status "shipped" MOET het tracking nummer getoond worden (indien beschikbaar).

**8.3** De klant MOET de orderbevestiging PDF kunnen downloaden.

---

### 9. Event Order Fulfilment (Afhalen op locatie)

**9.1** Event orders (source_id = event UUID) volgen een afwijkende fulfilment flow: er is geen verzending maar **afhalen op locatie** tijdens het event.

**9.2** De fulfilment status flow voor event orders:

```
draft → submitted → locked → paid → ready_for_pickup → picked_up → completed
```

**9.3** Bij event orders is `shipping_address` NIET verplicht. In plaats daarvan wordt `pickup_location` opgeslagen (uit het event record: `location` veld).

**9.4** De admin MOET per event een overzicht krijgen van alle betaalde orders die klaargemaakt moeten worden voor afhaling ("Pick list per event").

**9.5** De admin MOET bij een event orders kunnen afvinken als "uitgereikt" (status → `picked_up`).

**9.6** De pakbon voor event orders MOET de club/deelnemer naam prominent tonen (uit `registry_row_label` of `customer_name`), zodat de juiste bestelling aan de juiste persoon wordt uitgereikt.

**9.7** Event pakbonnen MOETEN groepeerbaar zijn per event (batch download per event).

**9.8** De leveroptie voor event orders is altijd "Afhalen op locatie" — dit hoeft niet door de klant gekozen te worden.

**9.9** `delivery_cost` is 0 voor event orders (afhalen is gratis).

---

### 10. Unified Fulfilment UI

**10.1** De admin order-management UI MOET beide flows (webshop + event) in dezelfde interface tonen, met een filter op source (webshop / specifiek event).

**10.2** De status badges en "Next Status" actie MOETEN context-aware zijn: webshop orders tonen verzend-acties, event orders tonen afhaal-acties.

**10.3** De OrderDetailDrawer MOET bij event orders "Afhaallocatie" tonen in plaats van "Verzendadres".

**10.4** Batch operaties MOETEN werken over zowel webshop als event orders (bijv. "alle betaalde orders voor Event X markeren als ready_for_pickup").

---

## Niet in scope

- Automatische e-mail notificaties bij statuswijzigingen (toekomstige spec)
- Retour-verwerking workflow (alleen status, geen refund-logica)
- Voorraadbeheer koppeling bij ship (stock_reservation draait al bij betaling)
