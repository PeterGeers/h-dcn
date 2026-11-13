# Handleiding Evenementen Beheer — voor beheerders

Deze handleiding legt uit hoe je als beheerder evenementen beheert: evenementen
aanmaken en bewerken, toegang en claims regelen, bookings vergrendelen,
betalingen registreren en rapporten/PDF's maken. De handleiding beschrijft de
evenementenadministratie zoals die nu werkt.

> 💡 **Tip:** Het beheer bestaat uit twee delen. De **Evenementenadministratie**
> (`/events`) is voor het aanmaken en inrichten van evenementen, financiën,
> analytics en toegangsbeheer. Het **Event Dashboard** is de operationele kant:
> voortgang, bookings vergrendelen/ontgrendelen, claims, handmatige betalingen en
> voorbereidings-PDF's.

---

## 1. Toegang en rollen

Of je bij het evenementbeheer kunt en wat je mag, hangt af van je rollen. De
belangrijkste rollen:

| Rol-categorie        | Voorbeelden van rollen                                                                 | Wat je ermee kunt                          |
| -------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------ |
| **Lezen**            | `Events_Read`, `Events_CRUD`, `Events_Export`, `Regio_All`, regionale bestuursrollen   | Evenementen bekijken                        |
| **Bewerken**         | `Events_CRUD`, `Webmaster`, `Tour_Commissioner`, `Regional_Chairman_*`                  | Evenementen aanmaken/bewerken               |
| **Financieel**       | `Events_CRUD`, `National_Treasurer`, `Regional_Treasurer_*`, e.a.                       | Financiële gegevens zien/bewerken           |
| **Volledige toegang**| `Events_CRUD`, `Webmaster`, `Tour_Commissioner`, `System_User_Management`               | Alles, inclusief **Toegangsbeheer**         |
| **Exporteren**       | `Events_CRUD`, `Events_Export`, `National_Secretary`, `Regional_Secretary_*`, e.a.      | Deelnemerslijsten/rapporten exporteren      |

Heb je geen leesrecht, dan zie je een melding met je huidige rollen en de
vereiste rollen. Veel regionale rollen (zoals `Regional_Chairman_*`) geven
toegang tot evenementen binnen de eigen regio.

> 📷 **[Screenshot: Evenementenadministratie met de tabbladen]** — bestand: `assets/beheer-evenementen-overzicht.png`

---

## 2. Evenementenadministratie (`/events`)

De pagina **Evenementenadministratie** heeft tabbladen die afhankelijk van je
rechten verschijnen:

- **Evenementen** — de lijst met evenementen (altijd zichtbaar bij leesrecht).
- **Financiën** — financieel overzicht (bij financieel recht).
- **Analytics** — analyses en overzichten (bij analytics-recht).
- **Toegangsbeheer** — toegang per evenement beheren (bij volledige toegang).

### Tabblad Evenementen

Een filterbare, sorteerbare lijst met kolommen zoals **Naam**, **Datum**,
**Locatie**, **Type**, **Deelname**, **Status** en **Regio**. De status heeft een
kleur: gepubliceerd (groen), concept (geel), gearchiveerd (grijs).

- Klik op **Nieuw Evenement** om een evenement aan te maken (bij bewerkrecht).
- Klik op een rij om een bestaand evenement te **bewerken**.
- Met de **CSV-export** download je de evenementenlijst (bij export-recht).

> 📷 **[Screenshot: evenementenlijst met filters en statuskolom]** — bestand: `assets/beheer-evenementen-lijst.png`

### Evenement aanmaken of bewerken

Het formulier **Nieuw Evenement** / **Evenement Bewerken** heeft een vast
bovendeel en een aantal uitklapbare secties:

- **Kerngegevens** (altijd zichtbaar): Eventnaam, Type, Deelname, Status, Start- en
  einddatum, Regio, Locatie, Poster, Slug en Omschrijving. Naam, type, start- en
  einddatum en regio zijn verplicht.
- **Registratie & Deadlines**: registratie-open, registratie-sluit en
  betaaldeadline.
- **Configuratie**: gekoppelde **producten** (zie "Winkel per evenement"
  hieronder), het **evenement-wachtwoord** en de **register-instellingen** (het
  label van een rij — bijvoorbeeld "club", de claim-modus, en of logo-upload is
  toegestaan).
- **Financieel** (alleen met financieel recht): deelnemers, kosten, opbrengst en
  notities.
- **Landing Page**: de inhoud van de publieke evenementpagina.

Bij een nieuw evenement kun je een **poster uploaden en laten analyseren**, zodat
een aantal velden automatisch wordt voorgesteld.

Onderaan het formulier kun je het evenement **Dupliceren**, **Verwijderen**
(met bevestiging) of je wijzigingen **Bijwerken** / **Aanmaken**.

> 📷 **[Screenshot: formulier Evenement bewerken met uitklapbare secties]** — bestand: `assets/beheer-evenement-formulier.png`

### Tabblad Financiën en Analytics

- **Financiën** toont de financiële module voor de evenementen waar je toegang toe
  hebt.
- **Analytics** toont analyses en overzichten. Beide tabbladen zijn afgeschermd op
  basis van je rollen.

> 📷 **[Screenshot: tabblad Financiën of Analytics]** — bestand: `assets/beheer-evenement-financien.png`

### Tabblad Toegangsbeheer

Met **Toegangsbeheer** (alleen bij volledige toegang) regel je wie toegang heeft
tot een evenement:

- Kies eerst een **evenement**.
- Je ziet de **leden met toegang**.
- **Toegang verlenen** doe je per e-mailadres of lid-ID; je kunt ook in bulk
  toegang verlenen of intrekken.

> 📷 **[Screenshot: Toegangsbeheer met ledenlijst en verlenen/intrekken]** — bestand: `assets/beheer-toegangsbeheer.png`

---

## 3. Event Dashboard (operationeel beheer)

Het **Event Dashboard** is het operationele hart voor een lopend evenement. Je
kiest bovenaan een **evenement** en krijgt dan:

### Registratievoortgang

Voortgangsbalken per **constraint** (bijvoorbeeld maximaal aantal deelnemers,
feesttickets, enz.) met de huidige waarde ten opzichte van het maximum, in kleur
(groen/geel/rood).

### Betalingsoverzicht

Totalen voor **Totaal gefactureerd**, **Totaal betaald** en **Openstaand**, plus
het aantal **volledig betaalde** clubs.

> 📷 **[Screenshot: Event Dashboard met voortgang en betalingsoverzicht]** — bestand: `assets/beheer-event-dashboard.png`

### Rapporten en snelle filters

Met de rapportknoppen open je rapporten zoals **Deelnemers**, **Feestgasten**,
**T-Shirts**, **Ophalen**, **Afzetten**, **Financieel** en **Overzicht**. De
**snelle filters** springen direct naar een rapport met een filter, zoals
**Concept bestellingen**, **Ingediende bestellingen**, **Vergrendelde
bestellingen**, **Onbetaalde bestellingen**, **Deels betaald** of **Volledig
betaald**. Rapporten zijn als **CSV** te downloaden.

> 📷 **[Screenshot: rapportknoppen en snelle filters]** — bestand: `assets/beheer-rapporten.png`

---

## 4. Bookings vergrendelen en ontgrendelen

Onder het dashboard staat **Bestellingen vergrendelen / ontgrendelen**. Hiermee
stuur je de bookingstatus. De statusworkflow:

- **Concept (draft)** — de deelnemer werkt nog aan de booking.
- **Ingediend (submitted)** — de booking is ingediend.
- **Vergrendeld (locked)** — vastgezet; delegates kunnen niet meer bewerken.

Acties:

- **Alle ingediende vergrendelen** — vergrendelt in bulk alle ingediende bookings.
- **Alles ontgrendelen** — zet bookings terug naar concept (delegates kunnen weer
  bewerken).
- Een enkele booking **ontgrendelen** vanuit het detailscherm.

Je kunt filteren op status (Concept / Ingediend / Vergrendeld). Bij het
vergrendelen/ontgrendelen verschijnt een bevestiging die uitlegt wat het effect
is voor delegates.

> ⚠️ **Let op:** Alleen ingediende of vergrendelde bookings kunnen worden
> ontgrendeld. Conceptbookings kunnen niet worden vergrendeld — die moeten eerst
> worden ingediend.

> 📷 **[Screenshot: bookings vergrendelen/ontgrendelen met statusfilter]** — bestand: `assets/beheer-vergrendelen.png`

---

## 5. Handmatige betaling en voorbereidings-PDF

### Handmatige betaling registreren

Met **Handmatige betaling** boek je een betaling die buiten de online betaling om
is ontvangen (bijvoorbeeld een bankoverschrijving):

- Open **Betaling registreren**.
- Vul de **Bestelling-ID**, het **Bedrag (€)**, de **Datum** en eventueel een
  **omschrijving** in.
- Bevestig met **Betaling registreren**.

> 📷 **[Screenshot: handmatige betaling registreren]** — bestand: `assets/beheer-handmatige-betaling.png`

### Voorbereidings-PDF

Met **Voorbereiding PDF** download je een logistieke PDF voor het evenement:

- Kies een **modus**: **Per bestelling** (per club) of **Per gast** (per persoon).
- Kies eventueel een **productfilter** (of alle producten).
- Klik op **Download PDF**.

Alleen **ingediende** en **vergrendelde** bookings worden meegenomen in de PDF.

> 📷 **[Screenshot: voorbereidings-PDF met modus en productfilter]** — bestand: `assets/beheer-voorbereiding-pdf.png`

---

## 6. Claimbeheer

Met **Claimbeheer** beheer je welke club/rij door welk lid is geclaimd. Je ziet
een (gepagineerde) tabel met per rij de **status** (Beschikbaar / Geclaimd / In
afwachting), de **gedelegeerde**, het **e-mailadres** en wanneer er is geclaimd.

Per rij kun je:

- **Claim vrijgeven** — de claim loslaten (de bijbehorende booking blijft bewaard).
- **Toewijzen** — een rij aan een lid koppelen op e-mailadres.
- **Primaire hertoewijzen** — een andere persoon de hoofd-delegate maken.
- **Secundaire verwijderen** — de tweede delegate verwijderen.
- **Uitnodiging annuleren** — een openstaande uitnodiging annuleren.

> 📷 **[Screenshot: Claimbeheer met rijen, status en acties]** — bestand: `assets/beheer-claimbeheer.png`

---

## 7. Winkel per evenement (producten koppelen)

Evenementen en de webwinkel delen hetzelfde bestel-/ordersysteem. Een evenement
krijgt zijn eigen **"winkel"** door er **producten** aan te koppelen:

- In het evenementformulier koppel je onder **Configuratie** één of meer
  **producten** uit de productcatalogus aan het evenement (`product_ids`).
- In de booking ziet de deelnemer precies die gekoppelde producten om per persoon
  te configureren (tickets, t-shirts, transfers, enz.).
- De bijbehorende bestellingen krijgen de **bron** van dit evenement. In het
  webwinkelbeheer (tabblad Bestellingen) zijn evenementbestellingen herkenbaar aan
  de kolom **Bron** en kun je er met de **pick-list** ter plaatse op uitgeven.

> ℹ️ **Opmerking:** Dit is hetzelfde "winkel per event"-mechanisme dat in de
> [webwinkel-beheerhandleiding](../webshop/handleiding-beheer.md) wordt beschreven.
> Het leent zich ook voor regio-winkels.

> 📷 **[Screenshot: producten koppelen in het evenementformulier]** — bestand: `assets/beheer-producten-koppelen.png`

---

## 8. Betalingen

Evenementbetalingen lopen via **Mollie** (online betalen door de deelnemer) of via
een **handmatig** door de beheerder geregistreerde betaling (zie hoofdstuk 5). De
betaalstatus van een booking is **Onbetaald**, **Deels betaald** of **Betaald**,
en is zichtbaar in het dashboard, de rapporten en op de bookingpagina van de
deelnemer.

---

*Vragen over rechten of een specifieke actie? Neem contact op met een
H-DCN-beheerder.*
