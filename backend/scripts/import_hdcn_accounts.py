#!/usr/bin/env python3
"""
Import @h-dcn.nl Google Workspace accounts as member records
This ensures they are preserved during member data migrations
"""

import boto3
import csv
import uuid
from datetime import datetime
import sys
import os

# Configure AWS
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')

def detect_region_from_email(email):
    """Detect H-DCN region from email address"""
    email_lower = email.lower()
    
    # Region mapping based on email patterns
    region_patterns = {
        'noord-holland': 'Noord-Holland',
        'noordholland': 'Noord-Holland',
        'zuid-holland': 'Zuid-Holland',
        'zuidholland': 'Zuid-Holland',
        'friesland': 'Friesland',
        'utrecht': 'Utrecht',
        'oost': 'Oost',
        'limburg': 'Limburg',
        'groningen': 'Groningen/Drenthe',
        'drenthe': 'Groningen/Drenthe',
        'brabant': 'Brabant/Zeeland',
        'zeeland': 'Brabant/Zeeland',
        'duitsland': 'Duitsland'
    }
    
    # Check email for region patterns
    for pattern, region in region_patterns.items():
        if pattern in email_lower:
            return region
    
    # Default to Overig if no region found
    return 'Overig'

def import_hdcn_accounts(csv_file_path):
    """Import @h-dcn.nl accounts from Google Workspace CSV export"""
    
    if not os.path.exists(csv_file_path):
        print(f"❌ CSV file not found: {csv_file_path}")
        return False
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"🚀 Starting import of @h-dcn.nl accounts from: {csv_file_path}")
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            # The CSV uses comma delimiter
            reader = csv.DictReader(file, delimiter=',')
            
            print(f"📋 Headers found: {len(reader.fieldnames)} columns")
            print(f"📋 First few headers: {reader.fieldnames[:5] if reader.fieldnames else 'None'}")
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Extract data from CSV - handle headers with extra spaces
                    first_name = ''
                    last_name = ''
                    email = ''
                    org_unit = ''
                    status = ''
                    
                    # Find the correct column values by checking for key parts in header names
                    for key, value in row.items():
                        key_clean = key.strip().lower()
                        if 'first name' in key_clean:
                            first_name = value.strip()
                        elif 'last name' in key_clean:
                            last_name = value.strip()
                        elif 'email address' in key_clean:
                            email = value.strip()
                        elif 'org unit path' in key_clean:
                            org_unit = value.strip()
                        elif 'status' in key_clean and 'read only' in key_clean:
                            status = value.strip()
                    
                    # Skip if no email or not @h-dcn.nl
                    if not email or '@h-dcn.nl' not in email.lower():
                        skipped_count += 1
                        continue
                    
                    # Import all @h-dcn.nl accounts regardless of status
                    # These are legitimate H-DCN organizational accounts that should be preserved
                    
                    # Detect region from email
                    detected_region = detect_region_from_email(email)
                    
                    # Build member record for @h-dcn.nl account with specified values
                    member_data = {
                        'member_id': str(uuid.uuid4()),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        'email': email,
                        'status': 'HdcnAccount',  # ✅ As requested
                        'lidmaatschap': 'Overig',  # ✅ As requested
                        'regio': detected_region,  # ✅ Detected from email or 'Overig'
                        'clubblad': 'Geen',  # ✅ As requested
                        'nieuwsbrief': 'Ja',  # ✅ As requested
                        'wiewatwaar': 'Lid H-DCN',  # ✅ As requested
                        'betaalwijze': 'Overmaking'  # ✅ As requested
                    }
                    
                    # Add name if available
                    name_parts = []
                    if first_name:
                        member_data['voornaam'] = first_name
                        name_parts.append(first_name)
                    if last_name:
                        member_data['achternaam'] = last_name
                        name_parts.append(last_name)
                    
                    if name_parts:
                        member_data['name'] = ' '.join(name_parts)
                    else:
                        # Use email prefix as name if no name provided
                        email_prefix = email.split('@')[0]
                        member_data['name'] = email_prefix.replace('.', ' ').title()
                    
                    # Add organizational info as notes
                    notes = []
                    if org_unit and org_unit != '/':
                        notes.append(f"Org Unit: {org_unit}")
                    if status:
                        notes.append(f"Google Status: {status}")
                    notes.append(f"Google Workspace Account")
                    notes.append(f"Imported: {datetime.now().strftime('%Y-%m-%d')}")
                    
                    if notes:
                        member_data['notities'] = ' | '.join(notes)
                    
                    # Insert into DynamoDB
                    table.put_item(Item=member_data)
                    imported_count += 1
                    
                    region_info = f" → {detected_region}" if detected_region != 'Overig' else ""
                    print(f"✅ Imported: {member_data['name']} ({email}){region_info}")
                    
                except Exception as e:
                    print(f"❌ Error processing row {row_num}: {str(e)}")
                    error_count += 1
                    continue
    
    except Exception as e:
        print(f"❌ Failed to read CSV file: {str(e)}")
        return False
    
    print(f"\n🎉 Import completed!")
    print(f"✅ Imported: {imported_count} @h-dcn.nl accounts")
    print(f"⚠️  Skipped: {skipped_count} accounts")
    print(f"❌ Errors: {error_count}")
    
    if imported_count > 0:
        print(f"\n📋 All @h-dcn.nl accounts now have member records with:")
        print(f"   Status: 'HdcnAccount'")
        print(f"   Lidmaatschap: 'Overig'")
        print(f"   Clubblad: 'Geen'")
        print(f"   Nieuwsbrief: 'Ja'")
        print(f"   WieWatWaar: 'Lid H-DCN'")
        print(f"   Betaalwijze: 'Overmaking'")
        print(f"   Regio: Detected from email or 'Overig'")
        print(f"\n🔒 They will be preserved during future member migrations")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_hdcn_accounts.py <csv_file_path>")
        print("Example: python import_hdcn_accounts.py '.kiro/specs/migration/User_Download_06012026_121413.csv'")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    print("🔧 @h-dcn.nl Account Import Configuration:")
    print(f"   CSV File: {csv_file}")
    print(f"   Target: Members table (as HdcnAccount records)")
    print(f"   Purpose: Preserve @h-dcn.nl accounts during migrations")
    print(f"   Status: HdcnAccount")
    print(f"   Lidmaatschap: Overig")
    print(f"   Clubblad: Geen")
    print(f"   Nieuwsbrief: Ja")
    print(f"   WieWatWaar: Lid H-DCN")
    print(f"   Betaalwijze: Overmaking")
    print(f"   Regio: Auto-detected from email")
    
    response = input("\nContinue with import? (y/N): ")
    if response.lower() != 'y':
        print("❌ Import cancelled")
        sys.exit(0)
    
    success = import_hdcn_accounts(csv_file)
    if not success:
        sys.exit(1)