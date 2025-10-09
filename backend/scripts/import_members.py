#!/usr/bin/env python3
"""
H-DCN Member CSV Import Script
Direct import to DynamoDB bypassing API issues
"""

import csv
import boto3
import uuid
from datetime import datetime
import sys

# Configure AWS (make sure your credentials are set)
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')  # Adjust table name if needed

def clean_email(email):
    """Clean and validate email addresses"""
    if not email or email.strip() == '' or email.strip().upper() == 'NA':
        return "test@h-dcn.nl"
    email = email.strip()
    if '@' in email and '.' in email:
        return email
    return "test@h-dcn.nl"

def process_csv_row(row, headers):
    """Convert CSV row to member data"""
    member_data = {}
    
    # Map CSV columns to member fields
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
    
    # Process each field
    for i, header in enumerate(headers):
        if i < len(row) and header.strip() in field_mapping:
            field_name = field_mapping[header.strip()]
            value = row[i].strip() if i < len(row) else ''
            if value and value != 'NA':
                member_data[field_name] = value
    
    # Generate required fields
    member_data['member_id'] = str(uuid.uuid4())
    member_data['created_at'] = datetime.now().isoformat()
    
    # Build name
    name_parts = []
    if member_data.get('voornaam'):
        name_parts.append(member_data['voornaam'])
    if member_data.get('tussenvoegsel'):
        name_parts.append(member_data['tussenvoegsel'])
    if member_data.get('achternaam'):
        name_parts.append(member_data['achternaam'])
    
    if name_parts:
        member_data['name'] = ' '.join(name_parts)
    
    # Handle email
    email = clean_email(member_data.get('email'))
    if email:
        member_data['email'] = email
    else:
        # Generate placeholder for members without email
        member_data['email'] = f"noemail_{int(datetime.now().timestamp())}@hdcn.local"
    
    # Set default status if not provided
    if 'status' not in member_data:
        member_data['status'] = 'active'
    
    return member_data

def import_csv(csv_file_path):
    """Import CSV file to DynamoDB"""
    imported_count = 0
    error_count = 0
    skipped_count = 0
    
    print(f"Starting import from {csv_file_path}")
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            # Try to detect delimiter
            sample = file.read(1024)
            file.seek(0)
            
            # Use comma as delimiter (adjust if needed)
            reader = csv.reader(file, delimiter=',')
            
            # Get headers
            headers = next(reader)
            print(f"Found {len(headers)} columns")
            print("Headers:", headers[:5], "..." if len(headers) > 5 else "")
            
            # Process each row
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Skip empty rows
                    if not any(cell.strip() for cell in row):
                        skipped_count += 1
                        continue
                    
                    # Process row
                    member_data = process_csv_row(row, headers)
                    
                    # Skip if no name and no email
                    if not member_data.get('name') and not member_data.get('email'):
                        print(f"Row {row_num}: Skipped - no name or email")
                        skipped_count += 1
                        continue
                    
                    # Insert into DynamoDB
                    table.put_item(Item=member_data)
                    imported_count += 1
                    
                    if imported_count % 50 == 0:
                        print(f"Progress: {imported_count} members imported...")
                        
                except Exception as e:
                    print(f"Row {row_num}: Error - {str(e)}")
                    error_count += 1
                    continue
    
    except Exception as e:
        print(f"File error: {str(e)}")
        return False
    
    print(f"\nImport completed!")
    print(f"Imported: {imported_count}")
    print(f"Errors: {error_count}")
    print(f"Skipped: {skipped_count}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_members.py <csv_file_path>")
        print("Example: python import_members.py 'HDCN Ledenbestand 2025.csv'")
        sys.exit(1)
    
    csv_file = "C:\\Users\\peter\\Downloads\\HDCN Ledenbestand 2025 - Ledenbestand.csv"
    ##sys.argv[1]
    import_csv(csv_file)