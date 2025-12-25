#!/usr/bin/env python3
"""
H-DCN Cognito User Pool Comparison Script

This script compares users between the old and new Cognito User Pools
to help plan the migration strategy.
"""

import boto3
import json
from typing import Dict, List

def get_user_count_and_sample(pool_id: str, pool_name: str) -> Dict:
    """Get user count and sample users from a Cognito User Pool"""
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    print(f"\n=== {pool_name} ({pool_id}) ===")
    
    try:
        # Get first batch of users
        response = cognito_client.list_users(
            UserPoolId=pool_id,
            Limit=10
        )
        
        users = response['Users']
        total_shown = len(users)
        
        print(f"Sample of {total_shown} users:")
        
        for i, user in enumerate(users, 1):
            email = None
            name_parts = []
            
            # Extract email and name
            for attr in user.get('Attributes', []):
                if attr['Name'] == 'email':
                    email = attr['Value']
                elif attr['Name'] == 'given_name':
                    name_parts.append(attr['Value'])
                elif attr['Name'] == 'family_name':
                    name_parts.append(attr['Value'])
            
            name = ' '.join(name_parts) if name_parts else 'No name'
            status = user.get('UserStatus', 'Unknown')
            enabled = user.get('Enabled', False)
            
            print(f"  {i:2d}. {email or 'No email'}")
            print(f"      Name: {name}")
            print(f"      Status: {status} | Enabled: {enabled}")
            print()
            
        # Try to get total count (this is approximate)
        print(f"Note: This shows first {total_shown} users. There may be more.")
        
        if 'PaginationToken' in response:
            print("More users available (pagination token present)")
        else:
            print(f"Total users in pool: {total_shown}")
            
        return {
            'pool_id': pool_id,
            'pool_name': pool_name,
            'sample_count': total_shown,
            'has_more': 'PaginationToken' in response,
            'users': users
        }
        
    except Exception as e:
        print(f"Error accessing pool {pool_name}: {str(e)}")
        return {
            'pool_id': pool_id,
            'pool_name': pool_name,
            'error': str(e)
        }

def main():
    """Main function to compare both pools"""
    print("=== H-DCN Cognito User Pool Comparison ===")
    
    # Pool configurations
    old_pool = {
        'id': 'eu-west-1_VtKQHhXGN',
        'name': 'Old Pool (Leden)'
    }
    
    new_pool = {
        'id': 'eu-west-1_OAT3oPCIm', 
        'name': 'New Pool (H-DCN-Authentication-Pool)'
    }
    
    # Check both pools
    old_pool_info = get_user_count_and_sample(old_pool['id'], old_pool['name'])
    new_pool_info = get_user_count_and_sample(new_pool['id'], new_pool['name'])
    
    # Summary
    print("\n=== SUMMARY ===")
    
    if 'error' not in old_pool_info:
        print(f"Old Pool: {old_pool_info['sample_count']} users shown")
        if old_pool_info['has_more']:
            print("  (More users available)")
    else:
        print(f"Old Pool: Error - {old_pool_info['error']}")
        
    if 'error' not in new_pool_info:
        print(f"New Pool: {new_pool_info['sample_count']} users shown")
        if new_pool_info['has_more']:
            print("  (More users available)")
    else:
        print(f"New Pool: Error - {new_pool_info['error']}")
    
    print("\nReady to proceed with migration if needed.")

if __name__ == "__main__":
    main()