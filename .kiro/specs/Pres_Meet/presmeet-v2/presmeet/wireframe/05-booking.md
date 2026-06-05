# Wireframe: Booking Pagina (booking.php)

## Beschrijving

Hoofdpagina voor clubs om hun boeking aan te maken en te beheren. Bevat sidebar navigatie, formulier met meerdere secties, en actieknoppen.

## Layout - Desktop

```
┌─────────────────────────────────────────────────────────────────────────┐
│ NAVBAR (fixed top)                                                      │
│ [PM Logo]  Booking Ref # NL-001-1    [Status: Submitted]    [≡ Menu]   │
├──────────┬──────────────────────────────────────────────────────────────┤
│ SIDEBAR  │  MAIN CONTENT                                               │
│          │                                                              │
│ Menu     │  [FH-DCE Logo]    [PM 2025 Logo]                            │
│          │  PM 2025 Booking Details                                     │
│ ┌──────┐ │                                                              │
│ │Instr.│ │  Before you start please read the instructions carefully.    │
│ │Save  │ │  The system will log you out after 25 min of inactivity.     │
│ │Valid. │ │                                                              │
│ │Overv. │ │  ┌─────────────────────────────────────────────────────┐     │
│ │Submit│ │  │         CLUB & CONTACT DETAILS (Section 1)          │     │
│ │Logout│ │  │                                                     │     │
│ └──────┘ │  │  Club name:    [dropdown FH-DCE clubs ▼]            │     │
│          │  │  Club address: [________________________]            │     │
│          │  │  Club ZIP:     [________]                            │     │
│          │  │  Club city:    [________________________]            │     │
│          │  │  Club country: [dropdown countries ▼]                │     │
│          │  │                                                     │     │
│          │  │  First name:   [________________________]            │     │
│          │  │  Last name:    [________________________]            │     │
│          │  │  Address:      [________________________]            │     │
│          │  │  ZIP:          [________]                            │     │
│          │  │  City:         [________________________]            │     │
│          │  │  Email:        [________________________]            │     │
│          │  │  Phone:        [________________________]            │     │
│          │  └─────────────────────────────────────────────────────┘     │
│          │                                                              │
│          │  ┌─────────────────────────────────────────────────────┐     │
│          │  │         DELEGATES (Section 2)                       │     │
│          │  │                                                     │     │
│          │  │  Delegate 1                                         │     │
│          │  │  First name:  [____________]                        │     │
│          │  │  Last name:   [____________]                        │     │
│          │  │  Position:    [____________]                        │     │
│          │  │  T-shirt:     [dropdown sizes ▼]                    │     │
│          │  │  Party:       (●) Yes  ( ) No                      │     │
│          │  │                                                     │     │
│          │  │  [+ Add Delegate]  [- Remove Delegate]              │     │
│          │  └─────────────────────────────────────────────────────┘     │
│          │                                                              │
│          │  ┌─────────────────────────────────────────────────────┐     │
│          │  │         GUESTS (Section 3)                          │     │
│          │  │                                                     │     │
│          │  │  (Geen guests toegevoegd)                           │     │
│          │  │                                                     │     │
│          │  │  [+ Add Guest]                                      │     │
│          │  └─────────────────────────────────────────────────────┘     │
│          │                                                              │
│          │  ┌─────────────────────────────────────────────────────┐     │
│          │  │         ROOMS (Section 4)                           │     │
│          │  │                                                     │     │
│          │  │  (Geen rooms toegevoegd)                            │     │
│          │  │                                                     │     │
│          │  │  [+ Add Room]                                       │     │
│          │  └─────────────────────────────────────────────────────┘     │
│          │                                                              │
│          │  ┌─────────────────────────────────────────────────────┐     │
│          │  │         TRAVELS (Section 5)                         │     │
│          │  │  (Alleen zichtbaar als er rooms zijn)               │     │
│          │  │                                                     │     │
│          │  │  [+ Add Travel]                                     │     │
│          │  └─────────────────────────────────────────────────────┘     │
│          │                                                              │
│          │  ┌─────────────────────────────────────────────────────┐     │
│          │  │    COMMENTS AND SPECIAL WISHES                      │     │
│          │  │  ┌───────────────────────────────────────────────┐  │     │
│          │  │  │                                               │  │     │
│          │  │  │  (textarea, 5 rijen)                          │  │     │
│          │  │  │                                               │  │     │
│          │  │  └───────────────────────────────────────────────┘  │     │
│          │  └─────────────────────────────────────────────────────┘     │
│          │                                                              │
│          │  ┌──────────┐  ┌──────────┐  ┌──────────────┐               │
│          │  │ Validate │  │   Save   │  │    Submit    │               │
│          │  └──────────┘  └──────────┘  └──────────────┘               │
│          │                                                              │
└──────────┴──────────────────────────────────────────────────────────────┘
```

## Delegate Detail (per delegate)

```
┌─────────────────────────────────────────────────────┐
│  Delegate [n]                                       │
│                                                     │
│  First name:  [____________]  Last name: [________] │
│  Position:    [____________]                        │
│  T-shirt:     [dropdown ▼ No shirt/Male S/.../4XL]  │
│  Party:       (●) Yes  ( ) No                      │
└─────────────────────────────────────────────────────┘
```

## Guest Detail (per guest)

```
┌─────────────────────────────────────────────────────┐
│  Guest [n]                                          │
│                                                     │
│  First name:  [____________]  Last name: [________] │
│  T-shirt:     [dropdown ▼]                          │
│  Party:       (●) Yes  ( ) No                      │
│  City tour:   ( ) Yes  (●) No                      │
└─────────────────────────────────────────────────────┘
```

## Room Detail (per room)

```
┌─────────────────────────────────────────────────────┐
│  Room [n]                                           │
│                                                     │
│  Arrival:     [dropdown dates ▼]                    │
│  Departure:   [dropdown dates ▼]                    │
│  Type:        [dropdown ▼ Single/Double/Twin]       │
│  Guest 1:     [____________] (autocomplete namen)   │
│  Guest 2:     [____________] (autocomplete namen)   │
└─────────────────────────────────────────────────────┘
```

## Travel Detail (per travel)

```
┌─────────────────────────────────────────────────────┐
│  Travel [n]                                         │
│                                                     │
│  ARRIVAL                                            │
│  Type:        [dropdown ▼ Airport/Own transport]    │
│  Airport:     [dropdown ▼ AMS/RTM/EIN]              │
│  Flight no:   [____________]                        │
│  Date:        [dropdown ▼]                          │
│  Time:        [____________]                        │
│  # Persons:   [___]                                 │
│                                                     │
│  DEPARTURE                                          │
│  Type:        [dropdown ▼ Airport/Own transport]    │
│  Airport:     [dropdown ▼]                          │
│  Flight no:   [____________]                        │
│  Date:        [dropdown ▼]                          │
│  Time:        [____________]                        │
│  # Persons:   [___]                                 │
└─────────────────────────────────────────────────────┘
```

## Off-canvas: Instructions (rechts)

```
┌──────────────────────────────────┐
│ Instructions              [X]   │
│                                  │
│ Please read these instructions   │
│ carefully before proceeding...   │
│                                  │
│ Menu:                            │
│ • Instructions                   │
│ • Save                           │
│ • Validate                       │
│ • Overview                       │
│ • Submit                         │
│ • Logout                         │
│                                  │
│ Rates:                           │
│ • Meeting: €50 per delegate      │
│ • Party: €99,50 per person       │
│ • T-shirt: €25 each              │
│ • Twin room: €185/night          │
│ • Single room: €175/night        │
│ • Transfer: €5 per person/trip   │
│ • Tourist tax: €2,30 pp/night    │
│                                  │
│ Payments:                        │
│ IBAN: NL51RABO0108112233         │
│ BIC: RABONL2U                    │
│                                  │
│           [ Close ]              │
└──────────────────────────────────┘
```

## Off-canvas: Booking Overview (onder)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Booking overview for FH-DCE Presidents' meeting 2025            [X]   │
│                                                                         │
│ Booking reference: NL-001-1                                             │
│                                                                         │
│ CONTACT DETAILS                    DELEGATES                            │
│ Club: [clubnaam]                   1. [naam] - President - Male L - Y   │
│ Contact: [naam]                    2. [naam] - Member - Female M - Y    │
│ Email: [email]                                                          │
│                                    GUESTS                               │
│ ROOMS                              1. [naam] - Male XL - Y - City: N   │
│ 1. Nov 13-16, Twin, [naam+naam]                                        │
│                                    TRAVELS                              │
│ CHARGES                            1. AMS, KL1234, Nov 13 14:00        │
│ ┌──────────────────────────────┐                                        │
│ │ Meeting    2 x €50  = €100  │                                        │
│ │ Party      3 x €99,50=€298,50│                                       │
│ │ T-shirts   3 x €25  = €75   │                                        │
│ │ Twin room  3 nights = €555  │                                        │
│ │ Transfer   2 x €5   = €10   │                                        │
│ │ Tourist tax 6 x €2,30=€13,80│                                        │
│ │ ─────────────────────────── │                                        │
│ │ TOTAL              €1052,30 │                                        │
│ │                              │                                        │
│ │ Payments received:  €500,00 │                                        │
│ │ Balance due:        €552,30 │                                        │
│ └──────────────────────────────┘                                        │
│                                                                         │
│                        [ Close ]                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Gedrag

- Sidebar zichtbaar op desktop, hamburger menu op mobiel
- Secties worden dynamisch geladen via AJAX (booking_load.php)
- Delegates: min 1, max 3 (configureerbaar per boeking)
- Guests: min 0, max 10
- Rooms: min 0, max 6
- Travels: min 0, max 4 (alleen zichtbaar als rooms > 0)
- Save → AJAX POST naar booking_save.php
- Validate → client-side + server-side validatie
- Submit → save + validate + email versturen
- Session timeout: 25 minuten
- Als `ALL_BOOKINGS_LOCKED = true` → Save/Validate/Submit verborgen, alleen overview
- Als boeking locked → beperkte wijzigingen (namen, kamertoewijzing, vluchttijden)
