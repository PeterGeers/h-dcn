# PM Registratiesysteem - Wireframe Overzicht

## Systeem

FH-DCE Presidents' Meeting registratie- en boekingssysteem. Clubs registreren een account, maken een boeking aan met delegates, guests, rooms, travels, en submitten deze naar de organisator.

## Pagina's & Flow

```
                    ┌──────────────┐
                    │  01 - LOGIN  │
                    │  index.php   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
     ┌──────────────┐ ┌─────────┐ ┌──────────────┐
     │ 02 - REGISTER│ │03-FORGOT│ │  Ingelogd?   │
     │ register.php │ │PASSWORD │ │              │
     └──────┬───────┘ └────┬────┘ └──────┬───────┘
            │              │             │
            ▼              ▼             │
     ┌──────────────┐ ┌─────────┐       │
     │ 04 - ACTIVATE│ │04-ACTIV.│       │
     │ (via email)  │ │(reset)  │       │
     └──────┬───────┘ └────┬────┘       │
            │              │             │
            └──────┬───────┘             │
                   │                     │
                   ▼                     ▼
            ┌──────────────┐    ┌───────────────┐
            │  01 - LOGIN  │    │ admin=true?   │
            └──────┬───────┘    └───┬───────┬───┘
                   │                │       │
                   │           Nee  │       │ Ja
                   │                ▼       ▼
                   │     ┌───────────┐ ┌──────────┐
                   └────►│05-BOOKING │ │06-ADMIN  │
                         │booking.php│ │admin.php │
                         └───────────┘ └──────────┘
```

## Wireframe Bestanden

| #   | Bestand                                        | Pagina         | Beschrijving                             |
| --- | ---------------------------------------------- | -------------- | ---------------------------------------- |
| 01  | [01-login.md](01-login.md)                     | index.php      | Login pagina met registratie-link        |
| 02  | [02-register.md](02-register.md)               | register.php   | Account registratie formulier            |
| 03  | [03-forgot-password.md](03-forgot-password.md) | forgotpass.php | Wachtwoord reset aanvraag                |
| 04  | [04-activate.md](04-activate.md)               | activate.php   | Account activatie / wachtwoord wijzigen  |
| 05  | [05-booking.md](05-booking.md)                 | booking.php    | Hoofd boekingsformulier met alle secties |
| 06  | [06-admin.md](06-admin.md)                     | admin.php      | Administratie dashboard                  |

## Technische Stack

- PHP 8.4 + MariaDB
- Bootstrap 5.3.3
- jQuery 3.7.1
- Bootbox.js (dialogen)
- intl-tel-input (telefoon invoer)
- SimpleXLSXGen (Excel export)
- PHPMailer (email)

## Database Tabellen

- `users` — gebruikersaccounts
- `booking` / `booking_submitted` — boekingen (draft vs. submitted)
- `contact` / `contact_submitted` — club & contactgegevens
- `delegate` / `delegate_submitted` — afgevaardigden
- `guest` / `guest_submitted` — gasten
- `room` / `room_submitted` — hotelkamers
- `travel` / `travel_submitted` — reisgegevens
- `payment` — betalingen
- `hotel_rooms` — beschikbare hotelkamers
- `fhdce_clubs` — lijst van FH-DCE clubs

## Prijzen (incl. BTW)

| Item               | Prijs              | BTW |
| ------------------ | ------------------ | --- |
| Meeting deelname   | €50 pp             | 21% |
| Diner & Party      | €99,50 pp          | 21% |
| T-shirt            | €25 per stuk       | 21% |
| Single room        | €175 per nacht     | 9%  |
| Twin/Double room   | €185 per nacht     | 9%  |
| Airport transfer   | €5 pp per rit      | 21% |
| Toeristenbelasting | €2,30 pp per nacht | 0%  |
