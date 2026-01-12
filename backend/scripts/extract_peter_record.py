#!/usr/bin/env python3
"""
Extract complete user record for peter@pgeers.nl from Members table
This script provides a comprehensive view of Peter's member data for analysis.
"""

import boto3
from boto3.dynamodb.conditions import Attr
import json
from datetime import datetime
import sys

# Configure AWS
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')

def extract_peter_record():
    """Extract and display Peter's complete member record"""
    print("=" * 80)
    print("🔍 EXTRACTING USER RECORD FOR peter@pgeers.nl")
    print("=" * 80)
    
    try:
        # Find Peter's record by email
        print("📡 Scanning Members table for peter@pgeers.nl...")
        response = table.scan(
            FilterExpression=Attr('email').eq('peter@pgeers.nl')
        )
        
        items = response['Items']
        
        if not items:
            print("❌ ERROR: No record found for peter@pgeers.nl")
            print("💡 Suggestions:")
            print("   - Check if email is correct")
            print("   - Verify AWS credentials and region")
            print("   - Check if Members table exists")
            return None
        
        if len(items) > 1:
            print(f"⚠️  WARNING: Multiple records found ({len(items)})")
            print("   Using the first record found")
        
        peter = items[0]
        
        print(f"✅ SUCCESS: Found record for peter@pgeers.nl")
        print(f"📅 Extraction time: {datetime.now().isoformat()}")
        
        # Display basic info
        print("\n" + "=" * 50)
        print("📋 BASIC INFORMATION")
        print("=" * 50)
        
        basic_fields = [
            ('Name', peter.get('name', 'NOT_SET')),
            ('Email', peter.get('email', 'NOT_SET')),
            ('Member ID', peter.get('member_id', 'NOT_SET')),
            ('Lid Nummer', peter.get('lidnummer', 'NOT_SET')),
            ('Status', peter.get('status', 'NOT_SET')),
            ('Lidmaatschap', peter.get('lidmaatschap', 'NOT_SET')),
            ('Regio', peter.get('regio', 'NOT_SET'))
        ]
        
        for label, value in basic_fields:
            print(f"   {label:<15}: {value}")
        
        # Display personal details
        print("\n" + "=" * 50)
        print("👤 PERSONAL DETAILS")
        print("=" * 50)
        
        personal_fields = [
            ('Voornaam', peter.get('voornaam', 'NOT_SET')),
            ('Achternaam', peter.get('achternaam', 'NOT_SET')),
            ('Geboortedatum', peter.get('geboortedatum', 'NOT_SET')),
            ('Telefoon', peter.get('telefoon', 'NOT_SET')),
            ('Adres', peter.get('adres', 'NOT_SET')),
            ('Postcode', peter.get('postcode', 'NOT_SET')),
            ('Plaats', peter.get('plaats', 'NOT_SET'))
        ]
        
        for label, value in personal_fields:
            print(f"   {label:<15}: {value}")
        
        # Display motorcycle details
        print("\n" + "=" * 50)
        print("🏍️  MOTORCYCLE DETAILS")
        print("=" * 50)
        
        motorcycle_fields = [
            ('Motormerk', peter.get('motormerk', 'NOT_SET')),
            ('Motortype', peter.get('motortype', 'NOT_SET')),
            ('Bouwjaar', peter.get('bouwjaar', 'NOT_SET')),
            ('Kenteken', peter.get('kenteken', 'NOT_SET')),
            ('Cilinderinhoud', peter.get('cilinderinhoud', 'NOT_SET'))
        ]
        
        for label, value in motorcycle_fields:
            print(f"   {label:<15}: {value}")
        
        # Display timestamps
        print("\n" + "=" * 50)
        print("⏰ TIMESTAMPS")
        print("=" * 50)
        
        timestamp_fields = [
            ('Tijdstempel (Lid sinds)', peter.get('tijdstempel', 'NOT_SET')),
            ('Created At', peter.get('created_at', 'NOT_SET')),
            ('Updated At', peter.get('updated_at', 'NOT_SET')),
            ('Ingangsdatum', peter.get('ingangsdatum', 'NOT_SET'))
        ]
        
        for label, value in timestamp_fields:
            print(f"   {label:<25}: {value}")
        
        # Display all other fields
        print("\n" + "=" * 50)
        print("📄 ALL FIELDS (COMPLETE RECORD)")
        print("=" * 50)
        
        # Sort fields alphabetically for easier reading
        all_fields = sorted(peter.items())
        for field, value in all_fields:
            # Format value for display
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            
            # Truncate very long values
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            
            print(f"   {field:<25}: {value_str}")
        
        # Analysis section
        print("\n" + "=" * 50)
        print("🔍 ANALYSIS & ISSUES")
        print("=" * 50)
        
        issues = []
        
        # Check for common issues
        if not peter.get('lidnummer') or peter.get('lidnummer') == 0:
            issues.append("❌ Lid nummer is missing or 0")
        
        if not peter.get('tijdstempel'):
            issues.append("❌ Tijdstempel (Lid sinds) is missing")
        
        if not peter.get('bouwjaar'):
            issues.append("⚠️  Bouwjaar is missing")
        
        if not peter.get('motormerk'):
            issues.append("⚠️  Motormerk is missing")
        
        if peter.get('status') != 'Actief':
            issues.append(f"⚠️  Status is '{peter.get('status')}' (not 'Actief')")
        
        if issues:
            print("   Issues found:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("   ✅ No obvious issues detected")
        
        # Export to JSON file
        print("\n" + "=" * 50)
        print("💾 EXPORT")
        print("=" * 50)
        
        filename = f"peter_record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert Decimal types to regular numbers for JSON serialization
        def decimal_default(obj):
            if hasattr(obj, '__float__'):
                return float(obj)
            raise TypeError
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(peter, f, indent=2, ensure_ascii=False, default=decimal_default)
        
        print(f"   ✅ Record exported to: {filename}")
        
        print("\n" + "=" * 80)
        print("✅ EXTRACTION COMPLETE")
        print("=" * 80)
        
        return peter
        
    except Exception as e:
        print(f"❌ ERROR: Failed to extract record: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function"""
    print("🚀 Peter's Record Extraction Tool")
    print("📧 Target: peter@pgeers.nl")
    print("🗄️  Source: Members table (DynamoDB)")
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"🔐 AWS Account: {identity.get('Account', 'Unknown')}")
        print(f"👤 AWS User: {identity.get('Arn', 'Unknown')}")
    except Exception as e:
        print(f"⚠️  Could not verify AWS credentials: {e}")
    
    print()
    
    # Extract the record
    record = extract_peter_record()
    
    if record:
        print(f"\n💡 TIP: Use the exported JSON file for further analysis")
        print(f"💡 TIP: Check the 'ANALYSIS & ISSUES' section above for potential problems")
    else:
        print(f"\n❌ Failed to extract record. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()