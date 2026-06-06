# Wireframe: Wachtwoord Vergeten (forgotpass.php)

## Beschrijving

Gebruikers kunnen hier een wachtwoord-reset aanvragen. Er wordt een email gestuurd met een reset-link.

## Layout

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   [FH-DCE Logo]    [PM 2025 Logo]                       │
│                                                         │
│             PM 2025 Password Reset                      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Enter the user name and email used for the initial     │
│  account registration to request a password reset.      │
│                                                         │
│  ┌─────────────────────────────────────────────┐        │
│  │ User name:       [________________________] │        │
│  │                                             │        │
│  │ Email address:   [________________________] │        │
│  │                                             │        │
│  │                  [ Request new password ]    │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Elementen

- PM + FH-DCE logo's
- Formulier: username + email
- "Request new password" button (primary)

## Gedrag

- Bij geldige combinatie → email met reset-link + bevestigingsmelding
- Bij onbekende username → foutmelding
- Bij niet-matchend email → foutmelding
- Email bevat twee opties: wachtwoord wijzigen OF alleen heractiveren
