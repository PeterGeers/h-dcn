# H-DCN Portal

Een React-gebaseerd dashboard voor H-DCN leden en beheerders met AWS Cognito authenticatie en geavanceerde toegangscontrole.

## 🚀 Snelstart

### Vereisten
- Node.js 18+
- AWS Account met Cognito configuratie
- Git

### Installatie
```bash
git clone <repository-url>
cd hdcn-frontEnd
npm install
```

### Configuratie
1. Kopieer `.env.example` naar `.env`
2. Vul AWS Cognito configuratie in:
```env
REACT_APP_AWS_REGION=eu-west-1
REACT_APP_USER_POOL_ID=your-user-pool-id
REACT_APP_USER_POOL_WEB_CLIENT_ID=your-client-id
REACT_APP_API_BASE_URL=your-api-url
```

### Starten
```bash
npm start
```

## 📋 Functionaliteiten

### Voor Alle Gebruikers
- **Lidmaatschap Aanmelding**: Dynamisch formulier voor nieuwe leden

### Voor Leden (hdcnLeden)
- **Webshop**: Producten bestellen met Stripe betalingen
- **Profiel Beheer**: Persoonlijke gegevens bijwerken

### Voor Regionale Beheerders (hdcnRegio_*)
- **Regionale Ledenadministratie**: Alleen-lezen toegang tot eigen regio

### Voor Beheerders (hdcnAdmins)
- **Ledenadministratie**: Gebruikers en groepen beheren
- **Evenementenbeheer**: Events aanmaken en beheren
- **Product Management**: Webshop producten beheren
- **Parameter Beheer**: Systeem configuratie

## 🔐 Toegangscontrole

Het systeem gebruikt AWS Cognito groepen voor toegangscontrole:

| Groep | Toegang |
|-------|---------|
| Geen groepen | Alleen lidmaatschap aanmelding |
| hdcnLeden | Webshop + Profiel |
| hdcnAdmins | Alle modules |
| hdcnRegio_* | Regionale leden (alleen-lezen) |

### Functie-niveau Rechten
Geavanceerd rechtensysteem via `function_permissions` parameter:
- **Read**: Alleen bekijken
- **Write**: Bekijken en wijzigen
- **Wildcards**: `hdcnRegio_*` voor alle regio's

## 🏗️ Architectuur

```
src/
├── components/          # Herbruikbare componenten
│   ├── AppCard.js
│   ├── FunctionGuard.js
│   └── GroupAccessGuard.js
├── modules/            # Feature modules
│   ├── events/
│   ├── members/
│   ├── products/
│   └── webshop/
├── pages/              # Hoofdpagina's
├── utils/              # Services en utilities
│   ├── api.js
│   ├── functionPermissions.js
│   └── parameterService.js
└── App.js
```

## 🛠️ Development

### Scripts
```bash
npm start          # Development server
npm run build      # Production build
npm test           # Run tests
```

### Deployment
```bash
.\deploy.ps1       # PowerShell deployment script
.\git-sync.ps1     # Git add, commit, push
```

### Testing
Test bestanden in `/test/` directory:
- `test-api.js` - API endpoints testen
- `test-cognito-*.js` - Cognito functionaliteit
- `test-function-permissions.js` - Rechten systeem

## 📦 Technische Stack

- **Frontend**: React 18, Chakra UI
- **Authenticatie**: AWS Cognito
- **State Management**: React Context
- **Routing**: React Router v6
- **Betalingen**: Stripe
- **Forms**: Formik + Yup
- **PDF**: jsPDF + html2canvas

## 🔧 AWS Services

- **Cognito**: User management en authenticatie
- **DynamoDB**: Data opslag
- **S3**: File storage
- **Parameter Store**: Configuratie
- **Lambda**: Backend API's

## 📚 Documentatie

- [Gebruikershandleiding](documentation/user-manual.html)
- [Technische Documentatie](documentation/technical-design-manual.html)
- [Cognito Implementatie](documentation/COGNITO_IMPLEMENTATION_GUIDE.md)
- [Backend Fix Summary](documentation/BACKEND_FIX_SUMMARY.md)

## 🐛 Troubleshooting

### Veelvoorkomende Problemen

**Toegang Geweigerd**
- Controleer groepslidmaatschap in Cognito
- Vraag beheerder om juiste groep toe te wijzen

**Modules Niet Zichtbaar**
- Verifieer functierechten in Parameter Beheer
- Check `function_permissions` configuratie

**API Errors**
- Controleer `.env` configuratie
- Verifieer AWS credentials en regio

## 🤝 Contributing

1. Fork het project
2. Maak feature branch (`git checkout -b feature/nieuwe-functie`)
3. Commit wijzigingen (`git commit -m 'Voeg nieuwe functie toe'`)
4. Push naar branch (`git push origin feature/nieuwe-functie`)
5. Open Pull Request

## 📄 Licentie

Dit project is eigendom van H-DCN organisatie.

## 📞 Support

Voor technische ondersteuning of vragen over toegangsrechten, neem contact op met de H-DCN beheerders.

---

**Versie**: 1.0.0  
**Laatst bijgewerkt**: December 2024