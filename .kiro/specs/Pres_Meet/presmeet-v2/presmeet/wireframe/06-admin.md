# Wireframe: Admin Pagina (admin.php)

## Beschrijving

Beheerpagina voor administrators. Biedt overzicht van alle boekingen, gebruikers, en mogelijkheid om data te beheren, emails te sturen, betalingen te verwerken en spreadsheets te downloaden.

## Layout - Desktop

```
┌─────────────────────────────────────────────────────────────────────────┐
│ NAVBAR (fixed top)                                                      │
│ [PM Logo]                              [Status]              [≡ Menu]  │
├──────────────┬──────────────────────────────────────────────────────────┤
│ SIDEBAR      │  MAIN CONTENT                                           │
│              │                                                          │
│ Menu         │  [FH-DCE Logo]    [PM 2025 Logo]                        │
│              │  PM 2025 Admin                                           │
│ ┌──────────┐ │                                                          │
│ │Instruct. │ │  This is the site admin page, select one of the         │
│ │Overview  │ │  menu options to continue.                               │
│ │Users     │ │                                                          │
│ │Bookings  │ │  (Content wordt dynamisch geladen per menu-keuze)       │
│ │Club&Cont.│ │                                                          │
│ │Delegates │ │                                                          │
│ │Guests    │ │                                                          │
│ │Rooms     │ │                                                          │
│ │Travels   │ │                                                          │
│ │Extras    │ │                                                          │
│ │Payments  │ │                                                          │
│ │Hotel Rms │ │                                                          │
│ │Downl.Sub │ │                                                          │
│ │Downl.Sav │ │                                                          │
│ │Logout    │ │                                                          │
│ └──────────┘ │                                                          │
└──────────────┴──────────────────────────────────────────────────────────┘
```

## Admin: Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  OVERVIEW                                                       │
│                                                                 │
│  USERS                          SAVED        SUBMITTED          │
│  Total users:        45         Bookings:    38    35           │
│  Active users:       42         Delegates:   72    68           │
│                                 Guests:      45    40           │
│                                 Party:       95    88           │
│                                 Single rooms: 8     7           │
│                                 Double rooms: 22    20          │
│                                 Twin rooms:   5     4           │
│                                 Arr. transfers:18   16          │
│                                 Dep. transfers:15   14          │
│                                 T-shirts:    85    80           │
│                                                                 │
│                                 Total charges: €38.500  €35.200 │
└─────────────────────────────────────────────────────────────────┘
```

## Admin: Users Tabel

```
┌─────────────────────────────────────────────────────────────────┐
│  USERS                                                          │
│                                                                 │
│  [☐] ID  Name         Email              Active  Admin  Joined │
│  ─────────────────────────────────────────────────────────────  │
│  [☐]  1  clubpresident [email]           Yes     No     2025   │
│  [☐]  2  admin1       [email]            Yes     Yes    2025   │
│  [☐]  3  otherclub    [email]            No      No     2025   │
│  ...                                                            │
│                                                                 │
│  [ Send Activation Reminder ]  [ Remove Selected ]              │
└─────────────────────────────────────────────────────────────────┘
```

## Admin: Bookings Tabel

```
┌─────────────────────────────────────────────────────────────────┐
│  BOOKINGS                                                       │
│                                                                 │
│  [☐] ID  User  Club       Created   Modified  Submitted  Lock  │
│  ─────────────────────────────────────────────────────────────  │
│  [☐]  1   1    H-DC Cent  01-Feb    15-Mar    15-Mar     No    │
│  [☐]  2   3    Club XYZ   05-Feb    20-Mar    --         No    │
│  ...                                                            │
│                                                                 │
│  Acties per geselecteerde boeking(en):                          │
│  [ Send Submit Reminder ] [ Send Payment Reminder ]             │
│  [ Lock Selected ] [ Unlock Selected ] [ Lock ALL ]             │
│  [ View Booking Overview ] [ Remove Selected ]                  │
└─────────────────────────────────────────────────────────────────┘
```

## Admin: Contacts / Delegates / Guests / Rooms / Travels Tabellen

```
┌─────────────────────────────────────────────────────────────────┐
│  [TABEL NAAM]                                                   │
│                                                                 │
│  Tabel met alle records uit de betreffende tabel.               │
│  Kolommen komen overeen met database velden.                    │
│  Elke rij toont booking_id referentie.                          │
│                                                                 │
│  Bij Rooms: extra kolom voor hotel room toewijzing              │
│  [dropdown beschikbare kamernummers ▼] [ Assign ]               │
└─────────────────────────────────────────────────────────────────┘
```

## Admin: Extras

```
┌─────────────────────────────────────────────────────────────────┐
│  EXTRAS                                                         │
│                                                                 │
│  Bestaande extras:                                              │
│  [☐] ID  Booking  Description          Amount                  │
│  [☐]  1    5      Extra t-shirts (3)   €75,00                  │
│  ...                                                            │
│  [ Remove Selected ]                                            │
│                                                                 │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─                    │
│  Nieuw extra toevoegen:                                         │
│  Booking:     [dropdown booking IDs ▼]                          │
│  Description: [________________________]                        │
│  Amount:      [________]                                        │
│  [☐] Send email to contact                                     │
│  [ Add Extra ]                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Admin: Payments

```
┌─────────────────────────────────────────────────────────────────┐
│  PAYMENTS                                                       │
│                                                                 │
│  Bestaande betalingen:                                          │
│  [☐] ID  Booking  Date        Description       Amount         │
│  [☐]  1    5      15-Mar-25   Bank transfer      €500,00       │
│  [☐]  2    8      20-Mar-25   PayPal             €350,00       │
│  ...                                                            │
│  [ Remove Selected ]                                            │
│                                                                 │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─                    │
│  Nieuwe betaling toevoegen:                                     │
│  Booking:     [dropdown booking IDs ▼]                          │
│  Date:        [____________]                                    │
│  Description: [________________________]                        │
│  Amount:      [________]                                        │
│  [☐] Send email to contact                                     │
│  [ Add Payment ]                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Admin: Hotel Rooms

```
┌─────────────────────────────────────────────────────────────────┐
│  HOTEL ROOMS                                                    │
│                                                                 │
│  ID  Room No   Type      Location   Available                  │
│  1   101       Single    Vianen     Yes                        │
│  2   102       Double    Vianen     No (assigned)              │
│  3   201       Twin      Houten     Yes                        │
│  ...                                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Admin: Downloads

```
┌─────────────────────────────────────────────────────────────────┐
│  DOWNLOAD                                                       │
│                                                                 │
│  Generating Excel spreadsheet...                                │
│                                                                 │
│  (Automatische download van .xlsx bestand met alle              │
│   boekingsdata + overzichten)                                   │
│                                                                 │
│  Twee varianten:                                                │
│  • Download Submitted: alleen gesubmitte boekingen              │
│  • Download Saved: alle opgeslagen boekingen (incl. drafts)     │
└─────────────────────────────────────────────────────────────────┘
```

## Off-canvas: Booking Overview (onder)

Zelfde als bij booking.php — toont details + kosten + betalingen van geselecteerde boeking.

## Gedrag

- Alleen toegankelijk voor users met admin=1
- Niet-admin gebruikers worden geredirect naar login
- Alle content wordt dynamisch geladen via AJAX (admin_load.php)
- Email-functies: activatie reminder, submit reminder, payment reminder, lock notificatie
- Bij Lock ALL → alle boekingen vergrendeld + email naar alle contacten
- Booking overview opent als off-canvas panel onderaan
- Session timeout: 25 minuten
