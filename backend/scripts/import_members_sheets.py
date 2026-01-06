#!/usr/bin/env python3
"""
H-DCN Member Google Sheets Import Script v2.0
Direct import from Google Sheets to DynamoDB with enhanced data quality

CHANGELOG v2.0 (2026-01-06):
- Fixed region mapping: 'Other' → 'Overig' to match memberFields.ts
- Fixed business rule logging to show correct original/corrected values
- Enhanced email validation: empty emails stay empty (no test@h-dcn.nl fallback)
- Added Dutch "no email" indicators detection
- Improved duplicate header handling
- Enhanced data quality reporting
- Added comprehensive validation against memberFields.ts enum values
"""

import gspread
from google.oauth2.service_account import Credentials
import boto3
import uuid
from datetime import datetime
import sys
import os
import json
from typing import Dict, List, Any, Optional

# Configure AWS
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')

class DataQualityLogger:
    """Enhanced data quality logging for migration issues"""
    
    def __init__(self):
        self.issues = []
        self.stats = {
            'CRITICAL': 0,
            'WARNING': 0,
            'INFO': 0,
            'CORRECTION': 0
        }
    
    def log_issue(self, severity: str, category: str, record_id: str, field: str, 
                  issue: str, original_value: str = '', corrected_value: str = ''):
        """Log a data quality issue"""
        self.issues.append({
            'timestamp': datetime.now().isoformat(),
            'severity': severity,
            'category': category,
            'record_id': record_id,
            'field': field,
            'issue': issue,
            'original_value': str(original_value),
            'corrected_value': str(corrected_value)
        })
        self.stats[severity] += 1
        
        # Print critical issues immediately
        if severity == 'CRITICAL':
            print(f"🚨 CRITICAL: {record_id} - {field}: {issue}")
    
    def save_report(self, filename: str = None):
        """Save detailed report to file"""
        if filename is None:
            filename = f'migration_data_quality_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        report = {
            'migration_info': {
                'version': '2.0',
                'timestamp': datetime.now().isoformat(),
                'script': 'import_members_sheets.py'
            },
            'summary': self.stats,
            'total_issues': len(self.issues),
            'issues': self.issues
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Data quality report saved to: {filename}")
        return report

# Initialize logger
logger = DataQualityLogger()

# VALID ENUM VALUES (matching memberFields.ts exactly)
VALID_REGIONS = [
    'Noord-Holland',
    'Zuid-Holland', 
    'Friesland',
    'Utrecht',
    'Oost',
    'Limburg',
    'Groningen/Drenthe',
    'Brabant/Zeeland',
    'Duitsland',
    'Overig'  # ✅ FIXED: Use 'Overig' not 'Other'
]

VALID_STATUSES = [
    'Actief', 'Opgezegd', 'wachtRegio', 'Aangemeld', 
    'Geschorst', 'HdcnAccount', 'Club', 'Sponsor', 'Overig'
]

VALID_MEMBERSHIPS = [
    'Gewoon lid', 'Gezins lid', 'Donateur', 
    'Gezins donateur', 'Erelid', 'Overig'
]

VALID_GENDERS = ['M', 'V', 'X', 'N']

# Regio value mappings - FIXED to match memberFields.ts exactly
regio_value_mapping = {
    # Standard region name corrections (add hyphens)
    'Noord Holland': 'Noord-Holland',
    'Zuid Holland': 'Zuid-Holland',
    
    # Spelling corrections
    'Groningen/Drente': 'Groningen/Drenthe',
    'Groningen/Drenthe': 'Groningen/Drenthe',  # Already correct
    
    # Regional mapping corrections - FIXED to match memberFields.ts
    'Brabant/Zeeland': 'Brabant/Zeeland',      # ✅ Keep as-is (correct in memberFields.ts)
    'Brabant': 'Brabant/Zeeland',
    'Noord-Brabant': 'Brabant/Zeeland',
    'Zeeland': 'Brabant/Zeeland',
    
    # International and special cases
    'Deutschland': 'Duitsland',
    'Germany': 'Overig',                        # ✅ FIXED: 'Other' → 'Overig'
    'Belgie': 'Overig',
    'Belgium': 'Overig',
    'Belgique': 'Overig',
    'Frankrijk': 'Overig',
    'France': 'Overig',
    'Oostenrijk': 'Overig',
    'Austria': 'Overig',
    'Zwitserland': 'Overig',
    'Switzerland': 'Overig',
    'Luxemburg': 'Overig',
    'Luxembourg': 'Overig',
    
    # No region specified - FIXED to match memberFields.ts
    'Geen': 'Overig',                          # ✅ FIXED: 'Other' → 'Overig'
    'Geen regio': 'Overig',
    'Onbekend': 'Overig',
    'Unknown': 'Overig',
    'N/A': 'Overig',
    'NA': 'Overig',
    
    # Alternative spellings and variations
    'Friesland/Frisia': 'Friesland',
    'Fryslân': 'Friesland',
    'Gelderland': 'Oost',
    'Overijssel': 'Oost',
    'Flevoland': 'Oost',
    'Drenthe': 'Groningen/Drenthe',
    'Groningen': 'Groningen/Drenthe',
    
    # Province to region mapping - FIXED to match memberFields.ts
    'Noord-Brabant': 'Brabant/Zeeland',        # ✅ Fixed mapping
    'Limburg': 'Limburg',                      # Already correct
    'Utrecht': 'Utrecht',                      # Already correct
    'Noord-Holland': 'Noord-Holland',          # Already correct
    'Zuid-Holland': 'Zuid-Holland',            # Already correct
    'Friesland': 'Friesland',                  # Already correct
    'Oost': 'Oost',                           # Already correct
    'Duitsland': 'Duitsland',                 # Already correct
    
    # Common misspellings
    'Noord-holland': 'Noord-Holland',
    'Zuid-holland': 'Zuid-Holland',
    'noord holland': 'Noord-Holland',
    'zuid holland': 'Zuid-Holland',
    'groningen/drente': 'Groningen/Drenthe',
    'GRONINGEN/DRENTHE': 'Groningen/Drenthe',
    'brabant/zeeland': 'Brabant/Zeeland',      # ✅ Fixed mapping
    'BRABANT/ZEELAND': 'Brabant/Zeeland',      # ✅ Fixed mapping
    
    # Empty or whitespace values - FIXED to match memberFields.ts
    '': 'Overig',                              # ✅ FIXED: 'Other' → 'Overig'
    ' ': 'Overig',                             # ✅ FIXED: 'Other' → 'Overig'
}

def validate_enum_value(value: str, valid_values: List[str], field_name: str, record_id: str) -> str:
    """Validate enum values against memberFields.ts definitions"""
    if value in valid_values:
        return value
    
    logger.log_issue('WARNING', 'VALIDATION', record_id, field_name,
                   f'Invalid {field_name} value - not in memberFields.ts enum',
                   value, 'Overig' if field_name == 'regio' else 'Actief')
    
    # Return safe default
    if field_name == 'regio':
        return 'Overig'
    elif field_name == 'status':
        return 'Actief'
    elif field_name == 'lidmaatschap':
        return 'Overig'
    elif field_name == 'geslacht':
        return 'X'
    else:
        return value

def load_google_credentials() -> Credentials:
    """Load Google service account credentials"""
    creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.googleCredentials.json')
    
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Google credentials not found at {creds_path}")
    
    # Define required scopes
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return credentials

def connect_to_sheet(sheet_name: str, worksheet_name: str = 'Ledenbestand') -> gspread.Worksheet:
    """Connect to Google Sheets and return worksheet"""
    try:
        credentials = load_google_credentials()
        gc = gspread.authorize(credentials)
        
        # Open the spreadsheet
        sheet = gc.open(sheet_name)
        worksheet = sheet.worksheet(worksheet_name)
        
        print(f"✅ Connected to Google Sheet: {sheet_name} -> {worksheet_name}")
        return worksheet
        
    except Exception as e:
        print(f"❌ Failed to connect to Google Sheet: {str(e)}")
        raise

def clean_email(email: str, record_id: str) -> str:
    """Clean and validate email addresses - FIXED to leave empty emails empty"""
    if not email or str(email).strip() == '' or str(email).strip().upper() == 'NA':
        logger.log_issue('INFO', 'EMAIL', record_id, 'email', 
                        'Empty email address - left blank', email, '')
        return ""
    
    email = str(email).strip()
    
    # Check for explicit "no email" indicators in Dutch - NEW FEATURE
    no_email_indicators = [
        'geen geldig emailadres',
        'geen email',
        'geen e-mail',
        'geen emailadres',
        'no email',
        'no e-mail',
        'nvt',
        'n.v.t.',
        'onbekend'
    ]
    
    if email.lower() in no_email_indicators:
        logger.log_issue('INFO', 'EMAIL', record_id, 'email', 
                        'No valid email indicator - left blank', email, '')
        return ""
    
    # Basic email validation
    if '@' in email and '.' in email and len(email) > 5:
        return email
    
    # Invalid email format - leave empty (FIXED: no more test@h-dcn.nl fallback)
    logger.log_issue('WARNING', 'EMAIL', record_id, 'email', 
                    'Invalid email format - left blank', email, '')
    return ""

def detect_column_shift(row: List[str], headers: List[str], record_id: str) -> bool:
    """Detect potential column shift issues"""
    if len(row) < len(headers):
        return False
    
    # Check for common column shift patterns
    geslacht_idx = None
    regio_idx = None
    
    for i, header in enumerate(headers):
        if header.strip() == 'Geslacht':
            geslacht_idx = i
        elif header.strip() == 'Regio':
            regio_idx = i
    
    if geslacht_idx is not None and regio_idx is not None:
        if geslacht_idx < len(row) and regio_idx < len(row):
            geslacht_value = str(row[geslacht_idx]).strip()
            regio_value = str(row[regio_idx]).strip()
            
            # Check for year in geslacht and gender in regio (column shift pattern)
            if (geslacht_value.isdigit() and len(geslacht_value) == 4 and 
                regio_value.lower() in ['man', 'vrouw', 'm', 'v']):
                
                logger.log_issue('CRITICAL', 'COLUMN_SHIFT', record_id, 'geslacht/regio',
                               f'Column shift detected: geslacht="{geslacht_value}", regio="{regio_value}"',
                               f'{geslacht_value}/{regio_value}', 'MANUAL_REVIEW_REQUIRED')
                return True
    
    return False

def process_sheet_row(row: List[str], headers: List[str], row_num: int) -> Optional[Dict[str, Any]]:
    """Convert Google Sheets row to member data with enhanced validation"""
    record_id = f"Row_{row_num}"
    
    # Detect column shift issues
    if detect_column_shift(row, headers, record_id):
        logger.log_issue('CRITICAL', 'DATA_INTEGRITY', record_id, 'all_fields',
                        'Row skipped due to column shift - requires manual review')
        return None
    
    member_data = {}
    
    # Field mapping from Google Sheets to database
    field_mapping = {
        'Tijdstempel': 'tijdstempel',
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
        'Digitale nieuwsbrieven': 'nieuwsbrief',
        'Opmerkingen': 'notities'
    }
    
    # Process each field with validation
    for i, header in enumerate(headers):
        header = header.strip()
        
        # Skip duplicate/empty headers
        if header.startswith('SKIP_DUPLICATE_'):
            continue
            
        if header in field_mapping and i < len(row):
            db_field = field_mapping[header]
            value = str(row[i]).strip() if i < len(row) and row[i] else ''
            
            if value and value.upper() != 'NA':
                # Special processing for specific fields
                if db_field == 'lidmaatschap' and value:
                    # Handle "Clubblad" special case
                    if value == 'Clubblad':
                        member_data[db_field] = 'Overig'
                        logger.log_issue('CORRECTION', 'MAPPING', record_id, db_field,
                                       'Mapped "Clubblad" to "Overig"', value, 'Overig')
                    else:
                        # Validate against memberFields.ts enum
                        validated_value = validate_enum_value(value, VALID_MEMBERSHIPS, 'lidmaatschap', record_id)
                        member_data[db_field] = validated_value
                        
                elif db_field == 'regio' and value:
                    # Map regio values with logging
                    processed_value = regio_value_mapping.get(value, value)
                    if processed_value != value:
                        logger.log_issue('INFO', 'MAPPING', record_id, db_field,
                                       'Regio value mapped', value, processed_value)
                    
                    # Check for data errors (gender in regio field)
                    if value.lower() in ['man', 'vrouw', 'm', 'v']:
                        logger.log_issue('CRITICAL', 'DATA_ERROR', record_id, db_field,
                                       'Gender value in regio field - possible column shift',
                                       value, 'MANUAL_REVIEW_REQUIRED')
                        return None
                    
                    # Validate against memberFields.ts enum
                    validated_value = validate_enum_value(processed_value, VALID_REGIONS, 'regio', record_id)
                    member_data[db_field] = validated_value
                    
                elif db_field == 'geslacht' and value:
                    # Normalize gender values
                    gender_mapping = {
                        'man': 'M',
                        'vrouw': 'V', 
                        'm': 'M',
                        'v': 'V'
                    }
                    processed_value = gender_mapping.get(value.lower(), value.upper())
                    if processed_value != value:
                        logger.log_issue('CORRECTION', 'NORMALIZATION', record_id, db_field,
                                       'Gender value normalized', value, processed_value)
                    
                    # Validate against memberFields.ts enum
                    validated_value = validate_enum_value(processed_value, VALID_GENDERS, 'geslacht', record_id)
                    member_data[db_field] = validated_value
                else:
                    member_data[db_field] = value
    
    # Generate required fields
    member_data['member_id'] = str(uuid.uuid4())
    member_data['created_at'] = datetime.now().isoformat()
    member_data['updated_at'] = datetime.now().isoformat()
    
    # Build full name
    name_parts = []
    if member_data.get('voornaam'):
        name_parts.append(member_data['voornaam'])
    if member_data.get('tussenvoegsel'):
        name_parts.append(member_data['tussenvoegsel'])
    if member_data.get('achternaam'):
        name_parts.append(member_data['achternaam'])
    
    if name_parts:
        member_data['name'] = ' '.join(name_parts)
    
    # Handle email with validation - FIXED to allow empty emails
    email = clean_email(member_data.get('email', ''), record_id)
    if email:  # Only set email if it's not empty
        member_data['email'] = email
    # If email is empty, don't set the field at all
    
    # Handle special status rules for "Clubblad" records - FIXED logging
    if member_data.get('lidmaatschap') == 'Overig':
        clubblad = member_data.get('clubblad', '').strip()
        
        if clubblad == 'Papier':
            member_data['status'] = 'Sponsor'
            logger.log_issue('INFO', 'BUSINESS_RULE', record_id, 'status',
                           'Applied Clubblad business rule: Papier -> Sponsor', 
                           clubblad, 'Sponsor')  # ✅ FIXED: proper logging
        elif clubblad == 'Digitaal':
            member_data['status'] = 'Club'
            logger.log_issue('INFO', 'BUSINESS_RULE', record_id, 'status',
                           'Applied Clubblad business rule: Digitaal -> Club',
                           clubblad, 'Club')  # ✅ FIXED: proper logging
        else:
            member_data['status'] = 'Actief'
            logger.log_issue('INFO', 'BUSINESS_RULE', record_id, 'status',
                           'Applied default status for Overig lidmaatschap',
                           clubblad, 'Actief')  # ✅ FIXED: proper logging
    else:
        member_data['status'] = 'Actief'
    
    # Validate final status against memberFields.ts enum
    if 'status' in member_data:
        member_data['status'] = validate_enum_value(member_data['status'], VALID_STATUSES, 'status', record_id)
    
    return member_data

def cleanup_existing_members():
    """Delete existing members except @h-dcn.nl accounts"""
    print("🧹 Starting cleanup of existing members...")
    
    deleted_count = 0
    preserved_count = 0
    error_count = 0
    
    try:
        # Scan all items in the table
        print("📊 Scanning existing members...")
        response = table.scan()
        items = response['Items']
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        print(f"📋 Found {len(items)} existing members")
        
        # Process items in batches
        with table.batch_writer() as batch:
            for item in items:
                try:
                    email = item.get('email', '')
                    member_id = item.get('member_id', '')
                    name = item.get('name', 'Unknown')
                    
                    # Preserve ALL @h-dcn.nl accounts (except generated test accounts)
                    if email.endswith('@h-dcn.nl') and email != 'test@h-dcn.nl':
                        preserved_count += 1
                        if preserved_count <= 10:  # Show first 10 preserved accounts
                            print(f"✅ Preserving: {name} ({email})")
                        elif preserved_count == 11:
                            print(f"✅ Preserving additional @h-dcn.nl accounts...")
                        
                        logger.log_issue('INFO', 'CLEANUP', member_id, 'email',
                                       f'Preserved @h-dcn.nl account: {email}')
                    else:
                        # Delete all other accounts (including test@h-dcn.nl fallbacks)
                        batch.delete_item(Key={'member_id': member_id})
                        deleted_count += 1
                        if deleted_count % 50 == 0:
                            print(f"🗑️  Deleted {deleted_count} members...")
                        
                        # Log differently for test accounts vs real members
                        if email == 'test@h-dcn.nl':
                            logger.log_issue('INFO', 'CLEANUP', member_id, 'email',
                                           f'Deleted generated test account: {name}')
                        else:
                            logger.log_issue('INFO', 'CLEANUP', member_id, 'email',
                                           f'Deleted member: {name} ({email})')
                        
                except Exception as e:
                    error_count += 1
                    logger.log_issue('CRITICAL', 'CLEANUP', item.get('member_id', 'unknown'), 'all_fields',
                                   f'Cleanup error: {str(e)}')
        
        print(f"\n🎯 Cleanup completed!")
        print(f"🗑️  Deleted: {deleted_count} members")
        print(f"✅ Preserved: {preserved_count} @h-dcn.nl accounts")
        print(f"❌ Errors: {error_count}")
        
        if preserved_count > 0:
            print(f"📋 Note: All {preserved_count} @h-dcn.nl accounts were preserved")
            print(f"🗑️  Only deleted non-@h-dcn.nl accounts and test@h-dcn.nl fallbacks")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")
        logger.log_issue('CRITICAL', 'CLEANUP', 'system', 'all_fields',
                       f'Cleanup operation failed: {str(e)}')
        return False

def backup_table():
    """Create a backup of the Members table"""
    print("💾 Creating table backup...")
    
    try:
        # Create backup using DynamoDB backup feature
        backup_name = f"Members-Backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Note: This requires boto3 dynamodb client, not resource
        dynamodb_client = boto3.client('dynamodb', region_name='eu-west-1')
        
        response = dynamodb_client.create_backup(
            TableName='Members',
            BackupName=backup_name
        )
        
        backup_arn = response['BackupDetails']['BackupArn']
        print(f"✅ Backup created: {backup_name}")
        print(f"📋 Backup ARN: {backup_arn}")
        
        logger.log_issue('INFO', 'BACKUP', 'system', 'table',
                       f'Table backup created: {backup_name}')
        
        return backup_name
        
    except Exception as e:
        print(f"⚠️  Backup failed: {str(e)}")
        print("⚠️  Continuing without backup - manual backup recommended")
        logger.log_issue('WARNING', 'BACKUP', 'system', 'table',
                       f'Backup failed: {str(e)}')
        return None

def import_from_google_sheets(sheet_name: str, worksheet_name: str = 'Ledenbestand', 
                            cleanup: bool = True, backup: bool = True):
    """Import members from Google Sheets to DynamoDB with optional cleanup"""
    imported_count = 0
    error_count = 0
    skipped_count = 0
    
    print(f"🚀 Starting import from Google Sheets: {sheet_name}")
    print(f"📋 Using import script v2.0 with enhanced validation")
    
    # Step 1: Create backup (optional)
    if backup:
        backup_name = backup_table()
        if not backup_name:
            response = input("⚠️  Backup failed. Continue without backup? (y/N): ")
            if response.lower() != 'y':
                print("❌ Import cancelled")
                return False
    
    # Step 2: Cleanup existing data (optional)
    if cleanup:
        print(f"\n🧹 Cleanup phase:")
        cleanup_success = cleanup_existing_members()
        if not cleanup_success:
            response = input("⚠️  Cleanup had errors. Continue with import? (y/N): ")
            if response.lower() != 'y':
                print("❌ Import cancelled")
                return False
    
    # Step 3: Import new data
    print(f"\n📥 Import phase:")
    
    try:
        # Connect to Google Sheets
        worksheet = connect_to_sheet(sheet_name, worksheet_name)
        
        # Get all data with enhanced duplicate header handling
        print("📊 Getting sheet data...")
        
        # Get headers first to handle duplicates
        headers = worksheet.row_values(1)
        print(f"📋 Found {len(headers)} columns")
        
        # Handle duplicate headers by keeping track of which ones we've seen
        seen_headers = set()
        clean_headers = []
        duplicate_positions = []
        
        for i, header in enumerate(headers):
            header = header.strip()
            if header in seen_headers or header == '':
                # Mark duplicate/empty headers for skipping
                duplicate_positions.append(i)
                clean_headers.append(f"SKIP_DUPLICATE_{i}")
                if header:
                    print(f"⚠️  Skipping duplicate header '{header}' at position {i+1}")
                else:
                    print(f"⚠️  Skipping empty header at position {i+1}")
            else:
                seen_headers.add(header)
                clean_headers.append(header)
        
        print(f"📋 Using {len(seen_headers)} unique headers (skipped {len(duplicate_positions)} duplicates)")
        
        # Get all records using clean approach
        all_values = worksheet.get_all_values()
        if not all_values:
            print("❌ No data found in worksheet")
            return False
        
        # Skip header row and process data rows
        data_rows = all_values[1:]
        print(f"📊 Found {len(data_rows)} data records")
        
        # Process each record
        for row_num, row_values in enumerate(data_rows, start=2):  # Start at 2 (header is row 1)
            try:
                # Skip empty rows
                if not any(cell.strip() for cell in row_values if cell):
                    skipped_count += 1
                    continue
                
                # Process row with clean headers
                member_data = process_sheet_row(row_values, clean_headers, row_num)
                
                if member_data is None:
                    # Row was skipped due to data quality issues
                    skipped_count += 1
                    continue
                
                # Skip if no name (but allow members with name but no email)
                if not member_data.get('name'):
                    logger.log_issue('WARNING', 'VALIDATION', f"Row_{row_num}", 'name',
                                   'Skipped - no name provided')
                    skipped_count += 1
                    continue
                
                # Insert into DynamoDB
                table.put_item(Item=member_data)
                imported_count += 1
                
                if imported_count % 50 == 0:
                    print(f"📈 Progress: {imported_count} members imported...")
                    
            except Exception as e:
                logger.log_issue('CRITICAL', 'PROCESSING', f"Row_{row_num}", 'all_fields',
                               f'Processing error: {str(e)}')
                error_count += 1
                continue
    
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        return False
    
    # Generate data quality report
    report = logger.save_report()
    
    print(f"\n🎉 Import completed!")
    print(f"✅ Imported: {imported_count}")
    print(f"⚠️  Errors: {error_count}")
    print(f"⏭️  Skipped: {skipped_count}")
    print(f"\n📊 Data Quality Summary:")
    for severity, count in report['summary'].items():
        if count > 0:
            print(f"   {severity}: {count}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("H-DCN Member Import Script v2.0")
        print("Usage: python import_members_sheets.py <sheet_name> [worksheet_name] [--no-cleanup] [--no-backup]")
        print("Example: python import_members_sheets.py 'HDCN Ledenbestand 2026' 'Ledenbestand'")
        print("Options:")
        print("  --no-cleanup    Skip deletion of existing members")
        print("  --no-backup     Skip table backup creation")
        print("\nChangelog v2.0:")
        print("  ✅ Fixed region mapping: 'Other' → 'Overig'")
        print("  ✅ Fixed business rule logging")
        print("  ✅ Enhanced email validation")
        print("  ✅ Added memberFields.ts enum validation")
        sys.exit(1)
    
    sheet_name = sys.argv[1]
    worksheet_name = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 'Ledenbestand'
    
    # Parse options
    cleanup = '--no-cleanup' not in sys.argv
    backup = '--no-backup' not in sys.argv
    
    # Show what will happen
    print("🔧 Import Configuration:")
    print(f"   Script Version: 2.0")
    print(f"   Sheet: {sheet_name}")
    print(f"   Worksheet: {worksheet_name}")
    print(f"   Backup: {'✅ Yes' if backup else '❌ No'}")
    print(f"   Cleanup: {'✅ Yes' if cleanup else '❌ No'}")
    
    if cleanup:
        print("\n⚠️  WARNING: This will DELETE existing members")
        print("✅ PRESERVED: All @h-dcn.nl accounts (except test@h-dcn.nl)")
        print("🗑️  DELETED: All other member accounts and test@h-dcn.nl fallbacks")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Import cancelled")
            sys.exit(0)
    
    import_from_google_sheets(sheet_name, worksheet_name, cleanup, backup)