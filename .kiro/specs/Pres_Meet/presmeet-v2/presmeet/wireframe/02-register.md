# Wireframe: Registratie Pagina (register.php)

## Beschrijving

Nieuwe gebruikers maken hier een account aan. Na registratie wordt een activatie-email verstuurd.

## Layout

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   [FH-DCE Logo]    [PM 2025 Logo]                       │
│                                                         │
│            PM 2025 User Registration                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Use a user name of your choosing to create your        │
│  account for the PM 2025 registration.                  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ User name:        [____________________]         │   │
│  │                   Must be 5-50 characters long.  │   │
│  │                                                  │   │
│  │ Password:         [____________________]         │   │
│  │                   Must be 8-20 characters long.  │   │
│  │                                                  │   │
│  │ Re-enter password:[____________________]         │   │
│  │                   Must be 8-20 characters long.  │   │
│  │                                                  │   │
│  │ Email address:    [____________________]         │   │
│  │                   Enter a valid email address.   │   │
│  │                                                  │   │
│  │                   [ Register Account ]           │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Elementen

- PM + FH-DCE logo's
- Formulier: username, password (2x), email
- Inline help-tekst per veld
- "Register Account" button (primary)

## Validatie

- Username: 5-50 tekens, mag niet al bestaan
- Password: 8-20 tekens, beide velden moeten matchen
- Email: geldig emailadres

## Gedrag

- Na succesvolle registratie → bevestigingsmelding + activatie-email
- Bij bestaande username → foutmelding
- Bij niet-matchende wachtwoorden → foutmelding
- Als `ACCOUNT_REGISTRATION_LOCKED = true` → melding "registratie gesloten"
- Als gebruiker al ingelogd is → uitloggen + melding
