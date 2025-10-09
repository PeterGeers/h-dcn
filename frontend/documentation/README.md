# H-DCN Dashboard

React SPA dashboard voor H-DCN leden portal.

## Setup

1. Installeer dependencies:
```bash
npm install
```

2. Update Cognito configuratie in `src/index.js`:
   - Vervang `YOUR_CLIENT_ID` met echte Cognito App Client ID

3. Start development server:
```bash
npm start
```

## Features

- **Authenticatie**: AWS Cognito integratie
- **Dashboard**: Welkomstpagina met beschikbare apps
- **Profiel beheer**: Gebruikers kunnen eigen attributen bijwerken
- **Role-based access**: Apps getoond op basis van gebruikersgroepen

## Gebruikersgroepen

- `hdcnLeden`: Toegang tot profiel en webshop
- `Admins`: Toegang tot alle apps + beheer

## Volgende stappen

1. Maak Cognito App Client aan
2. Voeg webshop en admin modules toe
3. Deploy naar S3 + CloudFront# hdcn-dashboard
