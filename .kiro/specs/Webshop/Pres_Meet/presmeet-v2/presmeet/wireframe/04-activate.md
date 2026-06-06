# Wireframe: Account Activatie (activate.php)

## Beschrijving

Pagina bereikbaar via activatie-link in email. Drie scenario's: eerste activatie, heractivatie, of wachtwoord reset.

## Layout - Wachtwoord Reset

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   [FH-DCE Logo]    [PM 2025 Logo]                       │
│                                                         │
│           PM 2025 Account Activation                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Enter the new password details for user: [username]    │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Password:         [____________________]         │   │
│  │                   Must be 8-20 characters long.  │   │
│  │                                                  │   │
│  │ Re-enter password:[____________________]         │   │
│  │                   Must be 8-20 characters long.  │   │
│  │                                                  │   │
│  │                   [ Change password ]            │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Layout - Activatie Bevestiging

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   [FH-DCE Logo]    [PM 2025 Logo]                       │
│                                                         │
│           PM 2025 Account Activation                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Your account has successfully been activated, you      │
│  can now log on and start your booking.                 │
│                                                         │
│  « Go to logon page                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Scenario's

1. `?register=true` → Account activeren na registratie → bevestiging + link naar login
2. `?activate=true` → Heractivatie (bestaand wachtwoord behouden) → bevestiging
3. `?reset=true` → Wachtwoord reset formulier tonen → na submit bevestiging

## Gedrag

- Ongeldige activatiecode → foutmelding
- Account al actief → melding "al actief"
- Onbekende user → redirect naar login
