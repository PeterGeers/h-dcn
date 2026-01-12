#!/usr/bin/env python3
"""
Cognito-Member Link Analysis Script

This script analyzes current Cognito users and finds matching member records
to prepare for linking Cognito accounts to member database records.

Usage:
    python analyze_cognito_member_links.py

Output:
    Creates a JSON file with analysis results including:
    - All Cognito users with their current attributes
    - Matched users (Cognito user has corresponding member record)
    - Unmatched users (Cognito user without member record)
    - Members without Cognito accounts
    - Summary statistics
"""

import boto3
import json
from datetime import datetime
import sys
import os

def analyze_cognito_member_links():
    """Analyze current Cognito users and find matching member records"""
    
    print("🔍 Starting Cognito-Member Link Analysis...")
    
    # Configuration - ensure we use the correct region
    region = 'eu-west-1'
    user_pool_id = 'eu-west-1_OAT3oPCIm'  # H-DCN Authentication Pool
    
    # Initialize AWS clients with explicit region
    try:
        cognito = boto3.client('cognito-idp', region_name=region)
        dynamodb = boto3.resource('dynamodb', region_name=region)
        members_table = dynamodb.Table('Members')
        print(f"✅ AWS clients initialized successfully (region: {region})")
    except Exception as e:
        print(f"❌ Failed to initialize AWS clients: {str(e)}")
        print("   Make sure your AWS credentials are configured properly")
        return None

    # Initialize results structure
    results = {
        'analysis_timestamp': datetime.now().isoformat(),
        'cognito_users': [],
        'matched_users': [],
        'unmatched_users': [],
        'members_without_cognito': [],
        'summary': {}
    }

    # Configuration
    user_pool_id = 'eu-west-1_OAT3oPCIm'  # H-DCN Authentication Pool
    
    try:
        # Get all Cognito users
        print("📥 Fetching Cognito users...")
        paginator = cognito.get_paginator('list_users')
        cognito_users = []

        for page in paginator.paginate(UserPoolId=user_pool_id):
            cognito_users.extend(page['Users'])

        print(f"✅ Found {len(cognito_users)} Cognito users")

        # Get all members with email
        print("📥 Fetching member records...")
        members_response = members_table.scan()
        members = members_response['Items']
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in members_response:
            members_response = members_table.scan(
                ExclusiveStartKey=members_response['LastEvaluatedKey']
            )
            members.extend(members_response['Items'])
        
        members_with_email = [m for m in members if m.get('email') and m.get('email').strip()]
        print(f"✅ Found {len(members)} total members, {len(members_with_email)} with email addresses")

        # Analyze each Cognito user
        print("🔍 Analyzing Cognito users...")
        for user in cognito_users:
            user_email = None
            member_id_attr = None
            user_status = user.get('UserStatus', 'UNKNOWN')
            username = user.get('Username', 'UNKNOWN')

            # Extract email and existing member_id from user attributes
            for attr in user.get('Attributes', []):
                if attr['Name'] == 'email':
                    user_email = attr['Value']
                elif attr['Name'] == 'custom:member_id':
                    member_id_attr = attr['Value']

            # Skip users without email
            if not user_email:
                print(f"⚠️  Skipping user {username} - no email attribute")
                continue

            user_info = {
                'username': username,
                'email': user_email,
                'current_member_id': member_id_attr,
                'status': user_status,
                'user_create_date': user.get('UserCreateDate', '').isoformat() if user.get('UserCreateDate') else None,
                'last_modified_date': user.get('UserLastModifiedDate', '').isoformat() if user.get('UserLastModifiedDate') else None
            }

            results['cognito_users'].append(user_info)

            # Find matching member by email (case-insensitive)
            matching_member = None
            for member in members_with_email:
                member_email = member.get('email', '').strip()
                if member_email.lower() == user_email.lower():
                    matching_member = member
                    break

            if matching_member:
                user_info['matched_member_id'] = matching_member.get('member_id')
                user_info['member_name'] = matching_member.get('name', '')
                user_info['member_lidnummer'] = matching_member.get('lidnummer', '')
                user_info['member_status'] = matching_member.get('status', '')
                user_info['needs_linking'] = not bool(member_id_attr)
                results['matched_users'].append(user_info)
            else:
                results['unmatched_users'].append(user_info)

        # Find members without Cognito accounts
        print("🔍 Finding members without Cognito accounts...")
        cognito_emails = [u['email'].lower() for u in results['cognito_users']]
        for member in members_with_email:
            member_email = member.get('email', '').strip().lower()
            if member_email not in cognito_emails:
                results['members_without_cognito'].append({
                    'member_id': member.get('member_id'),
                    'email': member_email,
                    'name': member.get('name', ''),
                    'lidnummer': member.get('lidnummer', ''),
                    'status': member.get('status', '')
                })

        # Generate summary statistics
        already_linked = len([u for u in results['matched_users'] if u.get('current_member_id')])
        need_linking = len([u for u in results['matched_users'] if not u.get('current_member_id')])
        
        results['summary'] = {
            'total_cognito_users': len(results['cognito_users']),
            'matched_users': len(results['matched_users']),
            'unmatched_users': len(results['unmatched_users']),
            'members_without_cognito': len(results['members_without_cognito']),
            'already_linked': already_linked,
            'need_linking': need_linking,
            'linking_coverage_percent': round((already_linked / len(results['matched_users']) * 100), 2) if results['matched_users'] else 0
        }

        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'cognito_member_analysis_{timestamp}.json'

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)

        # Print summary
        print(f"\n📊 Analysis Complete! Results saved to: {filename}")
        print(f"=" * 60)
        print(f"📈 Summary Statistics:")
        for key, value in results['summary'].items():
            print(f"   {key.replace('_', ' ').title()}: {value}")
        
        print(f"\n🔗 Linking Status:")
        print(f"   ✅ Already Linked: {already_linked} users")
        print(f"   🔄 Need Linking: {need_linking} users")
        print(f"   ❌ Unmatched: {len(results['unmatched_users'])} users")
        print(f"   👤 Members without Cognito: {len(results['members_without_cognito'])} members")
        
        if need_linking > 0:
            print(f"\n📋 Next Steps:")
            print(f"   1. Review the analysis file: {filename}")
            print(f"   2. Run the linking script: python link_cognito_members.py {filename}")
            print(f"   3. Verify linking results")
        else:
            print(f"\n✅ All matched users are already linked!")

        return results

    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function with error handling and validation"""
    
    # Check AWS credentials
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            print("❌ No AWS credentials found!")
            print("   Please configure your AWS credentials using:")
            print("   - AWS CLI: aws configure")
            print("   - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            print("   - IAM role (if running on EC2)")
            return False
    except Exception as e:
        print(f"❌ AWS credentials check failed: {str(e)}")
        return False
    
    # Check required permissions by testing access
    try:
        print("🔐 Checking AWS permissions...")
        
        # Test Cognito access
        cognito = boto3.client('cognito-idp', region_name='eu-west-1')
        cognito.describe_user_pool(UserPoolId='eu-west-1_OAT3oPCIm')
        print("   ✅ Cognito access confirmed")
        
        # Test DynamoDB access
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('Members')
        table.load()
        print("   ✅ DynamoDB access confirmed")
        
    except Exception as e:
        print(f"❌ Permission check failed: {str(e)}")
        print("   Required permissions:")
        print("   - cognito-idp:ListUsers")
        print("   - cognito-idp:DescribeUserPool")
        print("   - dynamodb:Scan (on Members table)")
        return False
    
    # Run the analysis
    results = analyze_cognito_member_links()
    return results is not None

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)