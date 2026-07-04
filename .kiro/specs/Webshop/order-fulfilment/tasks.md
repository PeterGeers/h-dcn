# Webshop Order Fulfilment — Tasks

## Fase 1: Data & Backend (Quick Wins)

- [x] 1.1 **submit_order: klantgegevens + verzendadres opslaan**
  - Fetch member record (voornaam, tussenvoegsel, achternaam, email, telefoon, straat, postcode, woonplaats, land)
  - Bouw `customer_name` (voornaam + tussenvoegsel + achternaam)
  - Kopieer `shipping_address` map
  - Lees `delivery_option` en `delivery_cost` uit request body
  - Herbereken `total_amount` inclusief delivery_cost
  - Sla op als onderdeel van de submit update

- [x] 1.2 **Mollie webhook: total_paid synchronisatie fixen**
  - Bij `paid` status: update `total_paid` op order record
  - Bij `paid` status: update `payment_status` → 'paid'
  - Bij `failed`/`expired`: update `payment_status` → 'payment_failed'
  - Verifieer dat de bestaande `_handle_presmeet_payment` flow dit correct doet

- [x] 1.3 **Order Field Registry uitbreiden met shipping groep**
  - Nieuw bestand: `frontend/src/config/orderFields/fields/shippingFields.ts`
  - Velden: customer_name, customer_email, customer_phone, shipping_address, delivery_option, delivery_cost, tracking_number, shipping_carrier, shipped_at
  - FieldGroup type uitbreiden in types.ts
  - Re-exporteren vanuit fields/index.ts

- [x] 1.4 **Frontend: klant-kolom vullen in OrdersTab en PaymentsTab**
  - OrdersTab: toon `order.customer_name` (fallback: `order.user_email`)
  - PaymentsTab: toon `order.customer_name`
  - PaymentsTab: toon correct `total_paid` (niet 0)
  - PaymentsTab: klikbare order_id → opent OrderDetailDrawer

- [x] 1.5 **CheckoutModal: delivery_option en delivery_cost meesturen bij submit**
  - submitOrder aanpassen om delivery info mee te geven
  - Backend submit_order: accepteer delivery_option en delivery_cost uit body

## Fase 2: Status Machine & Admin UI

- [x] 2.1 **Backend: update_order_status herschrijven met transitie-validatie**
  - Implementeer VALID_TRANSITIONS dict (webshop + event flows)
  - Valideer current → target transitie
  - Valideer actor (admin/customer/system)
  - Valideer precondities (shipped vereist tracking_number)
  - Append status_history entry bij elke transitie
  - Set timestamps (shipped_at bij shipped, picked_up_at bij picked_up)
  - Return 400 bij ongeldige transitie met duidelijke foutmelding

- [x] 2.2 **OrderDetailDrawer uitbreiden**
  - Sectie: Klant & Verzending (naam, email, telefoon, adres)
  - Sectie: Verzendinfo (tracking_number input, carrier select, shipped_at) — webshop
  - Sectie: Afhaalinfo (pickup_location, picked_up_at, picked_up_by) — event
  - Sectie: Documenten (download knoppen placeholder)
  - "Volgende status" knop toont alleen geldige transities (context-aware per source_id)
  - Bij transitie naar "shipped": modal met tracking_number + carrier input
  - Bij transitie naar "picked_up": bevestigingsknop

- [x] 2.3 **OrdersTab migreren naar Table Filter Framework**
  - Gebruik `useFilterableTable` hook (filter → sort pipeline)
  - `FilterableHeader` op alle kolommen (tekst filter + sort)
  - `FilterPanel` boven de tabel met `GenericFilter` dropdowns voor:
    - Order status (submitted, order_received, picked, packed, shipped, etc.)
    - Payment status (unpaid, partial, paid)
    - Source (Webshop / per event)
  - Sorteerbaar op: datum, totaalbedrag, status
  - Vervang huidige statische tabel

- [x] 2.4 **Fulfilment workflow knoppen in OrderDetailDrawer (niet in tabelrij)**
  - Alle acties op een order zitten in de modal/drawer (niet inline in de tabelrij)
  - Context-aware actieknoppen afhankelijk van huidige status + source_id
  - Visuele scheiding in de tabel: "Te verwerken" vs "Afgehandeld" via filtering (niet via rij-knoppen)
  - Patroon volgt ledenadministratie: klik op rij → modal met alle acties

- [x] 2.5 **Event pick-list view**
  - Filter: alle betaalde orders voor een specifiek event
  - Toon: club/deelnemer naam, producten, variant, aantal
  - Bulk actie: markeer geselecteerde als "ready_for_pickup"
  - Afhaal-check: markeer als "picked_up" bij uitreiking

## Fase 3: PDF Documenten

- [x] 3.1 **Pakbon PDF endpoint**
  - `GET /orders/{id}/packing-slip`
  - WeasyPrint template: header, verzendadres of afhaallocatie + clubnaam (op basis van delivery_option), productlijst (naam, variant, qty), leveroptie
  - Geen prijzen op pakbon
  - Checkbox-kolom voor pick-verificatie
  - Event pakbon: clubnaam/deelnemernaam prominent (registry_row_label of customer_name)
  - i18n (8 talen)

- [x] 3.2 **Adressticker/Verzendlabel PDF endpoint**
  - `GET /orders/{id}/shipping-label`
  - Formaat: 10×15cm (standaard verzendlabel)
  - Klantnaam, volledig adres, ordernummer als referentie
  - Beschikbaar voor alle orders (ongeacht leveroptie)

- [x] 3.3 **Orderbevestiging PDF verbeteren**
  - Verzendadres toevoegen (naast bestaande klantinfo)
  - Verzendkosten als aparte regel
  - Subtotaal + verzendkosten + totaal layout
  - Bij ophaal-leveroptie: leveroptie naam tonen in plaats van verzendadres

- [x] 3.4 **Download knoppen in OrderDetailDrawer**
  - Knop: "Download Orderbevestiging"
  - Knop: "Download Pakbon"
  - Knop: "Download Verzendlabel"
  - Loading states + error handling

## Fase 4: Batch Operaties & Polish

- [x] 4.1 **Batch status update endpoint**
  - `POST /admin/orders/batch-status`
  - Accepteert array van order_ids + target_status
  - Valideert elke order individueel
  - Retourneert per-order success/failure

- [x] 4.2 **Batch PDF download**
  - `POST /admin/orders/batch-pdf`
  - Accepteert order_ids + document_type (packing_slip/shipping_label)
  - Genereert één PDF met alle documenten (één per pagina)
  - Event batch: alle pakbonnen voor één event in één PDF

- [x] 4.3 **Multi-select in OrdersTab**
  - Checkboxes per rij
  - Bulk-actie toolbar: "Markeer als [status]", "Download pakbonnen", "Download labels"
  - Select all / deselect all
  - Event-specifiek: "Alle betaalde orders voor [event] klaarzetten"

- [x] 4.4 **Klant "Mijn bestellingen" verbeteren**
  - Status tonen met StatusBadge
  - Tracking nummer tonen bij shipped/delivered
  - Orderbevestiging PDF download knop

## Opruimtaken (kleine fixes)

- [ ] 5.1 **H-dcn omgeving: alle tabel weergaven migreren naar Table Filter Framework**
  - Inventariseer alle tabellen van de h-dcn app en in welke modules die tabellen getoond worden.
  - Alle geidentificeerde tabelweergaven in de h-dcn app consistent maken
  - Geen dubbele knoppen. Verwijder losse filter-knoppen/selectors boven tabellen (regio, status, etc.)
  - Vervang door `FilterPanel` + `GenericFilter` dropdowns (enum/categorie velden)
  - Voeg `FilterableHeader` toe op alle kolommen (inline tekst filter + sort)
  - Patroon: acties in modal (klik op rij), niet in de tabelrij
  - Resultaat: één consistent filter-patroon door de hele h-dcn app
