# Wireframe: Login Pagina (index.php)

## Beschrijving

Startpagina van het PM registratiesysteem. Gebruikers loggen hier in of navigeren naar registratie/wachtwoord reset.

## Layout

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   [FH-DCE Logo]    [PM 2025 Logo]                       │
│                                                         │
│              PM 2025 Sign-on                            │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  The FH-DCE Presidents' meeting 2025 is organized by    │
│  Harley-Davidson Club 't Centrum.                       │
│                                                         │
│  Log on to create or update the booking for your club.  │
│  Make sure to register for an account first.            │
│                                                         │
│  ┌─────────────────────────────────────────────┐        │
│  │ User name:       [________________________] │        │
│  │                                             │        │
│  │ Password:        [________________________] │        │
│  │                                             │        │
│  │                  [      Log in            ]  │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  Forgot password                                        │
│                                                         │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─          │
│                                                         │
│  Before you can log on you must first create an         │
│  account. Note that there can be only one account       │
│  per club.                                              │
│                                                         │
│                  [ Create new account ]                  │
│                                                         │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─          │
│  https://www.hdc-centrum.nl                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Elementen

- PM logo (geanimeerd, pulserend bij laden)
- FH-DCE logo
- Formulier: username + password
- "Log in" button (primary)
- Link "Forgot password" → forgotpass.php
- "Create new account" button → register.php
- Link naar club website

## Gedrag

- Bij succesvolle login → redirect naar booking.php (of admin.php voor admins)
- Bij inactief account → melding "account niet geactiveerd"
- Bij fout → melding "onbekende combinatie"
- Als `ACCOUNT_REGISTRATION_LOCKED = true` → registratie-knop verborgen
