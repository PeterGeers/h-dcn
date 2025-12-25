# 🚀 Cognito Management Implementation Guide

## 📋 Overzicht
Complete Cognito gebruikersbeheer systeem voor H-DCN dashboard met CSV bulk upload functionaliteit.

## 🎯 Frontend (Klaar)
✅ **Componenten aangemaakt:**
- `CognitoAdminPage.js` - Hoofdpagina met tabs
- `UserManagement.js` - Gebruikersbeheer met CSV upload
- `GroupManagement.js` - Groepenbeheer
- `PoolSettings.js` - Pool configuratie weergave
- `CsvUpload.js` - Bulk CSV upload component
- `UserModal.js` - Gebruiker aanmaken/bewerken
- `GroupModal.js` - Groep aanmaken
- `cognitoService.js` - API service laag

✅ **Integratie:**
- Toegevoegd aan MemberAdminPage als "Cognito Beheer" tab
- Werkt met bestaande API endpoints

## 🔧 Backend (Te implementeren)

### 1. Lambda Functie
**Bestand:** `cognito-lambda-example.py`
```bash
# Deploy naar AWS Lambda
aws lambda create-function \
  --function-name hdcn-cognito-admin \
  --runtime python3.9 \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://cognito-lambda.zip
```

### 2. IAM Permissions
**Bestand:** `cognito-iam-policy.json`
```bash
# Attach policy to Lambda role
aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::ACCOUNT:policy/CognitoAdminPolicy
```

### 3. API Gateway Routes
Voeg toe aan bestaande API Gateway:
```
/cognito/{proxy+} → Lambda: hdcn-cognito-admin
```

## 📁 Data Preparatie (Klaar)

### CSV Conversie
✅ **Script:** `convert-google-csv.js`
✅ **Input:** Google Workspace export (61 gebruikers)
✅ **Output:** `cognito-users.csv` (Cognito-ready formaat)

### Automatische Groep Mapping
```javascript
// Bestuur → hdcnBestuur + hdcnAdmins
president@, secretaris@, penningmeester@

// Admins → hdcnAdmins  
webmaster, ledenadministratie

// Regio's → hdcnRegio_[RegioNaam]
noordholland, utrecht, limburg, etc.

// Basis → hdcnLeden (iedereen)
```

## 🚀 Deployment Stappen

### Stap 1: Backend Deploy
1. **Lambda functie aanmaken** met `cognito-lambda-example.py`
2. **IAM policy toevoegen** uit `cognito-iam-policy.json`
3. **API Gateway routes** configureren voor `/cognito/*`
4. **Test endpoints** met `test-cognito-api.js`

### Stap 2: Frontend Deploy
1. **Build nieuwe code:**
   ```bash
   npm run build
   ```
2. **Deploy naar S3/CloudFront**
3. **Test interface** in browser

### Stap 3: Data Upload
1. **Ga naar** Ledenadministratie → Cognito Beheer → Gebruikers
2. **Upload** `cognito-users.csv` bestand
3. **Controleer** resultaten en groep toewijzingen

## 🧪 Testing

### API Endpoints Testen
```bash
# Test basis endpoints
node test-cognito-api.js

# Verwachte output:
# ✅ GET /cognito/users - 200 OK
# ✅ GET /cognito/groups - 200 OK  
# ✅ GET /cognito/pool - 200 OK
```

### Frontend Testen
1. **Gebruikers tab** - Lijst van Cognito gebruikers
2. **Groepen tab** - Lijst van groepen (10 stuks)
3. **Pool Settings** - User pool configuratie
4. **CSV Upload** - Bulk gebruiker import

## 📊 Verwachte Resultaten

### Na Implementatie
- **61 nieuwe Cognito gebruikers** uit Google Workspace
- **Automatische groep toewijzing** op basis van rol/regio
- **Volledig gebruikersbeheer** via web interface
- **Bulk operations** voor toekomstige imports

### Groepen Structuur
```
hdcnLeden (61 leden)
├── hdcnBestuur (5 leden)
├── hdcnAdmins (7 leden)  
├── hdcnRegio_Utrecht (4 leden)
├── hdcnRegio_NoordHolland (6 leden)
├── hdcnRegio_ZuidHolland (3 leden)
├── hdcnRegio_Limburg (4 leden)
├── hdcnRegio_Oost (5 leden)
├── hdcnRegio_Friesland (3 leden)
├── hdcnRegio_Groningen (3 leden)
└── hdcnRegio_Duitsland (4 leden)
```

## 🔒 Beveiliging

### Toegangscontrole
- **Alleen hdcnAdmins** kunnen Cognito beheer gebruiken
- **API endpoints** beveiligd via Lambda authorizer
- **Audit logging** van alle wijzigingen

### Wachtwoorden
- **Tijdelijk wachtwoord:** `WelkomHDCN2024!`
- **Gebruikers moeten** bij eerste login wijzigen
- **Email verificatie** automatisch ingeschakeld

## 📞 Support

### Troubleshooting
1. **404 errors** → Backend endpoints nog niet gedeployed
2. **403 errors** → IAM permissions ontbreken
3. **CSV upload fails** → POST /cognito/users endpoint mist
4. **Geen data** → Check browser console voor errors

### Logs Checken
```bash
# Lambda logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/hdcn-cognito

# API Gateway logs  
aws logs describe-log-groups --log-group-name-prefix API-Gateway-Execution-Logs
```

## ✅ Checklist

### Backend
- [ ] Lambda functie gedeployed
- [ ] IAM permissions geconfigureerd  
- [ ] API Gateway routes toegevoegd
- [ ] Endpoints getest met curl/Postman

### Frontend  
- [ ] Code gebuild en gedeployed
- [ ] Cognito Beheer tab zichtbaar
- [ ] Gebruikers/Groepen laden correct
- [ ] CSV upload component werkt

### Data
- [ ] `cognito-users.csv` gegenereerd
- [ ] Groep mappings gecontroleerd
- [ ] Test upload uitgevoerd
- [ ] Gebruikers kunnen inloggen

🎉 **Na voltooiing heb je een volledig Cognito management systeem!**