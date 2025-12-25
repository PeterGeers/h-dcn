# H-DCN Dutch Localization Strategy

## Overview

This document outlines the localization strategy for the H-DCN Dashboard application. As a Dutch club, all user-facing content should be in Dutch while maintaining English for technical documentation and code.

## Localization Principles

### What Should Be in Dutch

- ✅ All user interface text (buttons, labels, headings)
- ✅ Form field labels and placeholders
- ✅ Error messages and validation feedback
- ✅ Email templates and notifications
- ✅ Success/confirmation messages
- ✅ Navigation menus and breadcrumbs
- ✅ Help text and tooltips
- ✅ Status indicators and badges

### What Should Remain in English

- ✅ Code comments and documentation
- ✅ Requirements and design documents
- ✅ API endpoint names and responses
- ✅ Database field names
- ✅ Git commit messages
- ✅ Technical logs (with Dutch user-facing messages)
- ✅ Developer documentation

## Implementation Approach

### 1. Frontend Localization

#### Text Constants File

Create a centralized Dutch text constants file:

**Location**: `frontend/src/localization/nl.ts`

```typescript
export const NL_TEXT = {
  // Authentication
  auth: {
    login: {
      title: "Inloggen bij H-DCN",
      email: "E-mailadres",
      password: "Wachtwoord",
      forgotPassword: "Wachtwoord vergeten?",
      loginButton: "Inloggen",
      createAccount: "Nieuw account aanmaken",
      rememberMe: "Onthoud mij",
    },
    signup: {
      title: "Account Aanmaken",
      email: "E-mailadres",
      password: "Wachtwoord",
      confirmPassword: "Bevestig wachtwoord",
      signupButton: "Account Aanmaken",
      alreadyHaveAccount: "Heeft u al een account?",
      passwordRequirements:
        "Wachtwoord moet minimaal 8 tekens bevatten, inclusief hoofdletters, kleine letters en cijfers",
    },
    passwordReset: {
      title: "Wachtwoord Herstellen",
      email: "E-mailadres",
      sendResetLink: "Verstuur herstellink",
      resetCode: "Herstelcode",
      newPassword: "Nieuw wachtwoord",
      confirmNewPassword: "Bevestig nieuw wachtwoord",
      resetButton: "Wachtwoord Instellen",
      backToLogin: "Terug naar inloggen",
    },
  },

  // Member Registration
  registration: {
    title: "Lidmaatschap Aanvragen",
    subtitle: "Vul onderstaand formulier in om lid te worden van H-DCN",
    personalInfo: "Persoonlijke Gegevens",
    firstName: "Voornaam",
    lastName: "Achternaam",
    email: "E-mailadres",
    phone: "Telefoonnummer",
    address: "Adres",
    street: "Straat en huisnummer",
    postalCode: "Postcode",
    city: "Plaats",
    membershipType: "Type Lidmaatschap",
    individual: "Individueel",
    family: "Gezin",
    corporate: "Bedrijf",
    region: "Regio",
    additionalInfo: "Aanvullende Informatie",
    submitButton: "Aanvraag Versturen",
    confirmMessage:
      "Bedankt voor uw aanvraag! We nemen binnen een week contact met u op.",
    requiredField: "Dit veld is verplicht",
    invalidEmail: "Voer een geldig e-mailadres in",
    invalidPhone: "Voer een geldig telefoonnummer in",
  },

  // Member Portal
  portal: {
    title: "Mijn H-DCN Account",
    welcome: "Welkom",
    membershipInfo: "Lidmaatschapgegevens",
    memberNumber: "Lidnummer",
    memberSince: "Lid sinds",
    membershipType: "Type lidmaatschap",
    membershipStatus: "Status",
    region: "Regio",
    paymentStatus: "Betalingsstatus",
    renewalDate: "Verlengingsdatum",
    editProfile: "Profiel Bewerken",
    saveChanges: "Wijzigingen Opslaan",
    cancel: "Annuleren",
    editableFields: "Wijzigbare Gegevens",
    readOnlyFields: "Alleen-lezen Gegevens",
    updateSuccess: "Uw gegevens zijn succesvol bijgewerkt",
    updateError: "Er is een fout opgetreden bij het bijwerken van uw gegevens",
  },

  // Navigation
  nav: {
    home: "Home",
    myAccount: "Mijn Account",
    webshop: "Webshop",
    events: "Evenementen",
    products: "Producten",
    admin: "Beheer",
    logout: "Uitloggen",
  },

  // Membership Status
  status: {
    new_applicant: "Nieuwe Aanvraag",
    active: "Actief",
    inactive: "Inactief",
    suspended: "Geschorst",
    ended: "Beëindigd",
    sponsor: "Sponsor",
  },

  // Payment Status
  payment: {
    current: "Actueel",
    overdue: "Achterstallig",
    exempt: "Vrijgesteld",
  },

  // Error Messages
  errors: {
    generic: "Er is een fout opgetreden. Probeer het later opnieuw.",
    networkError: "Netwerkfout. Controleer uw internetverbinding.",
    unauthorized: "U bent niet geautoriseerd voor deze actie.",
    sessionExpired: "Uw sessie is verlopen. Log opnieuw in.",
    invalidCredentials: "Ongeldige inloggegevens.",
    accountLocked:
      "Uw account is vergrendeld. Neem contact op met de beheerder.",
    accountDisabled: "Uw account is uitgeschakeld.",
    passwordResetRequired: "U moet uw wachtwoord opnieuw instellen.",
    emailAlreadyExists: "Dit e-mailadres is al in gebruik.",
    weakPassword:
      "Wachtwoord is te zwak. Gebruik minimaal 8 tekens met hoofdletters, kleine letters en cijfers.",
    passwordMismatch: "Wachtwoorden komen niet overeen.",
    invalidResetCode: "Ongeldige of verlopen herstelcode.",
    formValidation: "Controleer de formuliervelden en probeer opnieuw.",
  },

  // Success Messages
  success: {
    loginSuccess: "Succesvol ingelogd",
    logoutSuccess: "Succesvol uitgelogd",
    accountCreated: "Account succesvol aangemaakt",
    passwordReset: "Wachtwoord succesvol ingesteld",
    resetLinkSent: "Herstellink verzonden naar uw e-mailadres",
    profileUpdated: "Profiel succesvol bijgewerkt",
    applicationSubmitted: "Aanvraag succesvol verzonden",
  },

  // Common Actions
  actions: {
    save: "Opslaan",
    cancel: "Annuleren",
    edit: "Bewerken",
    delete: "Verwijderen",
    confirm: "Bevestigen",
    back: "Terug",
    next: "Volgende",
    submit: "Versturen",
    close: "Sluiten",
    search: "Zoeken",
    filter: "Filteren",
    refresh: "Vernieuwen",
  },

  // H-DCN Organizational Structure
  roles: {
    // Algemeen Bestuur
    hdcnVoorzitter: "Voorzitter",
    hdcnSecretaris: "Landelijke Secretaris",
    hdcnViceVoorzitter: "Vice-Voorzitter",
    hdcnPenningmeester: "Penningmeester",
    hdcnLedenadministratie: "Ledenadministratie",

    // Ondersteunende Rollen
    hdcnWebmaster: "Webmaster",
    hdcnToercomisaris: "Toercommissaris",
    hdcnClubblad: "Clubblad",
    hdcnWebshop: "Webshop",

    // Regionale Rollen
    regioVoorzitter: "Regio Voorzitter",
    regioSecretaris: "Regio Secretaris",
    regioPenningmeester: "Regio Penningmeester",
    regioVrijwilliger: "Regio Vrijwilliger",

    // Basis
    hdcnLeden: "Leden",

    // Role Categories
    generalBoard: "Algemeen Bestuur",
    supportingRoles: "Ondersteunende Rollen",
    regionalRoles: "Regionale Rollen",
    basicMembers: "Basis Leden",
  },

  // Regions
  regions: {
    regio_1: "Regio 1",
    regio_2: "Regio 2",
    regio_3: "Regio 3",
    regio_4: "Regio 4",
    regio_5: "Regio 5",
    regio_6: "Regio 6",
    regio_7: "Regio 7",
    regio_8: "Regio 8",
    regio_9: "Regio 9",
    selectRegion: "Selecteer Regio",
    allRegions: "Alle Regio's",
  },

  // Clubblad Mailing Lists
  clubblad: {
    title: "Clubblad Beheer",
    mailingLists: "Verzendlijsten",
    createList: "Nieuwe Lijst Maken",
    filterOptions: "Filter Opties",
    exportFormat: "Export Formaat",
    emailList: "E-mail Lijst",
    physicalAddressList: "Adressenlijst",
    fullContactList: "Volledige Contactlijst",

    filters: {
      regions: "Regio's",
      membershipTypes: "Lidmaatschap Types",
      membershipStatuses: "Lidmaatschap Status",
      paymentStatuses: "Betalingsstatus",
      roles: "Rollen",
      dateRange: "Datum Bereik",
      customFilters: "Aangepaste Filters",
      includeRoles: "Inclusief Rollen",
      excludeRoles: "Exclusief Rollen",
      hasEmail: "Heeft E-mailadres",
      hasPhysicalAddress: "Heeft Fysiek Adres",
      joinDateFrom: "Lid sinds (van)",
      joinDateTo: "Lid sinds (tot)",
    },

    export: {
      generating: "Lijst wordt gegenereerd...",
      ready: "Lijst gereed voor download",
      error: "Fout bij genereren van lijst",
      downloadCsv: "Download CSV",
      downloadExcel: "Download Excel",
      totalMembers: "Totaal aantal leden",
      filteredMembers: "Gefilterde leden",
    },
  },

  // Events Management
  events: {
    title: "Evenementen",
    myRegionEvents: "Mijn Regio Evenementen",
    allEvents: "Alle Evenementen",
    createEvent: "Nieuw Evenement",
    editEvent: "Evenement Bewerken",
    eventDetails: "Evenement Details",
    eventDate: "Datum",
    eventTime: "Tijd",
    eventLocation: "Locatie",
    eventDescription: "Beschrijving",
    eventRegion: "Regio",
    maxParticipants: "Maximum Deelnemers",
    registrationDeadline: "Inschrijfdeadline",
    eventStatus: "Status",
    upcoming: "Aankomend",
    ongoing: "Bezig",
    completed: "Voltooid",
    cancelled: "Geannuleerd",
    registerForEvent: "Inschrijven",
    unregisterFromEvent: "Uitschrijven",
    registrationConfirmed: "Inschrijving bevestigd",
    registrationCancelled: "Inschrijving geannuleerd",
    eventFull: "Evenement vol",
    registrationClosed: "Inschrijving gesloten",
  },

  // Admin Interface
  admin: {
    title: "Beheer",
    users: "Gebruikers",
    members: "Leden",
    applications: "Aanvragen",
    cognitoManagement: "Cognito Gebruikersbeheer",
    syncWithDatabase: "Synchroniseer met Ledendatabase",
    syncInProgress: "Synchronisatie bezig...",
    syncComplete: "Synchronisatie voltooid",
    syncErrors: "Synchronisatiefouten",
    viewReport: "Bekijk Rapport",
    approveApplication: "Aanvraag Goedkeuren",
    rejectApplication: "Aanvraag Afwijzen",
    changeStatus: "Status Wijzigen",
    statusChangeLog: "Statuswijzigingen",
    lastSync: "Laatste synchronisatie",

    // Role Management
    roleManagement: "Rollenbeheer",
    assignRoles: "Rollen Toewijzen",
    removeRole: "Rol Verwijderen",
    multipleRoles: "Meerdere Rollen",
    roleConflict: "Rol Conflict",
    roleHierarchy: "Rol Hiërarchie",

    // Permission Management
    permissions: "Rechten",
    memberDataAccess: "Ledengegevens Toegang",
    eventManagement: "Evenementen Beheer",
    webshopAccess: "Webshop Toegang",
    clubbladAccess: "Clubblad Toegang",
    systemAdmin: "Systeem Beheerder",

    // Regional Management
    regionalAccess: "Regionale Toegang",
    crossRegionalAccess: "Regio-overschrijdende Toegang",
    regionalEvents: "Regionale Evenementen",
    regionalMembers: "Regionale Leden",
  },
};
```

#### Usage in Components

```typescript
import { NL_TEXT } from "../localization/nl";

function LoginPage() {
  return (
    <Box>
      <Heading>{NL_TEXT.auth.login.title}</Heading>
      <FormControl>
        <FormLabel>{NL_TEXT.auth.login.email}</FormLabel>
        <Input type="email" placeholder={NL_TEXT.auth.login.email} />
      </FormControl>
      <Button>{NL_TEXT.auth.login.loginButton}</Button>
    </Box>
  );
}
```

### 2. Backend Localization

#### Email Templates

**Location**: `backend/email_templates/nl/`

Create Dutch email templates:

**welcome_email.html**:

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Welkom bij H-DCN</title>
  </head>
  <body>
    <h1>Welkom bij H-DCN!</h1>
    <p>Beste {{firstName}} {{lastName}},</p>
    <p>
      Welkom bij H-DCN. Om uw account te activeren, moet u eerst uw wachtwoord
      instellen.
    </p>
    <p>Klik op onderstaande link om uw wachtwoord in te stellen:</p>
    <a href="{{resetLink}}">Wachtwoord Instellen</a>
    <p>Deze link is 24 uur geldig.</p>
    <p>Met vriendelijke groet,<br />Het H-DCN Team</p>
  </body>
</html>
```

**application_notification.html** (for admins):

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Nieuwe Lidmaatschapsaanvraag</title>
  </head>
  <body>
    <h1>Nieuwe Lidmaatschapsaanvraag</h1>
    <p>Er is een nieuwe lidmaatschapsaanvraag ontvangen:</p>
    <ul>
      <li><strong>Naam:</strong> {{firstName}} {{lastName}}</li>
      <li><strong>E-mail:</strong> {{email}}</li>
      <li><strong>Telefoon:</strong> {{phone}}</li>
      <li><strong>Type:</strong> {{membershipType}}</li>
      <li><strong>Regio:</strong> {{region}}</li>
      <li><strong>Datum:</strong> {{applicationDate}}</li>
    </ul>
    <p><a href="{{reviewLink}}">Bekijk Aanvraag</a></p>
  </body>
</html>
```

**application_confirmation.html**:

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Uw Aanvraag is Ontvangen</title>
  </head>
  <body>
    <h1>Bedankt voor uw Aanvraag</h1>
    <p>Beste {{firstName}} {{lastName}},</p>
    <p>Bedankt voor uw interesse in een lidmaatschap bij H-DCN.</p>
    <p>
      Wij hebben uw aanvraag in goede orde ontvangen en zullen deze zo spoedig
      mogelijk in behandeling nemen.
    </p>
    <p>U kunt binnen een week een reactie van ons verwachten.</p>
    <p>Met vriendelijke groet,<br />Het H-DCN Team</p>
  </body>
</html>
```

#### Error Messages

**Location**: `backend/localization/nl_errors.py`

```python
NL_ERROR_MESSAGES = {
    'INVALID_CREDENTIALS': 'Ongeldige inloggegevens',
    'USER_NOT_FOUND': 'Gebruiker niet gevonden',
    'ACCOUNT_DISABLED': 'Account is uitgeschakeld',
    'PASSWORD_RESET_REQUIRED': 'Wachtwoord moet opnieuw worden ingesteld',
    'SESSION_EXPIRED': 'Sessie is verlopen',
    'UNAUTHORIZED': 'Niet geautoriseerd',
    'VALIDATION_ERROR': 'Validatiefout',
    'EMAIL_EXISTS': 'E-mailadres is al in gebruik',
    'WEAK_PASSWORD': 'Wachtwoord is te zwak',
    'NETWORK_ERROR': 'Netwerkfout',
    'SERVER_ERROR': 'Serverfout',
    'SYNC_ERROR': 'Synchronisatiefout',
    'MEMBER_NOT_FOUND': 'Lid niet gevonden',
    'INVALID_STATUS': 'Ongeldige status',
    'PERMISSION_DENIED': 'Geen toegang'
}

def get_dutch_error_message(error_code: str) -> str:
    return NL_ERROR_MESSAGES.get(error_code, 'Er is een fout opgetreden')
```

### 3. AWS Cognito Configuration

#### Custom Email Templates

Configure Cognito to use Dutch email templates:

1. **Verification Email**:

   - Subject: `Bevestig uw e-mailadres voor H-DCN`
   - Body: `Klik op deze link om uw e-mailadres te bevestigen: {####}`

2. **Password Reset Email**:

   - Subject: `Wachtwoord herstellen voor H-DCN`
   - Body: `Gebruik deze code om uw wachtwoord te herstellen: {####}`

3. **Welcome Email**:
   - Subject: `Welkom bij H-DCN`
   - Body: Custom HTML template in Dutch

#### Cognito Error Messages

Map Cognito error codes to Dutch messages in frontend:

```typescript
const COGNITO_ERROR_MAP = {
  UserNotFoundException: "Gebruiker niet gevonden",
  NotAuthorizedException: "Ongeldige inloggegevens",
  UserNotConfirmedException: "E-mailadres nog niet bevestigd",
  PasswordResetRequiredException: "Wachtwoord moet opnieuw worden ingesteld",
  InvalidPasswordException: "Wachtwoord voldoet niet aan de eisen",
  UsernameExistsException: "E-mailadres is al in gebruik",
  CodeMismatchException: "Ongeldige verificatiecode",
  ExpiredCodeException: "Verificatiecode is verlopen",
  LimitExceededException: "Te veel pogingen. Probeer het later opnieuw",
  TooManyRequestsException: "Te veel verzoeken. Probeer het later opnieuw",
};
```

### 4. Form Validation Messages

**Location**: `frontend/src/validation/nl-messages.ts`

```typescript
export const NL_VALIDATION = {
  required: (field: string) => `${field} is verplicht`,
  email: "Voer een geldig e-mailadres in",
  phone: "Voer een geldig telefoonnummer in",
  minLength: (field: string, min: number) =>
    `${field} moet minimaal ${min} tekens bevatten`,
  maxLength: (field: string, max: number) =>
    `${field} mag maximaal ${max} tekens bevatten`,
  pattern: (field: string) => `${field} heeft een ongeldig formaat`,
  passwordMatch: "Wachtwoorden komen niet overeen",
  passwordStrength:
    "Wachtwoord moet minimaal 8 tekens bevatten, inclusief hoofdletters, kleine letters en cijfers",
  postalCode: "Voer een geldige postcode in (bijv. 1234AB)",
  numeric: (field: string) => `${field} moet een getal zijn`,
  future: (field: string) => `${field} moet in de toekomst liggen`,
  past: (field: string) => `${field} moet in het verleden liggen`,
};
```

## Implementation Checklist

### Phase 1: Setup

- [ ] Create `frontend/src/localization/nl.ts` with all Dutch text constants
- [ ] Create `backend/localization/nl_errors.py` for error messages
- [ ] Create `backend/email_templates/nl/` directory with email templates
- [ ] Create `frontend/src/validation/nl-messages.ts` for validation messages

### Phase 2: Frontend Updates

- [ ] Update all React components to use `NL_TEXT` constants
- [ ] Replace hardcoded English text with Dutch constants
- [ ] Update form validation to use Dutch messages
- [ ] Update error handling to display Dutch messages
- [ ] Update navigation menus with Dutch labels

### Phase 3: Backend Updates

- [ ] Update email service to use Dutch templates
- [ ] Update API error responses to include Dutch messages
- [ ] Configure Cognito custom email templates in Dutch
- [ ] Update Lambda functions to return Dutch error messages

### Phase 4: Testing

- [ ] Test all user flows with Dutch text
- [ ] Verify email templates render correctly
- [ ] Test error messages in various scenarios
- [ ] Verify form validation messages
- [ ] Test admin interface with Dutch labels

### Phase 5: Documentation

- [ ] Document localization approach for future developers
- [ ] Create translation guide for adding new text
- [ ] Document Cognito email template configuration

## Best Practices

### 1. Centralization

- Keep all Dutch text in centralized files
- Never hardcode Dutch text in components
- Use constants for all user-facing text

### 2. Consistency

- Use consistent terminology across the application
- Maintain a glossary of Dutch terms
- Use formal "u" form for professional communication

### 3. Maintainability

- Group related text together (auth, portal, admin, etc.)
- Use descriptive constant names
- Add comments for context where needed

### 4. Future-Proofing

- Structure allows easy addition of other languages
- Separate text from logic
- Use template strings for dynamic content

## Dutch Terminology Guide

### Common Terms

- **Account**: Account
- **Login**: Inloggen
- **Logout**: Uitloggen
- **Password**: Wachtwoord
- **Email**: E-mailadres
- **Member**: Lid
- **Membership**: Lidmaatschap
- **Application**: Aanvraag
- **Status**: Status
- **Region**: Regio
- **Admin**: Beheerder
- **Settings**: Instellingen
- **Profile**: Profiel
- **Save**: Opslaan
- **Cancel**: Annuleren
- **Edit**: Bewerken
- **Delete**: Verwijderen
- **Confirm**: Bevestigen

### Formal vs Informal

Use formal "u" form throughout the application:

- ✅ "Uw account" (Your account - formal)
- ❌ "Je account" (Your account - informal)

## Contact

For questions about localization or to suggest improvements, contact the development team.
