# H-DCN Members Table Schema Documentation

## Overview

This document provides a comprehensive overview of the DynamoDB Members table schema used in the H-DCN system. The schema is based on actual production data and field definitions found in the codebase.

## Table Information

- **Table Name**: `Members`
- **Primary Key**: `member_id` (String)
- **Region**: `eu-west-1`
- **Billing Mode**: Pay-per-request (on-demand) or incasso

## UI Field Mapping

The member details view organizes database fields into logical UI sections. Here's how the fields map to the UI display:

### Persoonlijke Gegevens (Personal Information)

- **Voornaam**: `voornaam` → "Johan"
- **Achternaam**: `achternaam` → "Ekelenburg"
- **Initialen**: `initialen` → "J.D."
- **Tussenvoegsel**: `tussenvoegsel` → "van"
- **Geboortedatum**: `geboortedatum` → "29-6-1960"
- **Geslacht**: `geslacht` → "man"
- **Email**: `email` → "johan6721@gmail.com"
- **Telefoon**: `telefoon` → "0613916262"

### Adresgegevens (Address Information)

- **Straat**: `straat` → "Jacob Cremerstraat 63"
- **Postcode**: `postcode` → "6821 DC"
- **Woonplaats**: `woonplaats` → "Arnhem"
- **Land**: `land` → "Nederland"

### Lidmaatschap (Membership Information)

- **Type**: `lidmaatschap` → "Gezins lid"
- **Regio**: `regio` → "Oost"
- **Clubblad**: `clubblad` → "Geen"
- **Lidnummer**: `lidnummer` → "6200"
- **Lid sinds**: `tijdstempel` → "1-10-2025" (formatted)
- **Laatste update**: `updated_at` → "1-10-2025" (formatted)

### Motor Gegevens (Motorcycle Information)

- **Merk**: `motormerk` → "Harley-Davidson"
- **Type**: `motortype` → "Fat Boy"
- **Bouwjaar**: `bouwjaar` → "1992"
- **Kenteken**: `kenteken` → "MV-70-NV"

### Financiële Gegevens (Financial Information)

- **Bankrekeningnummer**: `bankrekeningnummer` → "NL93INGB0668858354"

### Overige Informatie (Other Information)

- **Aanmeldingsjaar**: `aanmeldingsjaar` → "2022"
- **Datum_ondertekening**: `datum_ondertekening` → "1-8-2022"
- **Tijdstempel**: `tijdstempel` → "1-8-2022 14:30:03"
- **Wiewatwaar**: `wiewatwaar` → "Vrienden"

### Fields Not Shown in UI

Several database fields are not displayed in the current member details view:

- `member_id`, `created_at` (system fields)
- ~~`phone`, `mobiel`, `werktelefoon`~~ (LEGACY duplicate phone fields - should be removed, keep only `telefoon`)
- ~~`beroep`, `werkgever`, `nationaliteit`~~ (LEGACY fields - should be removed)
- `nieuwsbrief` (preference field - actually used in admin views and forms)
- Various postal address fields, financial details, etc.

**CLEANUP NEEDED**: The legacy fields should be removed from:

- TypeScript types (`frontend/src/types/index.ts`)
- Database records (if possible)
- Any remaining references in the codebase
- **Phone field consolidation**: Keep only `telefoon`, remove `phone`, `mobiel`, `werktelefoon`

## Field Categories

Based on the role permissions system and the actual member details UI, fields are categorized into groups. The UI organizes fields into logical sections as shown in the member details view:

### UI Field Organization

The member details view organizes fields into these sections:

- **Persoonlijke Gegevens** (Personal Information)
- **Adresgegevens** (Address Information)
- **Lidmaatschap** (Membership Information)
- **Motor Gegevens** (Motorcycle Information)
- **Financiële Gegevens** (Financial Information)
- **Overige Informatie** (Other Information)

### Permission-Based Categories

For role-based access control, fields are categorized into three main groups:

### 1. System Fields (Auto-generated)

Fields that are automatically managed by the system:

| Field Name   | Type   | Description                      | Example                                |
| ------------ | ------ | -------------------------------- | -------------------------------------- |
| `member_id`  | String | UUID primary key                 | `5dade63a-9497-4f00-ac50-bdccdd167fe6` |
| `created_at` | String | ISO timestamp of record creation | `2025-10-01T17:52:00.178242`           |
| `updated_at` | String | ISO timestamp of last update     | `2025-10-01T18:24:49.107907`           |

### 2. Personal Information Fields

Fields editable by members for their own records:

| Field Name      | Type   | Description                   | Example                                            |
| --------------- | ------ | ----------------------------- | -------------------------------------------------- |
| `voornaam`      | String | First name                    | `Johan`                                            |
| `achternaam`    | String | Last name                     | `Ekelenburg`                                       |
| `tussenvoegsel` | String | Name prefix (Dutch)           | `van`                                              |
| `initialen`     | String | Initials                      | `J.D.`                                             |
| `name`          | String | Full name (computed)          | `Johan Ekelenburg`                                 |
| `telefoon`      | String | Phone number                  | `0613916262`                                       |
| `straat`        | String | Street address                | `Jacob Cremerstraat 63`                            |
| `huisnummer`    | String | House number (separate field) | ``                                                 |
| `postcode`      | String | Postal code                   | `6821 DC`                                          |
| `woonplaats`    | String | City                          | `Arnhem`                                           |
| `land`          | String | Country                       | `Nederland`                                        |
| `address`       | String | Full address (computed)       | `Jacob Cremerstraat 63, 6821 DC Arnhem, Nederland` |
| `email`         | String | Email address                 | `johan6721@gmail.com`                              |
| `geboortedatum` | String | Date of birth                 | `29-6-1960`                                        |
| `geslacht`      | String | Gender                        | `man`                                              |
| `nieuwsbrief`   | String | Newsletter preference         | ``                                                 |
| `wiewatwaar`    | String | How did you hear about us     | `Vrienden`                                         |

### 3. Motorcycle Information Fields

Fields editable by members for their own records:

| Field Name   | Type   | Description      | Example           |
| ------------ | ------ | ---------------- | ----------------- |
| `bouwjaar`   | String | Build year       | `1992`            |
| `motormerk`  | String | Motorcycle brand | `Harley-Davidson` |
| `motortype`  | String | Motorcycle type  | `Fat Boy`         |
| `motormodel` | String | Motorcycle model | ``                |
| `kenteken`   | String | License plate    | `MV-70-NV`        |

### 4. Administrative Fields

Fields only editable by users with administrative roles:

| Field Name            | Type   | Description              | Example              | Editable by Applicant |
| --------------------- | ------ | ------------------------ | -------------------- | --------------------- |
| `lidnummer`           | String | Membership number        | `6200`               | N                     |
| `lidmaatschap`        | String | Membership type          | `Gezins lid`         | Y                     |
| `status`              | String | Membership status        | `active`             | N                     |
| `tijdstempel`         | String | Member since date        | `1-8-2022 14:30:03`  | N                     |
| `aanmeldingsjaar`     | String | Registration year        | `2022`               | N                     |
| `regio`               | String | Region assignment        | `Oost`               | Y                     |
| `clubblad`            | String | Club magazine preference | `Geen`               | Y                     |
| `bankrekeningnummer`  | String | Bank account number      | `NL93INGB0668858354` | Y                     |
| `iban`                | String | IBAN                     | ``                   | Y                     |
| `bic`                 | String | BIC code                 | ``                   | Y                     |
| `datum_ondertekening` | String | Signature date           | `1-8-2022`           | N                     |

### 5. Financial and Payment Fields

**⚠️ ARCHITECTURAL NOTE**: These fields could be better handled by external payment systems like Stripe, which would provide better security, compliance, and functionality for payment processing.

Administrative fields related to payments:

| Field Name     | Type   | Description         | Example | External System Suggestion |
| -------------- | ------ | ------------------- | ------- | -------------------------- |
| `contributie`  | String | Contribution amount | ``      | Stripe subscription plans  |
| `betaalwijze`  | String | Payment method      | ``      | Stripe payment methods     |
| `incasso`      | String | Direct debit        | ``      | Stripe SEPA Direct Debit   |
| `ingangsdatum` | String | Start date          | ``      | Stripe subscription start  |
| `einddatum`    | String | End date            | ``      | Stripe subscription end    |
| `opzegtermijn` | String | Notice period       | ``      | Stripe subscription config |

### 6. Additional Administrative Fields

**⚠️ ARCHITECTURAL NOTE**: These fields could be better managed in a dedicated CRM system or external administrative platform, separating business logic from core member identity data.

Other administrative and system fields:

| Field Name        | Type   | Description                           | Example | External System Suggestion  |
| ----------------- | ------ | ------------------------------------- | ------- | --------------------------- |
| `bsn`             | String | BSN (Dutch social security number)    | ``      | Secure compliance system    |
| `privacy`         | String | Privacy settings                      | ``      | Consent management platform |
| `toestemmingfoto` | String | Photo permission                      | ``      | Consent management platform |
| `hobbys`          | String | Hobbies                               | ``      | CRM system                  |
| `notities`        | String | Notes                                 | ``      | CRM system                  |
| `opmerkingen`     | String | Comments                              | ``      | CRM system                  |
| `minderjarigNaam` | String | Minor's name (for family memberships) | ``      | Family management system    |

### 7. Postal Address Fields

**⚠️ ARCHITECTURAL NOTE**: These fields could be handled by address validation services or integrated postal systems, reducing data duplication and improving address accuracy.

Alternative postal address (if different from main address):

| Field Name       | Type   | Description                    | Example | External System Suggestion |
| ---------------- | ------ | ------------------------------ | ------- | -------------------------- |
| `postadres`      | String | Postal address                 | ``      | Address validation service |
| `postpostcode`   | String | Postal code for postal address | ``      | Address validation service |
| `postwoonplaats` | String | City for postal address        | ``      | Address validation service |
| `postland`       | String | Country for postal address     | ``      | Address validation service |

### 8. Legacy Fields (TO BE REMOVED)

Fields that exist in the system but should be cleaned up and removed:

| Field Name            | Type       | Description                                                         | Example          | Status                |
| --------------------- | ---------- | ------------------------------------------------------------------- | ---------------- | --------------------- |
| ~~`phone`~~           | ~~String~~ | ~~Alternative phone field~~ (duplicate of `telefoon`)               | ~~`0613916262`~~ | LEGACY - remove       |
| ~~`mobiel`~~          | ~~String~~ | ~~Mobile phone~~                                                    | ~~``~~           | LEGACY - remove       |
| ~~`werktelefoon`~~    | ~~String~~ | ~~Work phone~~                                                      | ~~``~~           | LEGACY - remove       |
| ~~`nationaliteit`~~   | ~~String~~ | ~~Nationality~~                                                     | ~~``~~           | LEGACY - remove       |
| ~~`beroep`~~          | ~~String~~ | ~~Profession~~                                                      | ~~``~~           | LEGACY - remove       |
| ~~`werkgever`~~       | ~~String~~ | ~~Employer~~                                                        | ~~``~~           | LEGACY - remove       |
| ~~`membership_type`~~ | ~~String~~ | ~~Alternative membership type field~~ (duplicate of `lidmaatschap`) | ~~`Gezins lid`~~ | LEGACY - remove       |
| ~~`motorkleur`~~      | ~~String~~ | ~~Motorcycle color~~                                                | ~~``~~           | UNAUTHORIZED - remove |
| ~~`cilinderinhoud`~~  | ~~String~~ | ~~Engine displacement~~                                             | ~~``~~           | UNAUTHORIZED - remove |
| ~~`vermogen`~~        | ~~String~~ | ~~Engine power~~                                                    | ~~``~~           | UNAUTHORIZED - remove |

**Cleanup Actions Required:**

- Remove from TypeScript types (`frontend/src/types/index.ts`)
- Remove from UI components (`MemberDetailModal.tsx`, `MemberEditModal.tsx`)
- Remove from field categorization logic
- Optional: Database cleanup (fields exist but are mostly empty)

## Field Permission Rules

Based on the role permissions system defined in `backend/handler/hdcn_cognito_admin/role_permissions.py`:

### Personal Fields (PERSONAL_FIELDS)

```python
PERSONAL_FIELDS = [
    'voornaam', 'achternaam', 'tussenvoegsel', 'initialen',
    'telefoon', 'straat', 'postcode', 'woonplaats', 'land',
    'email', 'nieuwsbrief', 'geboortedatum', 'geslacht', 'wiewatwaar'
]
```

- **Editable by**: Members for their own records, users with `Members_CRUD_All` role
- **Permission**: `members:update_own_personal` (own record) or `members:update_all` (admin)

### Motorcycle Fields (MOTORCYCLE_FIELDS)

```python
MOTORCYCLE_FIELDS = [
    'bouwjaar', 'motormerk', 'motortype', 'kenteken'
]
```

- **Editable by**: Members for their own records, users with `Members_CRUD_All` role
- **Permission**: `members:update_own_personal` (own record) or `members:update_all` (admin)

### Administrative Fields (ADMINISTRATIVE_FIELDS)

```python
ADMINISTRATIVE_FIELDS = [
    'member_id', 'lidnummer', 'lidmaatschap', 'status', 'tijdstempel',
    'aanmeldingsjaar', 'regio', 'clubblad', 'bankrekeningnummer',
    'datum_ondertekening', 'created_at', 'updated_at'
]
```

- **Editable by**: Only users with `Members_CRUD_All` role
- **Permission**: `members:update_administrative`

## Data Types and Validation

### String Fields

All fields in the Members table are stored as DynamoDB String (S) type. This provides flexibility for various data formats and handles empty values consistently.

### Date Formats

The system uses multiple date formats:

- **ISO Timestamps**: `2025-10-01T17:52:00.178242` (for `created_at`, `updated_at`)
- **Dutch Date Format**: `1-8-2022` (for `datum_ondertekening`)
- **Dutch DateTime Format**: `1-8-2022 14:30:03` (for `tijdstempel`)
- **Simple Date**: `29-6-1960` (for `geboortedatum`)

### Empty Values

Empty fields are stored as empty strings (`""`) rather than being omitted from the record.

## Usage in Code

### Field Validation

The `can_edit_field()` function in `role_permissions.py` validates field access:

```python
def can_edit_field(roles, field_name, is_own_record=False):
    """Check if user can edit a specific field based on their roles"""
    user_permissions = get_combined_permissions(roles)

    # Administrative fields require special permissions
    if field_name in ADMINISTRATIVE_FIELDS:
        return 'members:update_administrative' in user_permissions

    # Personal and motorcycle fields can be edited by user for own record
    if field_name in PERSONAL_FIELDS or field_name in MOTORCYCLE_FIELDS:
        if is_own_record and 'members:update_own_personal' in user_permissions:
            return True
        # Or if user has admin permissions
        return 'members:update_all' in user_permissions

    # For other fields, require admin permissions
    return 'members:update_all' in user_permissions
```

### CSV Import Mapping

The `import_members.py` script maps CSV columns to database fields:

```python
field_mapping = {
    'Lidsinds': 'tijdstempel',
    'Lidnummer': 'lidnummer',
    'Achternaam': 'achternaam',
    'Initialen': 'initialen',
    'Voornaam': 'voornaam',
    'Tussenvoegsel': 'tussenvoegsel',
    'Straat en huisnummer': 'straat',
    'Postcode': 'postcode',
    'Woonplaats': 'woonplaats',
    'Land': 'land',
    'Telefoonnummer': 'telefoon',
    'E-mailadres': 'email',
    'Geboorte datum': 'geboortedatum',
    'Geslacht': 'geslacht',
    'Regio': 'regio',
    'Clubblad': 'clubblad',
    'Soort lidmaatschap': 'lidmaatschap',
    'Bouwjaar': 'bouwjaar',
    'Motormerk': 'motormerk',
    'Type motor': 'motortype',
    'Kenteken': 'kenteken',
    'WieWatWaar': 'wiewatwaar',
    'Bankrekeningnummer': 'bankrekeningnummer',
    'Datum ondertekening': 'datum_ondertekening',
    'Aanmeldingsjaar': 'aanmeldingsjaar',
    'Digitale nieuwsbrieven': 'nieuwsbrief'
}
```

## Notes

1. **Duplicate Fields**: Some fields have duplicates (e.g., `telefoon` and `phone`, `lidmaatschap` and `membership_type`) likely due to system evolution.

2. **Computed Fields**: Fields like `name` and `address` appear to be computed from other fields.

3. **Regional Values**: The `regio` field uses Dutch region names like "Oost", "Noord-Holland", etc.

4. **Membership Types**: Common values include "Gezins lid", "Gewoon lid", "Donateur", etc.

5. **Status Values**: The `status` field typically contains values like "active", "inactive", "pending", etc.

6. **Empty String Handling**: The system consistently uses empty strings (`""`) for null/empty values rather than omitting fields.

This schema documentation provides the foundation for implementing field-level permissions and understanding the complete structure of member data in the H-DCN system.
