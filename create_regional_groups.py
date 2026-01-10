#!/usr/bin/env python3
"""
Create comprehensive regional Cognito groups for H-DCN
Implements the new regional permission system with direct region name mapping
"""

import boto3
import json
from datetime import datetime

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Define the 9 H-DCN regions (matching parquet data)
REGIONS = [
    'Noord-Holland',
    'Zuid-Holland', 
    'Friesland',
    'Utrecht',
    'Oost',
    'Limburg',
    'Groningen/Drenthe',
    'Brabant/Zeeland',
    'Duitsland'
]

# Define data types that need regional permissions
DATA_TYPES = {
    'Members': {
        'description': 'Member data access',
        'precedence_base': 200  # Members groups start at 200
    },
    'Events': {
        'description': 'Event data access', 
        'precedence_base': 300  # Events groups start at 300
    },
    'Products': {
        'description': 'Product data access',
        'precedence_base': 400  # Products groups start at 400
    }
}

def create_cognito_group(group_name, description, precedence):
    """
    Create a Cognito group if it doesn't exist
    
    Args:
        group_name (str): Name of the group to create
        description (str): Description of the group
        precedence (int): Group precedence (lower = higher priority)
    
    Returns:
        tuple: (success, message)
    """
    try:
        # Check if group already exists
        try:
            response = cognito_client.get_group(
                GroupName=group_name,
                UserPoolId=USER_POOL_ID
            )
            return True, f"Group '{group_name}' already exists"
        except cognito_client.exceptions.ResourceNotFoundException:
            # Group doesn't exist, create it
            pass
        
        # Create the group
        response = cognito_client.create_group(
            GroupName=group_name,
            UserPoolId=USER_POOL_ID,
            Description=description,
            Precedence=precedence
        )
        
        return True, f"✅ Created group '{group_name}'"
        
    except Exception as e:
        return False, f"❌ Error creating group '{group_name}': {str(e)}"

def main():
    """
    Create all regional Cognito groups
    """
    print("🏗️  Creating H-DCN Regional Cognito Groups")
    print("=" * 60)
    print(f"User Pool ID: {USER_POOL_ID}")
    print(f"Regions: {len(REGIONS)}")
    print(f"Data Types: {len(DATA_TYPES)}")
    print()
    
    results = {
        'created': [],
        'existing': [],
        'errors': []
    }
    
    # Create regional groups for each data type
    for data_type, config in DATA_TYPES.items():
        print(f"📊 Creating {data_type} regional groups...")
        
        for i, region in enumerate(REGIONS):
            # Create regional group name
            group_name = f"{data_type}_Read_{region}"
            description = f"{config['description']} for {region} region"
            precedence = config['precedence_base'] + i + 1  # +1 to leave room for _All groups
            
            success, message = create_cognito_group(group_name, description, precedence)
            
            if success:
                if "already exists" in message:
                    results['existing'].append(group_name)
                else:
                    results['created'].append(group_name)
                print(f"   {message}")
            else:
                results['errors'].append((group_name, message))
                print(f"   {message}")
        
        print()
    
    # Create the "All" groups with higher precedence (lower number)
    print("🌍 Creating 'All' access groups...")
    for data_type, config in DATA_TYPES.items():
        group_name = f"{data_type}_Read_All"
        description = f"{config['description']} for all regions"
        precedence = config['precedence_base']  # Higher precedence than regional groups
        
        success, message = create_cognito_group(group_name, description, precedence)
        
        if success:
            if "already exists" in message:
                results['existing'].append(group_name)
            else:
                results['created'].append(group_name)
            print(f"   {message}")
        else:
            results['errors'].append((group_name, message))
            print(f"   {message}")
    
    print()
    
    # Summary
    print("📊 REGIONAL GROUP CREATION SUMMARY")
    print("=" * 60)
    print(f"✅ Groups created: {len(results['created'])}")
    print(f"ℹ️  Groups already existed: {len(results['existing'])}")
    print(f"❌ Errors: {len(results['errors'])}")
    
    if results['created']:
        print(f"\n✅ NEWLY CREATED GROUPS ({len(results['created'])}):")
        for group in sorted(results['created']):
            print(f"   • {group}")
    
    if results['existing']:
        print(f"\nℹ️  EXISTING GROUPS ({len(results['existing'])}):")
        for group in sorted(results['existing']):
            print(f"   • {group}")
    
    if results['errors']:
        print(f"\n❌ ERRORS ({len(results['errors'])}):")
        for group, error in results['errors']:
            print(f"   • {group}: {error}")
    
    # Calculate total expected groups
    total_expected = len(REGIONS) * len(DATA_TYPES) + len(DATA_TYPES)  # Regional + All groups
    total_processed = len(results['created']) + len(results['existing'])
    
    print(f"\n📈 COVERAGE:")
    print(f"   Expected groups: {total_expected}")
    print(f"   Processed groups: {total_processed}")
    print(f"   Success rate: {(total_processed / total_expected * 100):.1f}%")
    
    if len(results['errors']) == 0:
        print(f"\n🎉 SUCCESS: All regional groups are ready!")
        print(f"   • {len(REGIONS)} regions × {len(DATA_TYPES)} data types = {len(REGIONS) * len(DATA_TYPES)} regional groups")
        print(f"   • {len(DATA_TYPES)} 'All' access groups")
        print(f"   • Total: {total_expected} groups")
    else:
        print(f"\n⚠️  PARTIAL SUCCESS: {len(results['errors'])} groups had errors")
    
    return len(results['errors']) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)