#!/usr/bin/env python3
"""
Simple script to list all groups in the Cognito User Pool
"""

import boto3
import json
from botocore.exceptions import ClientError

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')

# User Pool ID
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

def list_all_groups():
    """List all available groups in the user pool with pagination support"""
    try:
        print("🔍 Listing all groups in Cognito User Pool:")
        print(f"User Pool ID: {USER_POOL_ID}")
        print("=" * 60)
        
        all_groups = []
        next_token = None
        page_count = 0
        
        # Handle pagination to get ALL groups
        while True:
            page_count += 1
            print(f"📄 Fetching page {page_count}...")
            
            params = {
                'UserPoolId': USER_POOL_ID,
                'Limit': 60  # Maximum allowed by AWS
            }
            
            if next_token:
                params['NextToken'] = next_token
            
            response = cognito_client.list_groups(**params)
            
            page_groups = response.get('Groups', [])
            all_groups.extend(page_groups)
            print(f"   Found {len(page_groups)} groups on this page")
            
            # Check if there are more pages
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        print(f"\n📊 Total groups found across all pages: {len(all_groups)}")
        print()
        
        # Sort groups alphabetically for easier reading
        sorted_groups = sorted(all_groups, key=lambda x: x['GroupName'])
        
        for i, group in enumerate(sorted_groups, 1):
            print(f"{i:2d}. {group['GroupName']}")
            if 'Description' in group and group['Description']:
                print(f"     Description: {group['Description']}")
            if 'Precedence' in group:
                print(f"     Precedence: {group['Precedence']}")
            if 'CreationDate' in group:
                print(f"     Created: {group['CreationDate']}")
            print()
        
        # Check specifically for verzoek_lid group
        verzoek_lid_group = next((g for g in all_groups if g['GroupName'] == 'verzoek_lid'), None)
        if verzoek_lid_group:
            print("✅ verzoek_lid group FOUND:")
            print(f"   Description: {verzoek_lid_group.get('Description', 'No description')}")
            print(f"   Precedence: {verzoek_lid_group.get('Precedence', 'Not set')}")
            print(f"   Created: {verzoek_lid_group.get('CreationDate', 'Unknown')}")
        else:
            print("❌ verzoek_lid group NOT FOUND")
        
        # Check for other expected groups
        expected_missing = ['verzoek_lid']
        missing_groups = [name for name in expected_missing if not any(g['GroupName'] == name for g in all_groups)]
        
        if missing_groups:
            print(f"\n🚨 Missing expected groups: {missing_groups}")
        
        return all_groups
                
    except Exception as e:
        print(f"❌ Error listing groups: {str(e)}")
        return []

if __name__ == "__main__":
    groups = list_all_groups()
    print("=" * 60)
    print("✅ Group listing completed!")