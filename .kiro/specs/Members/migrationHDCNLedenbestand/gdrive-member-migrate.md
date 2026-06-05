# H-DCN Member Data Migration from Google Sheets

This document provides a comprehensive overview of the member data import process from the "HDCN Ledenbestand 2026" Google Sheets directly to the H-DCN DynamoDB database using the Google Sheets API.

## Import Script Location

**Primary Script**: `backend/scripts/import_members_sheets.py` - Direct Google Sheets API access (v2.0)
**Fallback Script**: `backend/scripts/import_members.py` - CSV file import (for troubleshooting only)

**Additional Files**:

- `backend/scripts/csv_to_dynamodb.py` - Generic CSV to DynamoDB import
- `backend/scripts/setup_google_sheets_api.md` - Google Sheets API setup instructions
- `backend/Migratie/cognito_bulk_operations.py` - Bulk Cognito user import
- `backend/Migratie/cognito_bulk_cli.ps1` - PowerShell bulk operations

## Script Version History

### Version 2.0 (2026-01-06) - Current Production Version

**Enhanced Script**: `backend/scripts/import_members_sheets.py`

**Key Improvements from v1.0:**

- ✅ **Fixed region mapping**: 'Other' → 'Overig' to match memberFields.ts exactly
- ✅ **Fixed business rule logging**: Proper original/corrected value tracking in reports
- ✅ **Enhanced email validation**: Empty emails stay empty (no test@h-dcn.nl fallback)
- ✅ **Dutch "no email" indicators**: Detects "GEEN GELDIG EMAILADRES", "NVT", etc.
- ✅ **memberFields.ts validation**: Validates all enum fields against frontend definitions
- ✅ **Improved duplicate header handling**: Handles CSV export inconsistencies automatically
- ✅ **Enhanced data quality reporting**: Better categorization and timestamped reports

**Migration Results (2026-01-06):**

- ✅ Successfully imported 1,167 members
- ✅ Preserved 1 @h-dcn.nl account (webmaster@h-dcn.nl)
- ✅ Fixed 58 region values from 'Other' to 'Overig'
- ✅ Applied business rules for 100+ Clubblad members (Sponsor/Club status)

## Migration Approach: Direct Google Sheets API

### Primary Method: Google Sheets API Integration

**Key Advantages:**

- ✅ **Real-time data access** - No manual CSV export required
- ✅ **Eliminates column shift errors** - Direct cell-by-cell reading
- ✅ **Better data type preservation** - Native Google Sheets data types
- ✅ **Automatic data quality detection** - Built-in validation and error logging
- ✅ **Enhanced error reporting** - Comprehensive issue tracking with row references
- ✅ **No file management overhead** - Direct API integration
- ✅ **Consistent data format** - No CSV encoding or delimiter issues
- ✅ **memberFields.ts compliance** - Validates against frontend field definitions

**Usage (v2.0):**

```bash
# Standard import with backup and cleanup (recommended)
cd backend/scripts
python import_members_sheets.py "HDCN Ledenbestand 2026" "Ledenbestand"

# Skip backup creation (faster, but less safe)
python import_members_sheets.py "HDCN Ledenbestand 2026" --no-backup

# Skip cleanup (add to existing data instead of replacing)
python import_members_sheets.py "HDCN Ledenbestand 2026" --no-cleanup

# Skip both backup and cleanup (import only)
python import_members_sheets.py "HDCN Ledenbestand 2026" --no-backup --no-cleanup

# Show help and version info
python import_members_sheets.py
```

**Prerequisites:**

- Google Cloud project with Sheets API enabled
- Service account credentials in `.googleCredentials.json`
- Sheet shared with service account email (`your-service-account@project.iam.gserviceaccount.com`)
- Python dependencies: `pip install -r backend/requirements.txt`

### Fallback Method: CSV Import (Emergency Use Only)

**When to Use:**

- Google Sheets API is temporarily unavailable
- Service account credentials are not accessible
- Troubleshooting data-specific issues

**Usage:**

```bash
cd backend/scripts
python import_members.py "path/to/exported/file.csv"
```

**Limitations:**

- ⚠️ **Manual export required** - Additional step prone to human error
- ⚠️ **Column shift risk** - CSV export can misalign data
- ⚠️ **Data type conversion issues** - Loss of native data types
- ⚠️ **Limited error context** - Less detailed error reporting
- ⚠️ **Encoding issues** - Potential character encoding problems

## Google Sheets → Database Field Mapping

### Successfully Mapped Fields

| **Google Sheets Column Name** | **Database Field**    | **Field Group** | **Status**    | **Notes**                   |
| ----------------------------- | --------------------- | --------------- | ------------- | --------------------------- |
| `Tijdstempel`                 | `tijdstempel`         | membership      | ✅ **Mapped** | Member since date           |
| `Lidnummer`                   | `lidnummer`           | membership      | ✅ **Mapped** | Member number               |
| `Achternaam`                  | `achternaam`          | personal        | ✅ **Mapped** | Last name                   |
| `Initialen`                   | `initialen`           | personal        | ✅ **Mapped** | Initials                    |
| `Voornaam`                    | `voornaam`            | personal        | ✅ **Mapped** | First name                  |
| `Tussenvoegsel`               | `tussenvoegsel`       | personal        | ✅ **Mapped** | Name prefix (van, de, etc.) |
| `Straat en huisnummer`        | `straat`              | address         | ✅ **Mapped** | Street and house number     |
| `Postcode`                    | `postcode`            | address         | ✅ **Mapped** | Postal code                 |
| `Woonplaats`                  | `woonplaats`          | address         | ✅ **Mapped** | City                        |
| `Land`                        | `land`                | address         | ✅ **Mapped** | Country                     |
| `Telefoonnummer`              | `telefoon`            | personal        | ✅ **Mapped** | Phone number                |
| `E-mailadres`                 | `email`               | personal        | ✅ **Mapped** | Email address               |
| `Geboorte datum`              | `geboortedatum`       | personal        | ✅ **Mapped** | Birth date                  |
| `Geslacht`                    | `geslacht`            | personal        | ✅ **Mapped** | Gender                      |
| `Regio`                       | `regio`               | membership      | ✅ **Mapped** | H-DCN region                |
| `Clubblad`                    | `clubblad`            | membership      | ✅ **Mapped** | Magazine preference         |
| `Soort lidmaatschap`          | `lidmaatschap`        | membership      | ✅ **Mapped** | Membership type             |
| `Bouwjaar`                    | `bouwjaar`            | motor           | ✅ **Mapped** | Motorcycle build year       |
| `Motormerk`                   | `motormerk`           | motor           | ✅ **Mapped** | Motorcycle brand            |
| `Type motor`                  | `motortype`           | motor           | ✅ **Mapped** | Motorcycle type/model       |
| `Kenteken`                    | `kenteken`            | motor           | ✅ **Mapped** | License plate               |
| `WieWatWaar`                  | `wiewatwaar`          | membership      | ✅ **Mapped** | How did you find us         |
| `Bankrekeningnummer`          | `bankrekeningnummer`  | financial       | ✅ **Mapped** | Bank account (IBAN)         |
| `Datum ondertekening`         | `datum_ondertekening` | administrative  | ✅ **Mapped** | Signature date              |
| `Aanmeldingsjaar`             | `aanmeldingsjaar`     | administrative  | ✅ **Mapped** | Registration year           |
| `Digitale nieuwsbrieven`      | `nieuwsbrief`         | membership      | ✅ **Mapped** | Newsletter preference       |

### 2026 Google Sheets Field Analysis

The 2026 Google Sheets contains **47 columns** with several new fields and some duplicates. Here's the complete analysis:

#### Successfully Mapped Fields (2026 → Database)

| **2026 Google Sheets Column** | **Database Field**    | **Field Group** | **Status**    | **Notes**                   |
| ----------------------------- | --------------------- | --------------- | ------------- | --------------------------- |
| `Tijdstempel`                 | `tijdstempel`         | membership      | ✅ **Mapped** | Member since date           |
| `Lidnummer`                   | `lidnummer`           | membership      | ✅ **Mapped** | Member number               |
| `Achternaam`                  | `achternaam`          | personal        | ✅ **Mapped** | Last name                   |
| `Initialen`                   | `initialen`           | personal        | ✅ **Mapped** | Initials                    |
| `Voornaam`                    | `voornaam`            | personal        | ✅ **Mapped** | First name                  |
| `Tussenvoegsel`               | `tussenvoegsel`       | personal        | ✅ **Mapped** | Name prefix (van, de, etc.) |
| `Straat en huisnummer`        | `straat`              | address         | ✅ **Mapped** | Street and house number     |
| `Postcode`                    | `postcode`            | address         | ✅ **Mapped** | Postal code                 |
| `Woonplaats`                  | `woonplaats`          | address         | ✅ **Mapped** | City                        |
| `Land`                        | `land`                | address         | ✅ **Mapped** | Country                     |
| `Telefoonnummer`              | `telefoon`            | personal        | ✅ **Mapped** | Phone number                |
| `E-mailadres`                 | `email`               | personal        | ✅ **Mapped** | Email address (primary)     |
| `Geboorte datum`              | `geboortedatum`       | personal        | ✅ **Mapped** | Birth date (full date)      |
| `Geslacht`                    | `geslacht`            | personal        | ✅ **Mapped** | Gender                      |
| `Regio`                       | `regio`               | membership      | ✅ **Mapped** | H-DCN region                |
| `Clubblad`                    | `clubblad`            | membership      | ✅ **Mapped** | Magazine preference         |
| `Soort lidmaatschap`          | `lidmaatschap`        | membership      | ✅ **Mapped** | Membership type             |
| `Bouwjaar`                    | `bouwjaar`            | motor           | ✅ **Mapped** | Motorcycle build year       |
| `Motormerk`                   | `motormerk`           | motor           | ✅ **Mapped** | Motorcycle brand            |
| `Type motor`                  | `motortype`           | motor           | ✅ **Mapped** | Motorcycle type/model       |
| `Kenteken`                    | `kenteken`            | motor           | ✅ **Mapped** | License plate               |
| `WieWatWaar`                  | `wiewatwaar`          | membership      | ✅ **Mapped** | How did you find us         |
| `Bankrekeningnummer`          | `bankrekeningnummer`  | financial       | ✅ **Mapped** | Bank account (IBAN)         |
| `Datum ondertekening`         | `datum_ondertekening` | administrative  | ✅ **Mapped** | Signature date              |
| `Aanmeldingsjaar`             | `aanmeldingsjaar`     | administrative  | ✅ **Mapped** | Registration year           |
| `Digitale nieuwsbrieven`      | `nieuwsbrief`         | membership      | ✅ **Mapped** | Newsletter preference       |
| `Opmerkingen`                 | `notities`            | administrative  | ✅ **Mapped** | Comments/notes              |

#### New Fields in 2026 Google Sheets (Analysis Required)

| **2026 Google Sheets Column** | **Database Field** | **Field Group** | **Status**       | **Analysis**                                               |
| ----------------------------- | ------------------ | --------------- | ---------------- | ---------------------------------------------------------- |
| `Gezinslid`                   | -                  | personal        | ❌ **New**       | Add to notities Family member reference (appears to be ID) |
| `Geboortedag`                 | -                  | personal        | ❌ **Function**  | Birth day (1-31) - redundant with full date                |
| `Geboortemaand`               | -                  | personal        | ❌ **Function**  | Birth month (1-12) - redundant with full date              |
| `Geboortejaar`                | -                  | personal        | ❌ **Function**  | Birth year (YYYY) - redundant with full date               |
| `Bestuursfunctie`             | -                  | administrative  | ❌ **Future**    | Board function/role - could be useful                      |
| `in functie sinds`            | -                  | administrative  | ❌ **Future**    | Board function start date                                  |
| `H-DCN Clubblad`              | -                  | membership      | ❌ **Duplicate** | Duplicate of `Clubblad` field                              |
| `Ondertekening`               | -                  | administrative  | ❌ **New**       | Signature information                                      |
| `Naam voor akkoord`           | -                  | administrative  | ❌ **New**       | Name for agreement/signature                               |
| `Lidmaatschapsnummer`         | -                  | membership      | ❌ **Future**    | Membership number (different from lidnummer?)              |
| `Afmelding`                   | -                  | administrative  | ❌ **New**       | Cancellation/unsubscribe info                              |
| `Beeindiging`                 | -                  | administrative  | ❌ **New**       | Termination info                                           |
| `Jubilaris`                   | -                  | membership      | ❌ **Function**  | Anniversary member status                                  |
| `Bedrag`                      | -                  | financial       | ❌ **Function**  | Amount/fee information                                     |
| `Inschrijfformulier`          | -                  | administrative  | ❌ **New**       | Registration form reference                                |
| `KorteNaam`                   | -                  | personal        | ❌ **Function**  | Short name/nickname                                        |
| `E-Mail`                      | -                  | personal        | ❌ **Duplicate** | Forget: Duplicate email field (mostly empty)               |
| `Email Address`               | -                  | personal        | ❌ **Duplicate** | Forget: Another duplicate email field (mostly empty)       |

#### Duplicate/Empty Columns in 2026 Google Sheets

Several columns appear to be duplicates or mostly empty:

- `H-DCN Clubblad` (duplicate of `Clubblad`)
- `E-Mail` (duplicate of `E-mailadres`, mostly empty)
- `Email Address` (another email duplicate, mostly empty)
- Empty column at position 39 (no header)

#### Recommendations for 2026 Import

**1. Use Existing Mappings**

- Continue using the 26 successfully mapped fields
- `Opmerkingen` can now be mapped to `notities` field

**2. Handle New Useful Fields**
Consider adding these fields to the database schema:

- `Bestuursfunctie` + `in functie sinds` - Board member tracking
- `Jubilaris` - Anniversary member status
- `Gezinslid` - Family member relationships

**3. Ignore Redundant Fields**
Skip these during import:

- `Geboortedag`, `Geboortemaand`, `Geboortejaar` (use `Geboorte datum` instead)
- `H-DCN Clubblad`, `E-Mail`, `Email Address` (duplicates)
- `Lidmaatschapsnummer` (unclear difference from `Lidnummer`)

**4. Administrative Fields**
These could be useful for data migration history:

- `Ondertekening`, `Naam voor akkoord` - Signature tracking
- `Afmelding`, `Beeindiging` - Termination tracking
- `Inschrijfformulier` - Form version tracking

### Generated/Computed Fields (Not in CSV)

| **Database Field** | **Field Group** | **Source**        | **Notes**                                            |
| ------------------ | --------------- | ----------------- | ---------------------------------------------------- |
| `member_id`        | administrative  | Generated UUID    | Primary key                                          |
| `created_at`       | administrative  | Current timestamp | Record creation date                                 |
| `updated_at`       | administrative  | Current timestamp | Last update date                                     |
| `name`             | personal        | Computed          | Full name from voornaam + tussenvoegsel + achternaam |
| `status`           | membership      | Default: 'Actief' | Member status (not in CSV)                           |

### Current Member Fields NOT in Google Sheets Import

| **Database Field** | **Field Group** | **Status**     | **Notes**                  |
| ------------------ | --------------- | -------------- | -------------------------- |
| `minderjarigNaam`  | personal        | ❌ **Missing** | Parent/guardian name       |
| `privacy`          | membership      | ❌ **Missing** | Privacy consent            |
| `betaalwijze`      | financial       | ❌ **Missing** | Payment method             |
| `jaren_lid`        | membership      | ❌ **Missing** | Years as member (computed) |
| `notities`         | administrative  | ❌ **Missing** | Internal notes             |

## Field Type Mapping & Validation

| **Field**       | **Google Sheets Type** | **Database Type** | **Validation Needed**      |
| --------------- | ---------------------- | ----------------- | -------------------------- |
| `geboortedatum` | Text                   | Date              | Date format conversion     |
| `lidnummer`     | Text                   | Number            | Numeric validation         |
| `bouwjaar`      | Text                   | Number            | Numeric validation         |
| `email`         | Text                   | Email             | Email validation (handled) |
| `geslacht`      | Text                   | Enum              | M/V/X/N validation         |
| `regio`         | Text                   | Enum              | Region validation          |
| `lidmaatschap`  | Text                   | Enum              | Membership type validation |

## Enhanced Data Quality Features (Google Sheets API)

### Automatic Column Shift Detection

The Google Sheets API import automatically detects and flags column shift errors:

```python
def detect_column_shift(row, headers, record_id):
    """Detect birth year in geslacht field, gender in regio field"""
    geslacht_value = row[geslacht_idx].strip()
    regio_value = row[regio_idx].strip()

    if (geslacht_value.isdigit() and len(geslacht_value) == 4 and
        regio_value.lower() in ['man', 'vrouw', 'm', 'v']):

        logger.log_issue('CRITICAL', 'COLUMN_SHIFT', record_id,
                        'geslacht/regio', 'Column shift detected')
        return True
    return False
```

### Data Quality Logging System

**Severity Levels:**

- `CRITICAL`: Data integrity issues requiring manual review
- `WARNING`: Data quality concerns with automatic correction
- `INFO`: Successful data transformations and mappings
- `CORRECTION`: Automatic data normalization applied

**Report Generation:**

```json
{
  "summary": {
    "CRITICAL": 5,
    "WARNING": 23,
    "INFO": 156,
    "CORRECTION": 89
  },
  "total_issues": 273,
  "generated_at": "2026-01-06T15:30:00",
  "issues": [...]
}
```

### Enhanced Business Rules Processing

**Clubblad Status Mapping:**

```python
if member_data.get('lidmaatschap') == 'Overig':
    clubblad = member_data.get('clubblad', '').strip()
    if clubblad == 'Papier':
        member_data['status'] = 'Sponsor'
    elif clubblad == 'Digitaal':
        member_data['status'] = 'Club'
```

**Regio Value Normalization:**

- Automatic mapping of 30+ regional variations
- Spelling corrections (Groningen/Drente → Groningen/Drenthe)
- International region handling
- Province to region consolidation

### Complete 2026 Google Sheets Column Mapping

### All 49 Columns with Database Field Mapping

| **Col#** | **2026 Google Sheets Column Name** | **Database Field**    | **Status**               | **Notes**                                              |
| -------- | ---------------------------------- | --------------------- | ------------------------ | ------------------------------------------------------ |
| 0        | `Tijdstempel`                      | `tijdstempel`         | ✅ **Mapped**            | Member since date                                      |
| 1        | `Lidnummer`                        | `lidnummer`           | ✅ **Mapped**            | Member number                                          |
| 2        | `Achternaam`                       | `achternaam`          | ✅ **Mapped**            | Last name                                              |
| 3        | `Initialen`                        | `initialen`           | ✅ **Mapped**            | Initials                                               |
| 4        | `Voornaam`                         | `voornaam`            | ✅ **Mapped**            | First name                                             |
| 5        | `Tussenvoegsel`                    | `tussenvoegsel`       | ✅ **Mapped**            | Name prefix                                            |
| 6        | `Gezinslid`                        |                       | ❌ **Add to notitie**    | Family member reference (Concatenate)                  |
| 7        | `Straat en huisnummer`             | `straat`              | ✅ **Mapped**            | Street and house number                                |
| 8        | `Postcode`                         | `postcode`            | ✅ **Mapped**            | Postal code                                            |
| 9        | `Woonplaats`                       | `woonplaats`          | ✅ **Mapped**            | City                                                   |
| 10       | `Land`                             | `land`                | ✅ **Mapped**            | Country                                                |
| 11       | `Telefoonnummer`                   | `telefoon`            | ✅ **Mapped**            | Phone number                                           |
| 12       | `E-mailadres`                      | `email`               | ✅ **Mapped**            | Primary email address                                  |
| 13       | `Geboorte datum`                   | `geboortedatum`       | ✅ **Mapped**            | Birth date (full date)                                 |
| 14       | `Geboortedag`                      |                       | ❌ **Skip**              | Redundant (use col 13)                                 |
| 15       | `Geboortemaand`                    |                       | ❌ **Skip**              | Redundant (use col 13)                                 |
| 16       | `Geboortejaar`                     |                       | ❌ **Skip**              | Redundant (use col 13)                                 |
| 17       | `Geslacht`                         | `geslacht`            | ✅ **Mapped**            | Gender                                                 |
| 18       | `Regio`                            | `regio`               | ✅ **Mapped**            | H-DCN region                                           |
| 19       | `Bestuursfunctie`                  |                       | ❌ **Future**            | Board function                                         |
| 20       | `in functie sinds`                 |                       | ❌ **Future**            | Board function start date                              |
| 21       | `Clubblad`                         | `clubblad`            | ✅ **Mapped**            | Magazine preference                                    |
| 22       | `Soort lidmaatschap`               | `lidmaatschap`        | ✅ **Mapped**            | Membership type                                        |
| 23       | `Bouwjaar`                         | `bouwjaar`            | ✅ **Mapped**            | Motorcycle build year                                  |
| 24       | `Motormerk`                        | `motormerk`           | ✅ **Mapped**            | Motorcycle brand                                       |
| 25       | `Type motor`                       | `motortype`           | ✅ **Mapped**            | Motorcycle type/model                                  |
| 26       | `Kenteken`                         | `kenteken`            | ✅ **Mapped**            | License plate                                          |
| 27       | `WieWatWaar`                       | `wiewatwaar`          | ✅ **Mapped**            | How did you find us                                    |
| 28       | `Bankrekeningnummer`               | `bankrekeningnummer`  | ✅ **Mapped**            | Bank account (IBAN)                                    |
| 29       | `H-DCN Clubblad`                   |                       | ❌ **Skip**              | Duplicate of col 21                                    |
| 30       | `Datum ondertekening`              | `datum_ondertekening` | ✅ **Mapped**            | Signature date                                         |
| 31       | `Aanmeldingsjaar`                  | `aanmeldingsjaar`     | ✅ **Calculated**        | Registration year                                      |
| 32       | `Ondertekening`                    |                       | ❌ **Future**            | Signature information                                  |
| 33       | `Naam voor akkoord`                |                       | ❌ **Future**            | Name for agreement                                     |
| 34       | `E-mailadres`                      |                       | ❌ **Skip**              | Duplicate of col 12                                    |
| 35       | `H-DCN Clubblad`                   |                       | ❌ **Skip**              | Duplicate of col 21                                    |
| 36       | `Digitale nieuwsbrieven`           | `nieuwsbrief`         | ✅ **Mapped**            | Newsletter preference                                  |
| 37       | `Lidmaatschapsnummer`              |                       | ❌ **Skip**              | Alternative membership ID                              |
| 38       | _(empty column)_                   |                       | ❌ **Skip**              | No header                                              |
| 39       | `Afmelding`                        |                       | ❌ **Add**               | Cancellation information Date                          |
| 40       | `Beeindiging`                      |                       | ❌ **Add**               | Termination information Date                           |
| 41       | `Jubilaris`                        |                       | ❌ **CalculateFunction** | Anniversary member status                              |
| 42       | `Bedrag`                           |                       | ❌ **Calculate**         | Amount/fee information                                 |
| 43       | `Inschrijfformulier`               |                       | ❌ **Future**            | Registration form version                              |
| 44       | `KorteNaam`                        |                       | ❌ **Function**          | Voornaam/tussenvoegsel/achetrnaam                      |
| 45       | `E-Mail`                           |                       | ❌ **Skip**              | Duplicate of col 12                                    |
| 46       | `Email Address`                    |                       | ❌ **Skip**              | Duplicate of col 12                                    |
| 47       | `Opmerkingen`                      | `notities`            | ✅ **Mapped**            | Comments/notes Conactenate with info if already thwere |
| 48       | _(empty column)_                   |                       | ❌ **Skip**              | No header                                              |

### Summary Statistics

- **Total Columns**: 49
- **Successfully Mapped**: 27 fields
- **Skip (Duplicates/Empty)**: 8 fields
- **Future Consideration**: 14 fields

**Note**: The `nationaliteit` (nationality) field has been removed from the database schema and is not included in the migration mapping.

### Special Business Rules for 2026 Import

#### Status Determination for "Clubblad" Records

When `Soort lidmaatschap` = "Clubblad" in the Google Sheets, these records are processed as follows:

1. **Lidmaatschap** is set to `"Overig"` (since "Clubblad" is not a valid membership type)
2. **Status** is determined by the `Clubblad` preference value:

| **Clubblad Value** | **Resulting Status** | **Resulting Lidmaatschap** | **Description**                           |
| ------------------ | -------------------- | -------------------------- | ----------------------------------------- |
| `Papier`           | `Sponsor`            | `Overig`                   | Sponsors who receive paper magazine       |
| `Digitaal`         | `Club`               | `Overig`                   | Club members who receive digital magazine |
| _(other/empty)_    | `Actief`             | `Overig`                   | Default fallback status                   |

**Implementation Logic:**

```python
if sheets_lidmaatschap == 'Clubblad':
    # Always map to 'Overig' lidmaatschap
    processed_row['lidmaatschap'] = 'Overig'

    # Determine status based on clubblad preference
    if clubblad == 'Papier':
        processed_row['status'] = 'Sponsor'
    elif clubblad == 'Digitaal':
        processed_row['status'] = 'Club'
    else:
        processed_row['status'] = 'Actief'  # Fallback
else:
    # Normal membership processing
    processed_row['status'] = 'Actief'  # Default
```

**Note**: "Clubblad" is not a valid membership type in the system, so these records are categorized as "Overig" with their status determined by magazine preference.

#### Regio Value Mapping

The Google Sheets contains H-DCN regio names that need to be mapped to the standardized database values. This mapping handles variations, misspellings, and data errors:

| **Google Sheets Regio Value** | **Database Value**  | **Notes**                                              |
| ----------------------------- | ------------------- | ------------------------------------------------------ |
| `Noord Holland`               | `Noord-Holland`     | Add hyphen for consistency                             |
| `Zuid Holland`                | `Zuid-Holland`      | Add hyphen for consistency                             |
| `Friesland`                   | `Friesland`         | ✅ Exact match                                         |
| `Utrecht`                     | `Utrecht`           | ✅ Exact match                                         |
| `Oost`                        | `Oost`              | ✅ Exact match                                         |
| `Limburg`                     | `Limburg`           | ✅ Exact match                                         |
| `Groningen/Drente`            | `Groningen/Drenthe` | Fix spelling: Drente → Drenthe                         |
| `Brabant/Zeeland`             | `Brabant/Zeeland`   | ✅ Exact match                                         |
| `Duitsland`                   | `Duitsland`         | ✅ Valid H-DCN regio                                   |
| `Deutschland`                 | `Duitsland`         | German spelling variant                                |
| `Geen`                        | `Overig`            | No regio specified                                     |
| `Man`                         | ❌ **DATA ERROR**   | Column shift - birth year in geslacht, gender in regio |
| `Vrouw`                       | ❌ **DATA ERROR**   | Column shift - birth year in geslacht, gender in regio |
| _(empty/whitespace)_          | `Other`             | Missing data                                           |

**Valid Database Enum Options:**

- `Noord-Holland`
- `Zuid-Holland`
- `Friesland`
- `Utrecht`
- `Oost`
- `Limburg`
- `Groningen/Drenthe`
- `Brabant/Zeeland`
- `Duitsland`
- `Overig`

**Implementation:**

```python
regio_value_mapping = {
    # Standard region name corrections (add hyphens)
    'Noord Holland': 'Noord-Holland',
    'Zuid Holland': 'Zuid-Holland',

    # Spelling corrections
    'Groningen/Drente': 'Groningen/Drenthe',
    'Groningen/Drenthe': 'Groningen/Drenthe',  # Already correct

    # Regional mapping corrections
    'Brabant/Zeeland': 'Brabant/Zeeland',
    'Brabant': 'Brabant/Zeeland',
    'Noord-Brabant': 'Brabant/Zeeland',
    'Zeeland': 'Brabant/Zeeland',


    # No region specified
    'Geen': 'Overig',
    'Geen regio': 'Overig',
    'Onbekend': 'Overig',
    'Unknown': 'Other',
    'N/A': 'Other',
    'NA': 'Other',

    # NOTE: Gender values in regio field indicate column shift data errors
    # These rows should be flagged for manual review, not automatically mapped
    # Pattern: birth year in geslacht field, actual gender in regio field
    # 'Man': 'Other',     # DATA ERROR - requires manual correction
    # 'Vrouw': 'Other',   # DATA ERROR - requires manual correction
    # 'M': 'Other',       # DATA ERROR - requires manual correction
    # 'V': 'Other',       # DATA ERROR - requires manual correction


    # Common misspellings
    'Noord-holland': 'Noord-Holland',
    'Zuid-holland': 'Zuid-Holland',
    'noord holland': 'Noord-Holland',
    'zuid holland': 'Zuid-Holland',
    'groningen/drente': 'Groningen/Drenthe',
    'GRONINGEN/DRENTHE': 'Groningen/Drenthe',
    'brabant/zeeland': 'Brabant/Zeeland',
    'BRABANT/ZEELAND': 'Brabant/Zeeland',

```

**Database Enum Options:**
\*\*\* Regios updated

### Board Member Role Processing Strategy

#### Approach 1: Enhanced Notities Field (Recommended for Initial Implementation)

For members with `@h-dcn.nl` email addresses, append board function information to the `notities` field:

```python
def process_board_member_info(row, processed_row):
    """
    Process board function information for @h-dcn.nl accounts
    """
    email = processed_row.get('email', '')
    bestuursfunctie = row.get('Bestuursfunctie', '').strip()
    functie_sinds = row.get('in functie sinds', '').strip()

    # Only process for @h-dcn.nl accounts with board functions
    if email.endswith('@h-dcn.nl') and bestuursfunctie:
        board_info = f"Bestuursfunctie: {bestuursfunctie}"
        if functie_sinds:
            board_info += f" (sinds {functie_sinds})"

        # Append to existing notities or create new
        existing_notes = processed_row.get('notities', '').strip()
        if existing_notes:
            processed_row['notities'] = f"{existing_notes}\n{board_info}"
        else:
            processed_row['notities'] = board_info

    return processed_row
```

**Advantages:**

- ✅ No database schema changes required
- ✅ Preserves historical information
- ✅ Easy to implement immediately
- ✅ Searchable through existing notities field

**Disadvantages:**

- ❌ Not structured data (harder to query/filter)
- ❌ Mixed with other administrative notes

#### Approach 2: Dedicated Board Member Fields (Future Enhancement)

Add specific fields to the member schema for board member tracking:

```sql
-- Database schema additions
ALTER TABLE Members ADD COLUMN board_function VARCHAR(100);
ALTER TABLE Members ADD COLUMN board_since DATE;
ALTER TABLE Members ADD COLUMN board_active BOOLEAN DEFAULT FALSE;
```

```typescript
// Frontend field definitions
boardFunction: {
  key: 'board_function',
  label: 'Bestuursfunctie',
  dataType: 'string',
  inputType: 'text',
  group: 'administrative',
  permissions: {
    view: ['System_CRUD_All', 'Members_CRUD_All', 'National_Chairman', 'National_Secretary'],
    edit: ['System_CRUD_All', 'National_Chairman', 'National_Secretary']
  },
  showWhen: [
    { field: 'email', operator: 'contains', value: '@h-dcn.nl' }
  ]
},

boardSince: {
  key: 'board_since',
  label: 'In functie sinds',
  dataType: 'date',
  inputType: 'date',
  group: 'administrative',
  permissions: {
    view: ['System_CRUD_All', 'Members_CRUD_All', 'National_Chairman', 'National_Secretary'],
    edit: ['System_CRUD_All', 'National_Chairman', 'National_Secretary']
  },
  showWhen: [
    { field: 'board_function', operator: 'exists' }
  ]
}
```

**Advantages:**

- ✅ Structured, queryable data
- ✅ Proper field validation and permissions
- ✅ Can be filtered and sorted
- ✅ Better UI/UX for board member management

**Disadvantages:**

- ❌ Requires database schema changes
- ❌ More complex implementation
- ❌ Need to update forms and views

#### Approach 3: Hybrid Solution (Recommended Long-term)

**Phase 1**: Use enhanced notities for immediate import
**Phase 2**: Migrate to dedicated fields when ready

```python
def process_board_members_hybrid(row, processed_row):
    """
    Hybrid approach: notities now, structured fields later
    """
    email = processed_row.get('email', '')
    bestuursfunctie = row.get('Bestuursfunctie', '').strip()
    functie_sinds = row.get('in functie sinds', '').strip()

    if email.endswith('@h-dcn.nl') and bestuursfunctie:
        # Phase 1: Add to notities with structured format for easy parsing
        board_info = f"[BOARD] {bestuursfunctie}"
        if functie_sinds:
            board_info += f" | Since: {functie_sinds}"

        existing_notes = processed_row.get('notities', '').strip()
        if existing_notes:
            processed_row['notities'] = f"{existing_notes}\n{board_info}"
        else:
            processed_row['notities'] = board_info

        # Phase 2: When schema is ready, also populate dedicated fields
        # processed_row['board_function'] = bestuursfunctie
        # processed_row['board_since'] = normalize_date_format(functie_sinds)
        # processed_row['board_active'] = True

    return processed_row

# Migration helper for Phase 2
def migrate_board_info_from_notities():
    """
    Extract board information from notities and populate dedicated fields
    """
    import re

    # Query all members with @h-dcn.nl emails
    members = get_members_with_hdcn_emails()

    for member in members:
        notities = member.get('notities', '')

        # Extract board info using regex
        board_match = re.search(r'\[BOARD\] (.+?)(?:\s*\|\s*Since:\s*(.+?))?(?:\n|$)', notities)

        if board_match:
            board_function = board_match.group(1).strip()
            board_since = board_match.group(2).strip() if board_match.group(2) else None

            # Update member with structured data
            update_member(member['member_id'], {
                'board_function': board_function,
                'board_since': normalize_date_format(board_since) if boase None,
                'board_active': True
            })

       # Optionally clean up notities
            cleaned_notities = re.sub(r'\[BOARD\] .+?(?:\n|$)', '', notities).strip()
            if cleaned_notities != notities:
                update_member(member['member_id'], {'not: cleaned_notities})
```

### Implementation Recommendation

**For 2026 Import**: Use **Approach 1** (Enhanced Notities)

- Quick to implement
- No schema changes needed
- Preserves all historical board information
- Can be enhanced later

**For Future Development**: Migrate to **Approach 2** (Dedicated Fields)

- Bettercture
- Improved querying and reporting
- Professional board member management

### Updated Processing Function

```python
# Add this to the main processing function
def process_2026_csv_row(row):
    # ... existing processing ...

    # Process board member information for @h-dcn.nl accounts
    processed_row = process_board_member_info(row, processed_row)

    return processed_row

### Board Member Processing Summary

#### Recommended Implementation Path:

1. **Immediate (2026 Import)**: Use Enhanced Notities approach
   - Add board function info to `notities` field for @h-dcn.nl accounts
   - Format: `[BOARD] Voorzitter | Since: 2020-01-01`
   - No schema changes required

2. **Future Enhancement**: Migrate to dedicated fields
   - Add `board_function`, `board_since`, `board_active` fields
   - Create migration script to extract from notities
   - Enhanced UI for board member management

#### Expected Results for @h-dcn.nl Accounts:

```

Email: voorzitter@h-dcn.nl
Notities: "[BOARD] Voorzitter | Since: 2020-01-01"

Email: secretaris@h-dcn.nl  
Notities: "Algemene administratieve notities\n[BOARD] Secretaris | Since: 2019-06-15"

````

This approach ensures no historical board information is lost while providing a clear migration path for future enhancements.

## Data Quality Logging and Problem Tracking

### Enhanced Import with Comprehensive Data Quality Logging

```python
import logging
import json
from datetime import datetime
from typing import List, Dict, Any

class DataQualityLogger:
    """
    Comprehensive logging system for tracking data quality issues during import
    """

    def __init__(self, log_file_path: str = "migration_data_quality.log"):
        self.log_file = log_file_path
        self.issues = []
        self.stats = {
            'total_records': 0,
            'successful_imports': 0,
            'records_with_issues': 0,
            'critical_errors': 0,
            'warnings': 0,
            'data_corrections': 0
        }

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def log_issue(self, severity: str, category: str, record_id: str,
                  field: str, issue: str, original_value: str = None,
                  corrected_value: str = None, row_number: int = None):
        """
        Log a data quality issue

        Args:
            severity: 'CRITICAL', 'WARNING', 'INFO', 'CORRECTION'
            category: 'VALIDATION', 'MAPPING', 'MISSING_DATA', 'FORMAT', 'BUSINESS_RULE'
            record_id: Unique identifier for the record
            field: Field name where issue occurred
            issue: Description of the issue
            original_value: Original value from CSV
            corrected_value: Value after correction/mapping
            row_number: CSV row number for reference
        """
        issue_record = {
            'timestamp': datetime.now().isoformat(),
            'severity': severity,
            'category': category,
            'record_id': record_id,
            'field': field,
            'issue': issue,
            'original_value': original_value,
            'corrected_value': corrected_value,
            'row_number': row_number
        }

        self.issues.append(issue_record)

        # Update statistics
        if severity == 'CRITICAL':
            self.stats['critical_errors'] += 1
        elif severity == 'WARNING':
            self.stats['warnings'] += 1
        elif severity == 'CORRECTION':
            self.stats['data_corrections'] += 1

        # Log to file
        log_message = f"Row {row_number} | {record_id} | {field} | {severity}: {issue}"
        if original_value and corrected_value:
            log_message += f" | '{original_value}' → '{corrected_value}'"

        if severity == 'CRITICAL':
            self.logger.error(log_message)
        elif severity == 'WARNING':
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    def generate_manual_review_csv(self, output_file: str = "manual_review_required.csv"):
        """Generate CSV file with records requiring manual review"""
        import csv

        # Filter critical and warning issues
        review_issues = [issue for issue in self.issues
                        if issue['severity'] in ['CRITICAL', 'WARNING']]

        if not review_issues:
            return

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['row_number', 'record_id', 'severity', 'category',
                         'field', 'issue', 'original_value', 'corrected_value', 'action_required']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for issue in review_issues:
                action_required = self._determine_action_required(issue)
                writer.writerow({
                    'row_number': issue['row_number'],
                    'record_id': issue['record_id'],
                    'severity': issue['severity'],
                    'category': issue['category'],
                    'field': issue['field'],
                    'issue': issue['issue'],
                    'original_value': issue['original_value'],
                    'corrected_value': issue['corrected_value'],
                    'action_required': action_required
                })

    def _determine_action_required(self, issue):
        """Determine what manual action is required for an issue"""
        if issue['severity'] == 'CRITICAL':
            if issue['category'] == 'MISSING_DATA':
                return 'PROVIDE_MISSING_DATA'
            elif issue['category'] == 'VALIDATION':
                return 'CORRECT_INVALID_DATA'
            else:
                return 'MANUAL_REVIEW_REQUIRED'
        elif issue['severity'] == 'WARNING':
            if 'gender' in issue['issue'].lower() and 'region' in issue['issue'].lower():
                return 'VERIFY_CORRECT_REGION'
            elif 'email' in issue['field']:
                return 'VERIFY_EMAIL_ADDRESS'
            else:
                return 'REVIEW_AND_CONFIRM'
        return 'REVIEW'

    def generate_report(self, output_file: str = "migration_quality_report.json"):
        """Generate comprehensive data quality report"""
        report = {
            'migration_summary': self.stats,
            'timestamp': datetime.now().isoformat(),
            'issues_by_severity': self._group_by_severity(),
            'issues_by_category': self._group_by_category(),
            'issues_by_field': self._group_by_field(),
            'detailed_issues': self.issues,
            'recommendations': self._generate_recommendations()
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def _group_by_severity(self):
        groups = {}
        for issue in self.issues:
            severity = issue['severity']
            if severity not in groups:
                groups[severity] = []
            groups[severity].append(issue)
        return groups

    def _group_by_category(self):
        groups = {}
        for issue in self.issues:
            category = issue['category']
            if category not in groups:
                groups[category] = []
            groups[category].append(issue)
        return groups

    def _group_by_field(self):
        groups = {}
        for issue in self.issues:
            field = issue['field']
            if field not in groups:
                groups[field] = []
            groups[field].append(issue)
        return groups

    def _generate_recommendations(self):
        recommendations = []

        # Analyze patterns and generate recommendations
        field_issues = self._group_by_field()

        for field, issues in field_issues.items():
            if len(issues) > 5:  # Field with many issues
                recommendations.append({
                    'type': 'DATA_QUALITY',
                    'field': field,
                    'issue_count': len(issues),
                    'recommendation': f"Field '{field}' has {len(issues)} issues. Consider data source validation."
                })

        return recommendations
```

### Usage Example

```python
# Initialize logger
logger = DataQualityLogger("2026_migration_quality.log")

# Process CSV with logging
for row_number, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
    try:
        processed_row = process_2026_csv_row_with_logging(row, row_number, logger)
        # Import to database
        import_to_database(processed_row)
    except Exception as e:
        logger.log_issue('CRITICAL', 'PROCESSING',
                        row.get('Lidnummer', f'Row_{row_number}'),
                        'general', f'Processing failed: {str(e)}',
                        None, None, row_number)

# Generate reports
logger.generate_report("2026_migration_report.json")
logger.generate_manual_review_csv("2026_manual_review.csv")
```

### Output Files Generated

1. **migration_data_quality.log** - Detailed log file with all issues
2. **migration_quality_report.json** - Comprehensive JSON report with statistics
3. **manual_review_required.csv** - CSV file with records needing manual attention

## Signature and Agreement Storage Strategy

### Recommended Approach for Signature Information

For storing signature and agreement acknowledgment data from the CSV, I recommend a **hybrid approach**:

#### Option 1: Enhanced Notities Field (Immediate Implementation)

```python
def process_signature_info(row, processed_row, record_id, row_number, logger):
    """
    Process signature and agreement information into notities field
    """
    ondertekening = row.get('Ondertekening', '').strip()
    naam_akkoord = row.get('Naam voor akkoord', '').strip()
    datum_ondertekening = row.get('Datum ondertekening', '').strip()
    inschrijfformulier = row.get('Inschrijfformulier', '').strip()

    if ondertekening or naam_akkoord or inschrijfformulier:
        signature_info = "[SIGNATURE]"

        if naam_akkoord:
            signature_info += f" Signed by: {naam_akkoord}"

        if datum_ondertekening:
            signature_info += f" | Date: {datum_ondertekening}"

        if inschrijfformulier:
            signature_info += f" | Form: {inschrijfformulier}"

        if ondertekening:
            signature_info += f" | Details: {ondertekening}"

        # Add to notities
        existing_notes = processed_row.get('notities', '').strip()
        if existing_notes:
            processed_row['notities'] = f"{existing_notes}\n{signature_info}"
        else:
            processed_row['notities'] = signature_info

        logger.log_issue('INFO', 'BUSINESS_RULE', record_id, 'notities',
                       'Signature information preserved', None, signature_info, row_number)

    return processed_row
```

#### Option 2: Dedicated Signature Fields (Future Enhancement)

```sql
-- Database schema additions for signature tracking
ALTER TABLE Members ADD COLUMN signature_name VARCHAR(200);
ALTER TABLE Members ADD COLUMN signature_date DATE;
ALTER TABLE Members ADD COLUMN signature_details TEXT;
ALTER TABLE Members ADD COLUMN signature_form_version VARCHAR(100);
ALTER TABLE Members ADD COLUMN agreement_acknowledged BOOLEAN DEFAULT FALSE;
ALTER TABLE Members ADD COLUMN agreement_version VARCHAR(50);
```

```typescript
// Frontend field definitions
signatureName: {
  key: 'signature_name',
  label: 'Ondertekend door',
  dataType: 'string',
  inputType: 'text',
  group: 'administrative',
  permissions: {
    view: ['System_CRUD_All', 'Members_CRUD_All', 'National_Secretary'],
    edit: ['System_CRUD_All', 'National_Secretary']
  },
  helpText: 'Naam van persoon die het formulier heeft ondertekend'
},

signatureDate: {
  key: 'signature_date',
  label: 'Datum ondertekening',
  dataType: 'date',
  inputType: 'date',
  group: 'administrative',
  permissions: {
    view: ['System_CRUD_All', 'Members_CRUD_All', 'National_Secretary'],
    edit: ['System_CRUD_All', 'National_Secretary']
  },
  helpText: 'Datum waarop het formulier is ondertekend'
},

agreementAcknowledged: {
  key: 'agreement_acknowledged',
  label: 'Akkoord bevestigd',
  dataType: 'boolean',
  inputType: 'select',
  group: 'administrative',
  enumOptions: ['Ja', 'Nee'],
  permissions: {
    view: ['System_CRUD_All', 'Members_CRUD_All', 'National_Secretary'],
    edit: ['System_CRUD_All', 'National_Secretary']
  },
  helpText: 'Of de persoon akkoord is gegaan met de voorwaarden'
}
```

#### Option 3: Audit Trail System (Advanced Implementation)

```typescript
// Separate audit/signature table for comprehensive tracking
interface SignatureRecord {
  id: string;
  member_id: string;
  signature_type: 'MEMBERSHIP_APPLICATION' | 'PRIVACY_CONSENT' | 'TERMS_CONDITIONS';
  signed_by: string;
  signature_date: Date;
  signature_method: 'PAPER' | 'DIGITAL' | 'IMPORTED';
  document_version: string;
  ip_address?: string;
  user_agent?: string;
  witness?: string;
  notes?: string;
  created_at: Date;
}
```

### Recommended Implementation Strategy

**Phase 1 (Immediate - 2026 Import):**
- Use enhanced notities field with structured format
- Format: `[SIGNATURE] Signed by: John Doe | Date: 2025-01-01 | Details: Paper form`
- Preserves all historical signature information
- No schema changes required

**Phase 2 (Future Enhancement):**
- Add dedicated signature fields to member schema
- Create migration script to extract from notities
- Enhanced UI for signature management

**Phase 3 (Advanced - If Needed):**
- Implement comprehensive audit trail system
- Digital signature integration
- Legal compliance features

### Expected Results

```
Email: member@example.com
Notities: "General notes\n[SIGNATURE] Signed by: John Doe | Date: 2025-01-01 | Details: Paper membership form"

Email: bestuur@h-dcn.nl
Notities: "[BOARD] Voorzitter | Since: 2020-01-01\n[SIGNATURE] Signed by: Jane Smith | Date: 2024-12-15"
```

This approach ensures **legal compliance**, **data preservation**, and provides a **clear upgrade path** for future signature management enhancements.
        }

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def log_issue(self, severity: str, category: str, record_id: str,
                  field: str, issue: str, original_value: str = None,
                  corrected_value: str = None, row_number: int = None):
        """
        Log a data quality issue

        Args:
            severity: 'CRITICAL', 'WARNING', 'INFO'
            category: 'VALIDATION', 'MAPPING', 'MISSING_DATA', 'FORMAT', 'BUSINESS_RULE'
            record_id: Identifier for the record (lidnummer, email, etc.)
            field: Field name where issue occurred
            issue: Description of the issue
            original_value: Original value from CSV
            corrected_value: Value after correction (if applicable)
            row_number: CSV row number
        """
        issue_record = {
            'timestamp': datetime.now().isoformat(),
            'severity': severity,
            'category': category,
            'record_id': record_id,
            'field': field,
            'issue': issue,
            'original_value': original_value,
            'corrected_value': corrected_value,
            'row_number': row_number
        }

        self.issues.append(issue_record)

        # Update statistics
        if severity == 'CRITICAL':
            self.stats['critical_errors'] += 1
        elif severity == 'WARNING':
            self.stats['warnings'] += 1

        if corrected_value is not None:
            self.stats['data_corrections'] += 1

        # Log to file
        log_message = f"[{severity}] {category} - Record: {record_id} | Field: {field} | Issue: {issue}"
        if original_value:
            log_message += f" | Original: '{original_value}'"
        if corrected_value:
            log_message += f" | Corrected: '{corrected_value}'"
        if row_number:
            log_message += f" | Row: {row_number}"

        self.logger.info(log_message)

    def generate_report(self, output_file: str = "data_quality_report.json"):
        """Generate comprehensive data quality report"""
        report = {
            'summary': self.stats,
            'issues_by_severity': self._group_by_severity(),
            'issues_by_category': self._group_by_category(),
            'issues_by_field': self._group_by_field(),
            'detailed_issues': self.issues,
            'recommendations': self._generate_recommendations()
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def _group_by_severity(self):
        groups = {'CRITICAL': [], 'WARNING': [], 'INFO': []}
        for issue in self.issues:
            groups[issue['severity']].append(issue)
        return groups

    def _group_by_category(self):
        groups = {}
        for issue in self.issues:
            category = issue['category']
            if category not in groups:
                groups[category] = []
            groups[category].append(issue)
        return groups

    def _group_by_field(self):
        groups = {}
        for issue in self.issues:
            field = issue['field']
            if field not in groups:
                groups[field] = []
            groups[field].append(issue)
        return groups

    def _generate_recommendations(self):
        recommendations = []

        # Check for common patterns
        field_issues = self._group_by_field()

        for field, issues in field_issues.items():
            if len(issues) > 5:  # Many issues in same field
                recommendations.append({
                    'type': 'FIELD_VALIDATION',
                    'field': field,
                    'issue_count': len(issues),
                    'recommendation': f"Review validation rules for {field} - {len(issues)} issues found"
                })

        # Check for critical errors
        critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
        if critical_issues:
            recommendations.append({
                'type': 'MANUAL_REVIEW',
                'issue_count': len(critical_issues),
                'recommendation': f"Manual review required for {len(critical_issues)} critical errors"
            })

        return recommendations

# Enhanced processing function with data quality logging
def process_2026_csv_row_with_logging(row, row_number, logger: DataQualityLogger):
    """
    Enhanced processing with comprehensive data quality logging
    """
    processed_row = {}
    record_id = row.get('Lidnummer', f'Row_{row_number}')

    logger.stats['total_records'] += 1
    has_issues = False

    # Apply field mapping with validation
    for csv_field, db_field in field_mapping_2026.items():
        if csv_field in row and db_field:
            value = row[csv_field].strip() if row[csv_field] else None
            original_value = value

            # Validate and process each field
            try:
                if db_field == 'geboortedatum' and value:
                    processed_value = normalize_date_format(value)
                    if not processed_value:
                        logger.log_issue('CRITICAL', 'FORMAT', record_id, db_field,
                                       'Invalid date format', original_value, None, row_number)
                        has_issues = True
                        continue
                    elif processed_value != value:
                        logger.log_issue('INFO', 'FORMAT', record_id, db_field,
                                       'Date format normalized', original_value, processed_value, row_number)
                    processed_row[db_field] = processed_value

                elif db_field == 'email' and value:
                    processed_value = validate_and_clean_email(value)
                    if processed_value == 'test@h-dcn.nl':
                        logger.log_issue('WARNING', 'VALIDATION', record_id, db_field,
                                       'Invalid email, using fallback', original_value, processed_value, row_number)
                        has_issues = True
                    processed_row[db_field] = processed_value

                elif db_field == 'lidnummer' and value:
                    processed_value = process_lidnummer(value)
                    if not processed_value:
                        logger.log_issue('CRITICAL', 'VALIDATION', record_id, db_field,
                                       'Invalid lidnummer format', original_value, None, row_number)
                        has_issues = True
                        continue
                    processed_row[db_field] = processed_value

                elif db_field == 'lidmaatschap' and value:
                    processed_value = lidmaatschap_value_mapping.get(value, value)
                    if processed_value != value:
                        logger.log_issue('INFO', 'MAPPING', record_id, db_field,
                                       'Lidmaatschap value mapped', original_value, processed_value, row_number)

                    # Check for invalid membership types
                    valid_memberships = ['Gewoon lid', 'Gezins lid', 'Donateur', 'Gezins donateur', 'Erelid', 'Overig']
                    if processed_value not in valid_memberships:
                        logger.log_issue('WARNING', 'VALIDATION', record_id, db_field,
                                       'Unknown membership type', original_value, processed_value, row_number)
                        has_issues = True

                    processed_row[db_field] = processed_value

                elif db_field == 'regio' and value:
                    processed_value = regio_value_mapping.get(value, value)
                    if processed_value != value:
                        logger.log_issue('INFO', 'MAPPING', record_id, db_field,
                                       'Regio value mapped', original_value, processed_value, row_number)

                    # Special logging for data errors (gender in regio field)
                    if value in ['Man', 'Vrouw']:
                        logger.log_issue('WARNING', 'VALIDATION', record_id, db_field,
                                       'Gender value found in regio field', original_value, processed_value, row_number)
                        has_issues = True

                    processed_row[db_field] = processed_value

                elif db_field == 'geslacht' and value:
                    processed_value = normalize_gender(value)
                    if processed_value != value:
                        logger.log_issue('INFO', 'MAPPING', record_id, db_field,
                                       'Gender value normalized', original_value, processed_value, row_number)
                    processed_row[db_field] = processed_value

                else:
                    processed_row[db_field] = value

            except Exception as e:
                logger.log_issue('CRITICAL', 'VALIDATION', record_id, db_field,
                               f'Processing error: {str(e)}', original_value, None, row_number)
                has_issues = True

    # Validate required fields
    required_fields = ['voornaam', 'achternaam', 'email', 'lidmaatschap', 'regio']
    for field in required_fields:
        if not processed_row.get(field):
            logger.log_issue('CRITICAL', 'MISSING_DATA', record_id, field,
                           'Required field is missing or empty', None, None, row_number)
            has_issues = True

    # Business rule validations
    email = processed_row.get('email', '')

    # Check for @h-dcn.nl accounts without board function
    if email.endswith('@h-dcn.nl'):
        bestuursfunctie = row.get('Bestuursfunctie', '').strip()
        if not bestuursfunctie:
            logger.log_issue('WARNING', 'BUSINESS_RULE', record_id, 'bestuursfunctie',
                           '@h-dcn.nl account without board function', None, None, row_number)

    # Generate computed fields
    processed_row['member_id'] = str(uuid.uuid4())
    processed_row['created_at'] = datetime.now().isoformat()
    processed_row['updated_at'] = datetime.now().isoformat()

    # Special status determination for "Clubblad" records
    clubblad_value = row.get('Clubblad', '').strip()
    lidmaatschap_value = row.get('Soort lidmaatschap', '').strip()
    processed_row['status'] = determine_status_for_clubblad_records(clubblad_value, lidmaatschap_value)

    # Process board member information for @h-dcn.nl accounts
    processed_row = process_board_member_info(row, processed_row)

    # Build full name
    name_parts = [
        processed_row.get('voornaam', ''),
        processed_row.get('tussenvoegsel', ''),
        processed_row.get('achternaam', '')
    ]
    processed_row['name'] = ' '.join(filter(None, name_parts))

    # Update statistics
    if has_issues:
        logger.stats['records_with_issues'] += 1
    else:
        logger.stats['successful_imports'] += 1

    return processed_row

# Main import function with logging
def import_2026_csv_with_logging(csv_file_path: str):
    """
    Main import function with comprehensive data quality logging
    """
    logger = DataQualityLogger(f"migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logger.logger.info(f"Starting import of {csv_file_path}")

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)

            for row_number, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
                try:
                    processed_row = process_2026_csv_row_with_logging(row, row_number, logger)

                    # Here you would normally insert into database
                    # insert_member_record(processed_row)

                    if row_number % 50 == 0:
                        logger.logger.info(f"Processed {row_number} records...")

                except Exception as e:
                    logger.log_issue('CRITICAL', 'VALIDATION', f'Row_{row_number}', 'general',
                                   f'Row processing failed: {str(e)}', None, None, row_number)

    except Exception as e:
        logger.logger.error(f"Import failed: {str(e)}")
        return None

    # Generate final report
    report = logger.generate_report(f"data_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    logger.logger.info("Import completed. Summary:")
    logger.logger.info(f"Total records: {logger.stats['total_records']}")
    logger.logger.info(f"Successful imports: {logger.stats['successful_imports']}")
    logger.logger.info(f"Records with issues: {logger.stats['records_with_issues']}")
    logger.logger.info(f"Critical errors: {logger.stats['critical_errors']}")
    logger.logger.info(f"Warnings: {logger.stats['warnings']}")
    logger.logger.info(f"Data corrections: {logger.stats['data_corrections']}")

    return report
````

### Data Quality Report Structure

The system generates two types of output:

#### 1. Real-time Log File (`migration_log_YYYYMMDD_HHMMSS.log`)

```
2026-01-06 14:30:15 - INFO - [WARNING] VALIDATION - Record: 6539 | Field: regio | Issue: Gender value found in regio field | Original: 'Man' | Corrected: 'Other' | Row: 15
2026-01-06 14:30:16 - INFO - [CRITICAL] VALIDATION - Record: 6540 | Field: email | Issue: Invalid email format | Original: 'invalid-email' | Row: 16
2026-01-06 14:30:17 - INFO - [INFO] MAPPING - Record: 6541 | Field: lidmaatschap | Issue: Lidmaatschap value mapped | Original: 'Donateur zonder motor' | Corrected: 'Donateur' | Row: 17
```

#### 2. Structured JSON Report (`data_quality_report_YYYYMMDD_HHMMSS.json`)

```json
{
  "summary": {
    "total_records": 1195,
    "successful_imports": 1150,
    "records_with_issues": 45,
    "critical_errors": 5,
    "warnings": 25,
    "data_corrections": 15
  },
  "issues_by_severity": {
    "CRITICAL": [...],
    "WARNING": [...],
    "INFO": [...]
  },
  "issues_by_category": {
    "VALIDATION": [...],
    "MAPPING": [...],
    "MISSING_DATA": [...],
    "FORMAT": [...],
    "BUSINESS_RULE": [...]
  },
  "issues_by_field": {
    "email": [...],
    "regio": [...],
    "geboortedatum": [...]
  },
  "recommendations": [
    {
      "type": "MANUAL_REVIEW",
      "issue_count": 5,
      "recommendation": "Manual review required for 5 critical errors"
    }
  ]
}
```

### Usage Instructions

```python
# Run import with logging
report = import_2026_csv_with_logging("HDCN Ledenbestand 2026 - Ledenbestand.csv")

# Review critical issues that need manual attention
critical_issues = report['issues_by_severity']['CRITICAL']
for issue in critical_issues:
    print(f"Row {issue['row_number']}: {issue['issue']} - {issue['original_value']}")
```

This comprehensive logging system will help identify all data quality issues that require manual review and correction.

````

### Updated Field Mapping Logic for 2026 CSV

```python
# Complete field mapping for 2026 Google Sheets structure (49 columns)
field_mapping_2026 = {
    # Successfully mapped fields (27 total)
    'Tijdstempel': 'tijdstempel',                    # Col 0
    'Lidnummer': 'lidnummer',                        # Col 1
    'Achternaam': 'achternaam',                      # Col 2
    'Initialen': 'initialen',                       # Col 3
    'Voornaam': 'voornaam',                          # Col 4
    'Tussenvoegsel': 'tussenvoegsel',               # Col 5
    'Straat en huisnummer': 'straat',               # Col 7
    'Postcode': 'postcode',                         # Col 8
    'Woonplaats': 'woonplaats',                     # Col 9
    'Land': 'land',                                  # Col 10
    'Telefoonnummer': 'telefoon',                   # Col 11
    'E-mailadres': 'email',                         # Col 12 (primary)
    'Geboorte datum': 'geboortedatum',              # Col 13 (use this, not 14-16)
    'Geslacht': 'geslacht',                         # Col 17
    'Regio': 'regio',                               # Col 18
    'Clubblad': 'clubblad',                         # Col 21 (primary)
    'Soort lidmaatschap': 'lidmaatschap',           # Col 22
    'Bouwjaar': 'bouwjaar',                         # Col 23
    'Motormerk': 'motormerk',                       # Col 24
    'Type motor': 'motortype',                      # Col 25
    'Kenteken': 'kenteken',                         # Col 26
    'WieWatWaar': 'wiewatwaar',                     # Col 27
    'Bankrekeningnummer': 'bankrekeningnummer',     # Col 28
    'Datum ondertekening': 'datum_ondertekening',   # Col 30
    'Aanmeldingsjaar': 'aanmeldingsjaar',           # Col 31
    'Digitale nieuwsbrieven': 'nieuwsbrief',        # Col 36
    'Opmerkingen': 'notities',                      # Col 47 (NEW in 2026)
}

# Board member information processing (for @h-dcn.nl accounts)
board_info_fields = {
    'Bestuursfunctie': 'board_function_temp',       # Col 19 - processed separately
    'in functie sinds': 'board_since_temp'          # Col 20 - processed separately
}

# Special value mappings for enum fields
lidmaatschap_value_mapping = {
    'Donateur zonder motor': 'Donateur',
    'Gezins Donateur zonder motor': 'Gezins donateur',
    'Gewoon lid': 'Gewoon lid',
    'Gezins lid': 'Gezins lid',
    'Ere lid': 'Erelid',  # Note: different spelling in CSV
    'Clubblad': 'Overig'  # Clubblad is not a valid membership type, map to Overig
}

# Regio value mappings for CSV to database consistency
regio_value_mapping = {
    'Noord Holland': 'Noord-Holland',           # Add hyphen
    'Zuid Holland': 'Zuid-Holland',             # Add hyphen
    'Friesland': 'Friesland',                   # Exact match
    'Utrecht': 'Utrecht',                       # Exact match
    'Oost': 'Oost',                            # Exact match
    'Limburg': 'Limburg',                      # Exact match
    'Groningen/Drente': 'Groningen/Drenthe',   # Fix spelling: Drente -> Drenthe
    'Brabant/Zeeland': 'Brabant/Zeeland',        # Map combined region to Noord-Brabant
    'Zeeland': 'Brabant/Zeeland',                      # Exact match (if exists separately)
    'Duitsland': 'Duitsland',                  # Valid H-DCN region
    'Geen': 'Overig',                          # No region specified -> Overig
    # Data errors - column shift issues (birth year in geslacht, gender in regio)
    # These rows have data integrity issues and need manual review
    # 'Man': 'Other',     # Remove - this is a data shift error
    # 'Vrouw': 'Other',   # Remove - this is a data shift error
    # 'M': 'Other',       # Remove - this is a data shift error
    # 'V': 'Other',       # Remove - this is a data shift error
    # Add any other international regions found
    'België': 'Other',
    'Belgie': 'Other',
    'Germany': 'Other',
    'International': 'Other'
}

# Special status mapping rules for records with "Clubblad" in Soort lidmaatschap
def determine_status_for_clubblad_records(clubblad_value, lidmaatschap_value):
    """
    Special logic for records where 'Soort lidmaatschap' = 'Clubblad'
    These get lidmaatschap = 'Overig' and status determined by Clubblad preference
    """
    if lidmaatschap_value == 'Clubblad':
        if clubblad_value == 'Papier':
            return 'Sponsor'
        elif clubblad_value == 'Digitaal':
            return 'Club'
        else:
            return 'Actief'  # Default fallback
    else:
        return 'Actief'  # Default status for normal memberships

# Fields to skip during import (duplicates and empty columns)
skip_columns = [
    'Geboortedag',           # Col 14 - redundant
    'Geboortemaand',         # Col 15 - redundant
    'Geboortejaar',          # Col 16 - redundant
    'H-DCN Clubblad',        # Col 29, 35 - duplicates
    'E-mailadres',           # Col 34 - duplicate
    'E-Mail',                # Col 45 - duplicate
    'Email Address',         # Col 46 - duplicate
    '',                      # Col 38, 48 - empty columns
]

# Future consideration fields (not implemented yet)
future_fields = {
    'Gezinslid': 'family_member_ref',        # Col 6
    'Bestuursfunctie': 'board_function',     # Col 19
    'in functie sinds': 'board_since',       # Col 20
    'Ondertekening': 'signature_info',       # Col 32
    'Naam voor akkoord': 'signature_name',   # Col 33
    'Lidmaatschapsnummer': 'membership_alt_id', # Col 37
    'Afmelding': 'cancellation_info',        # Col 39
    'Beeindiging': 'termination_info',       # Col 40
    'Jubilaris': 'anniversary_status',       # Col 41
    'Bedrag': 'fee_amount',                  # Col 42
    'Inschrijfformulier': 'form_version',    # Col 43
    'KorteNaam': 'short_name',               # Col 44
}

# Data processing improvements for 2026
def process_2026_csv_row(row):
    """
    Enhanced processing for 2026 CSV format
    """
    processed_row = {}

    # Apply field mapping
    for csv_field, db_field in field_mapping_2026.items():
        if csv_field in row and db_field:
            value = row[csv_field].strip() if row[csv_field] else None

            # Special processing for specific fields
            if db_field == 'geboortedatum' and value:
                # Ensure date format consistency
                processed_row[db_field] = normalize_date_format(value)
            elif db_field == 'email' and value:
                # Enhanced email validation
                processed_row[db_field] = validate_and_clean_email(value)
            elif db_field == 'lidnummer' and value:
                # Handle mixed lidnummer formats (numbers vs "Donateur")
                processed_row[db_field] = process_lidnummer(value)
            elif db_field == 'lidmaatschap' and value:
                # Map CSV lidmaatschap values to database values
                processed_row[db_field] = lidmaatschap_value_mapping.get(value, value)
            elif db_field == 'regio' and value:
                # Map CSV regio values to database values
                processed_row[db_field] = regio_value_mapping.get(value, value)
            elif db_field == 'geslacht' and value:
                # Normalize gender values
                processed_row[db_field] = normalize_gender(value)
            else:
                processed_row[db_field] = value

    # Generate computed fields
    processed_row['member_id'] = str(uuid.uuid4())
    processed_row['created_at'] = datetime.now().isoformat()
    processed_row['updated_at'] = datetime.now().isoformat()

    # Special status determination for records with "Clubblad" in Soort lidmaatschap
    clubblad_value = row.get('Clubblad', '').strip()
    lidmaatschap_value = row.get('Soort lidmaatschap', '').strip()
    processed_row['status'] = determine_status_for_clubblad_records(clubblad_value, lidmaatschap_value)

    # Process board member information for @h-dcn.nl accounts
    processed_row = process_board_member_info(row, processed_row)

    # Build full name
    name_parts = [
        processed_row.get('voornaam', ''),
        processed_row.get('tussenvoegsel', ''),
        processed_row.get('achternaam', '')
    ]
    processed_row['name'] = ' '.join(filter(None, name_parts))

    return processed_row

def process_lidnummer(value):
    """
    Handle different lidnummer formats in 2026 CSV
    """
    if not value:
        return None

    # Handle "Donateur" entries
    if 'Donateur' in value:
        # Extract number if present (e.g., "6539 Donateur" -> 6539)
        import re
        match = re.search(r'(\d+)', value)
        return int(match.group(1)) if match else None

    # Handle pure numbers
    try:
        return int(value)
    except ValueError:
        return None

def normalize_gender(value):
    """
    Normalize gender values to standard format
    """
    if not value:
        return None

    value = value.lower().strip()
    if value in ['man', 'm', 'male']:
        return 'M'
    elif value in ['vrouw', 'v', 'female']:
        return 'V'
    else:
        return 'X'  # Unknown/other

def validate_and_clean_email(email):
    """
    Enhanced email validation and cleaning
    """
    if not email or email.strip() == '':
        return 'test@h-dcn.nl'  # Fallback email

    email = email.strip().lower()

    # Basic email validation
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if re.match(email_pattern, email):
        return email
    else:
        print(f"Invalid email format: {email}, using fallback")
        return 'test@h-dcn.nl'

def normalize_date_format(date_str):
    """
    Normalize various date formats to consistent format
    """
    if not date_str:
        return None

    # Handle different date formats
    import datetime

    formats_to_try = [
        '%d-%m-%Y',    # 29-11-1971
        '%d/%m/%Y',    # 29/11/1971
        '%Y-%m-%d',    # 1971-11-29
        '%d-%m-%y',    # 29-11-71
        '%d/%m/%y'     # 29/11/71
    ]

    for fmt in formats_to_try:
        try:
            parsed_date = datetime.datetime.strptime(date_str.strip(), fmt)
            return parsed_date.strftime('%Y-%m-%d')  # Return in ISO format
        except ValueError:
            continue

    print(f"Could not parse date: {date_str}")
    return None
````

## Migration Strategy for 2026 CSV

### Pre-Migration Database Cleanup

**⚠️ CRITICAL: Execute these steps BEFORE running the 2026 import**

#### Step 1: Backup Current Database

```sql
-- Create backup of current Members table
CREATE TABLE Members_Backup_Pre2026 AS SELECT * FROM Members;

-- Verify backup
SELECT COUNT(*) as total_records FROM Members_Backup_Pre2026;
```

#### Step 2: Preserve @h-dcn.nl Accounts

```sql
-- First, verify which @h-dcn.nl accounts will be preserved
SELECT member_id, email, voornaam, achternaam, status
FROM Members
WHERE email LIKE '%@h-dcn.nl'
  AND email != 'test@h-dcn.nl'
ORDER BY email;

-- Expected accounts to preserve:
-- - voorzitter@h-dcn.nl
-- - secretaris@h-dcn.nl
-- - penningmeester@h-dcn.nl
-- - etc.
```

#### Step 3: Delete Records for Fresh Import

```sql
-- Delete all records EXCEPT @h-dcn.nl accounts (but keep functional accounts)
DELETE FROM Members
WHERE email NOT LIKE '%@h-dcn.nl'
   OR email = 'test@h-dcn.nl';

-- Verify deletion
SELECT
    COUNT(*) as remaining_records,
    COUNT(CASE WHEN email LIKE '%@h-dcn.nl' THEN 1 END) as hdcn_accounts,
    COUNT(CASE WHEN email = 'test@h-dcn.nl' THEN 1 END) as test_accounts
FROM Members;

-- Expected result:
-- - remaining_records: 5-10 (only real @h-dcn.nl accounts)
-- - hdcn_accounts: 5-10 (same as remaining)
-- - test_accounts: 0 (all test accounts deleted)
```

#### Step 4: Verification Before Import

```sql
-- Final verification - list all remaining accounts
SELECT member_id, email, voornaam, achternaam, status, lidmaatschap
FROM Members
ORDER BY email;

-- All remaining records should be legitimate @h-dcn.nl functional accounts
-- No test@h-dcn.nl accounts should remain
```

### Phase 1: Core Data Migration

Import the 27 successfully mapped fields using the existing import script with updated field mapping.

**Fields to Import:**

- All 26 original fields from 2025 import
- **NEW**: `Opmerkingen` → `notities` (administrative notes)

### Phase 2: Data Quality Improvements

Enhanced validation and processing for 2026 data:

1. **Lidnummer Handling**: Process mixed formats ("6539 Donateur" vs pure numbers)
2. **Email Validation**: Improved validation with fallback handling
3. **Date Normalization**: Handle various date formats consistently
4. **Gender Normalization**: Standardize "Man"/"Vrouw" to "M"/"V"

### Phase 3: Future Enhancements (Optional)

Consider adding new fields to database schema:

**High Priority:**

- `Bestuursfunctie` + `in functie sinds` - Board member tracking
- `Jubilaris` - Anniversary member status
- `Gezinslid` - Family member relationships

**Medium Priority:**

- `Bedrag` - Fee/payment tracking
- `KorteNaam` - Nickname/display name
- Signature tracking fields

### Post-Migration Verification

#### Step 1: Data Integrity Checks

```sql
-- Verify import results
SELECT
    COUNT(*) as total_members,
    COUNT(CASE WHEN email LIKE '%@h-dcn.nl' THEN 1 END) as hdcn_accounts,
    COUNT(CASE WHEN email = 'test@h-dcn.nl' THEN 1 END) as fallback_emails,
    COUNT(CASE WHEN status = 'Actief' THEN 1 END) as active_members,
    COUNT(CASE WHEN status = 'Sponsor' THEN 1 END) as sponsors,
    COUNT(CASE WHEN status = 'Club' THEN 1 END) as club_members
FROM Members;
```

#### Step 2: Validate Key Data Quality

```sql
-- Check for missing required data
SELECT 'Missing Names' as issue, COUNT(*) as count
FROM Members
WHERE voornaam IS NULL OR achternaam IS NULL OR TRIM(voornaam) = '' OR TRIM(achternaam) = ''

UNION ALL

SELECT 'Invalid Emails' as issue, COUNT(*) as count
FROM Members
WHERE email IS NULL OR email NOT LIKE '%@%.%'

UNION ALL

SELECT 'Missing Regions' as issue, COUNT(*) as count
FROM Members
WHERE regio IS NULL OR regio = ''

UNION ALL

SELECT 'Invalid Membership Types' as issue, COUNT(*) as count
FROM Members
WHERE lidmaatschap NOT IN ('Gewoon lid', 'Gezins lid', 'Donateur', 'Gezins donateur', 'Erelid', 'Overig');
```

#### Step 3: Board Member Verification

```sql
-- Verify board member information was preserved and enhanced
SELECT
    email,
    voornaam,
    achternaam,
    status,
    lidmaatschap,
    CASE
        WHEN notities LIKE '%[BOARD]%' THEN 'Board info preserved'
        ELSE 'No board info'
    END as board_status,
    notities
FROM Members
WHERE email LIKE '%@h-dcn.nl'
ORDER BY email;
```

#### Step 4: Sample Data Verification

```sql
-- Random sample check for data quality
SELECT
    lidnummer,
    voornaam,
    achternaam,
    email,
    regio,
    status,
    lidmaatschap,
    CASE WHEN notities LIKE '%[SIGNATURE]%' THEN 'Has signature' ELSE 'No signature' END as signature_info
FROM Members
WHERE email NOT LIKE '%@h-dcn.nl'
ORDER BY RANDOM()
LIMIT 10;
```

## Usage Instructions

### ⚠️ IMPORTANT: Pre-Migration Steps Required

**BEFORE running the 2026 import, you MUST execute the database cleanup steps outlined in the "Pre-Migration Database Cleanup" section above.**

### Running the 2026 Import

```bash
cd backend/scripts
python import_members_2026.py "path/to/HDCN Ledenbestand 2026 - Ledenbestand.csv"
```

### Updated Script Configuration

The script should be updated to handle 2026 format:

```python
# Update the CSV file path for 2026
csv_file = "path/to/HDCN Ledenbestand 2026 - Ledenbestand.csv"

# Use the updated field mapping
field_mapping = field_mapping_2026

# Enable enhanced processing
use_enhanced_processing = True
```

### Prerequisites

**For Google Sheets API (Recommended):**

- Google Cloud project with Sheets API enabled
- Service account credentials configured in `.googleCredentials.json`
- Google Sheet shared with service account email
- Python dependencies installed: `pip install -r backend/requirements.txt`

**For CSV Import (Legacy):**

- AWS credentials configured
- CSV file downloaded from Google Sheets
- DynamoDB table 'Members' exists
- Python dependencies: boto3, csv, uuid, datetime

**Common Requirements:**

- AWS credentials with DynamoDB write permissions
- DynamoDB table 'Members' exists in eu-west-1 region

## Recommendations for 2026 Import

### 1. Immediate Actions (Ready to Implement)

**Use Enhanced Field Mapping:**

- Import 27 fields (26 original + `Opmerkingen`)
- Apply improved data validation and normalization
- Handle mixed lidnummer formats properly

**Data Quality Improvements:**

- Implement enhanced email validation with fallbacks
- Normalize date formats consistently
- Normalize enum fields like regio, geslacht, status, lidmaatschap
- Standardize gender values ("Man"/"Vrouw" → "M"/"V")

### 2. Database Schema Enhancements (Future Consideration)

**Medium Priority Fields:**

```sql
-- Administrative tracking
ALTER TABLE Members ADD COLUMN signature_info TEXT;
ALTER TABLE Members ADD COLUMN form_version VARCHAR(20);
```

### 3. Import Script Updates

**Create Updated Import Script:**

- Copy `import_members.py` to `import_members_2026.py`
- Update field mapping to `field_mapping_2026`
- Add enhanced processing functions
- Implement better error handling and logging

**Validation Improvements:**

- Pre-import data quality report
- Duplicate detection across email fields
- Lidnummer format validation
- Date format consistency checks

### 4. Data Migration Best Practices

**Before Import:**

1. Backup existing member data
2. Run data quality analysis on CSV
3. Test import with small sample (first 10-20 records)
4. Validate field mappings against current schema

**During Import:**

1. Monitor import progress and error rates
2. Log all data transformations and fallbacks
3. Track skipped/problematic records
4. Validate critical fields (email, lidnummer, names)

**After Import:**

1. Run data integrity checks
2. Compare record counts and key statistics
3. Validate sample records manually
4. Update member statistics and reports

### 5. Future Data Management

**Standardize CSV Format:**

- Work with data source to eliminate duplicate columns
- Establish consistent date formats
- Standardize enum values (gender, membership types)
- Document required vs optional fields

**Enhanced Validation Rules:**

- Implement real-time validation for new member registrations
- Add data quality monitoring and alerts
- Create automated data consistency reports
- Establish data governance procedures

## Migration History

### Original Import (2025)

- **Source**: HDCN Ledenbestand 2025 - Ledenbestand.csv
- **Fields Mapped**: 26 core fields
- **Records**: [Number of records imported]
- **Date**: [Import date]
- **Status**: Successful with [X] errors, [Y] skipped records

### Updated Import (2026)

- **Source**: HDCN Ledenbestand 2026 - Ledenbestand.csv
- **Fields Mapped**: 27 fields (added `Opmerkingen` → `notities`)
- **New Fields Available**: 18 additional fields for future consideration
- **Records**: [To be determined]
- **Date**: [Pending import]
- **Status**: Ready for import with enhanced processing

### Key Differences Between 2025 and 2026

**Added Fields in 2026:**

- `Opmerkingen` - Now mappable to `notities` field
- `Gezinslid` - Family member references Store in Notities
- `Bestuursfunctie` + `in functie sinds` - Board member tracking (FUTURE)
- `Jubilaris` - Anniversary member status (Function)
- Various administrative fields for signature and termination tracking

**Data Quality Improvements:**

- Better handling of mixed lidnummer formats
- Enhanced email validation
- Improved date format normalization
- Gender value standardization

**Duplicate Fields Identified:**

- `H-DCN Clubblad` (duplicate of `Clubblad`)
- `E-Mail` and `Email Address` (duplicates of `E-mailadres`)
- Separate birth date components (redundant with full date)

### Field Evolution

The member schema has evolved since the original import:

1. **Added**: Role-based enum permissions (Erelid, Other options)
2. **Added**: Enhanced validation rules
3. **Added**: Conditional field visibility
4. **Added**: Self-service permissions

## Technical Notes

### Database Configuration

- **Table**: Members (DynamoDB)
- **Region**: eu-west-1
- **Primary Key**: member_id (UUID)
- **Indexes**: [List any GSI/LSI if applicable]

### Performance Considerations

- **Batch Size**: Processes records individually (consider batch operations for large imports)
- **Rate Limiting**: No rate limiting implemented (may need for large datasets)
- **Memory Usage**: Loads entire CSV into memory (consider streaming for very large files)

### Security Considerations

- **Email Fallbacks**: Leave empty invalid emails. No invalid e-mails
- **Data Sanitization**: Basic input cleaning implemented
- **Access Control**: Requires AWS credentials with DynamoDB write permissions

## Troubleshooting

### Common Issues

1. **AWS Credentials**: Ensure proper AWS configuration
2. **Table Permissions**: Verify DynamoDB write permissions
3. **File Encoding**: CSV must be UTF-8 encoded
4. **Column Headers**: Headers must match exactly (case-sensitive)

### Error Recovery

- Script continues processing after individual record errors
- Check logs for specific error details
- Re-run import with corrected data if needed

## Related Documentation

- [Member Field Registry](../steering/member-field-registry.md)
- [Look and Feel Guidelines](../steering/look-and-feel.md)
- [Permission System](../steering/permission-system.md)

## Mapping

lidmaatschap_mapping = {
'Donateur zonder motor': 'Donateur',
'Gezins Donateur zonder motor': 'Gezins donateur',
'Gewoon lid': 'Gewoon lid',
'Gezins lid': 'Gezins lid'
}
