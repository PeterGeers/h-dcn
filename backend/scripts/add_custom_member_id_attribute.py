#!/usr/bin/env python3
"""
Script to add custom:member_id attribute to Cognito User Pool.

IMPORTANT: Custom attributes cannot be added to existing Cognito User Pools.
This script provides two approaches:

1. WORKAROUND: Use existing attributes to store member_id
2. PROPER SOLUTION: Instructions for recreating the user pool with the custom attribute

The workaround is recommended for immediate use, while the proper solution
should be implemented during the next maintenance window.
"""

import boto3
import json
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_custom_attributes(user_pool_id: str, region: str = 'eu-west-1') -> List[Dict]:
    """
    Check current custom attributes in the user pool.
    
    Args:
        user_pool_id: Cognito User Pool ID
        region: AWS region
        
    Returns:
        List[Dict]: List of custom attributes
    """
    try:
        cognito = boto3.client('cognito-idp', region_name=region)
        
        response = cognito.describe_user_pool(UserPoolId=user_pool_id)
        schema_attributes = response['UserPool']['SchemaAttributes']
        
        custom_attributes = [
            attr for attr in schema_attributes 
            if attr['Name'].startswith('custom:')
        ]
        
        return custom_attributes
        
    except Exception as e:
        logger.error(f"Failed to check custom attributes: {str(e)}")
        return []

def generate_user_pool_template(user_pool_id: str, region: str = 'eu-west-1') -> Dict:
    """
    Generate a template for recreating the user pool with custom:member_id attribute.
    
    Args:
        user_pool_id: Current Cognito User Pool ID
        region: AWS region
        
    Returns:
        Dict: User pool configuration template
    """
    try:
        cognito = boto3.client('cognito-idp', region_name=region)
        
        # Get current user pool configuration
        response = cognito.describe_user_pool(UserPoolId=user_pool_id)
        current_pool = response['UserPool']
        
        # Create template with custom:member_id added
        template = {
            "PoolName": current_pool['Name'] + "-WithMemberID",
            "Policies": current_pool.get('Policies', {}),
            "LambdaConfig": current_pool.get('LambdaConfig', {}),
            "AutoVerifiedAttributes": current_pool.get('AutoVerifiedAttributes', []),
            "UsernameAttributes": current_pool.get('UsernameAttributes', []),
            "EmailVerificationMessage": current_pool.get('EmailVerificationMessage', ''),
            "EmailVerificationSubject": current_pool.get('EmailVerificationSubject', ''),
            "VerificationMessageTemplate": current_pool.get('VerificationMessageTemplate', {}),
            "MfaConfiguration": current_pool.get('MfaConfiguration', 'OFF'),
            "UserAttributeUpdateSettings": current_pool.get('UserAttributeUpdateSettings', {}),
            "EmailConfiguration": current_pool.get('EmailConfiguration', {}),
            "UserPoolTags": current_pool.get('UserPoolTags', {}),
            "AdminCreateUserConfig": current_pool.get('AdminCreateUserConfig', {}),
            "Schema": []
        }
        
        # Copy existing schema attributes
        for attr in current_pool['SchemaAttributes']:
            template['Schema'].append({
                "Name": attr['Name'],
                "AttributeDataType": attr['AttributeDataType'],
                "DeveloperOnlyAttribute": attr.get('DeveloperOnlyAttribute', False),
                "Mutable": attr.get('Mutable', True),
                "Required": attr.get('Required', False),
                "StringAttributeConstraints": attr.get('StringAttributeConstraints', {}),
                "NumberAttributeConstraints": attr.get('NumberAttributeConstraints', {})
            })
        
        # Add custom:member_id attribute
        template['Schema'].append({
            "Name": "custom:member_id",
            "AttributeDataType": "String",
            "DeveloperOnlyAttribute": False,
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {
                "MinLength": "1",
                "MaxLength": "256"
            }
        })
        
        return template
        
    except Exception as e:
        logger.error(f"Failed to generate user pool template: {str(e)}")
        return {}

def create_migration_plan(user_pool_id: str, region: str = 'eu-west-1') -> str:
    """
    Create a detailed migration plan for adding custom:member_id.
    
    Args:
        user_pool_id: Current Cognito User Pool ID
        region: AWS region
        
    Returns:
        str: Detailed migration plan
    """
    
    plan = f"""
# Cognito User Pool Migration Plan: Adding custom:member_id

## Current Situation
- User Pool ID: {user_pool_id}
- Region: {region}
- Issue: Cannot add custom:member_id to existing user pool
- Users affected: 74 users need member_id linking

## Option 1: IMMEDIATE WORKAROUND (Recommended for now)

### Use Profile Field JSON Storage
```bash
cd backend/scripts
python add_member_id_workaround.py cognito_member_analysis_20260112_153447.json --execute
```

This stores member_id in the 'profile' field as JSON:
```json
{{
  "member_id": "6bcc949f-49ab-4d8b-93e3-ba9f7ab3e579",
  "member_id_added": "2026-01-12T15:45:00.000Z"
}}
```

### Update Application Code
Update auth utilities to read member_id from profile field:
```python
def get_member_id_from_cognito_user(user_attributes):
    for attr in user_attributes:
        if attr['Name'] == 'profile':
            try:
                profile_data = json.loads(attr['Value'])
                return profile_data.get('member_id')
            except json.JSONDecodeError:
                pass
    return None
```

## Option 2: PROPER SOLUTION (For next maintenance window)

### Step 1: Create New User Pool with custom:member_id
```bash
aws cognito-idp create-user-pool \\
    --pool-name "H-DCN-Authentication-Pool-v2" \\
    --region eu-west-1 \\
    --cli-input-json file://new-user-pool-config.json
```

### Step 2: Export Current Users
```bash
python export_cognito_users.py {user_pool_id}
```

### Step 3: Import Users to New Pool
```bash
python import_cognito_users.py NEW_POOL_ID exported_users.json
```

### Step 4: Update Application Configuration
- Update aws-exports.ts with new User Pool ID
- Update backend Lambda functions
- Update frontend authentication configuration

### Step 5: DNS/Domain Migration
- Move custom domain to new user pool
- Update OAuth callbacks
- Test authentication flows

### Step 6: Cleanup
- Archive old user pool
- Update documentation

## Recommended Approach

1. **IMMEDIATE**: Use Option 1 (workaround) to fix Peter's webshop issue
2. **PLANNED**: Schedule Option 2 for next maintenance window
3. **TESTING**: Test workaround thoroughly before production use

## Risk Assessment

### Option 1 (Workaround):
- ✅ Low risk, immediate implementation
- ✅ No user disruption
- ✅ Reversible
- ⚠️  Requires code changes to read from profile field
- ⚠️  Not the "proper" solution

### Option 2 (New User Pool):
- ✅ Proper, long-term solution
- ✅ Clean architecture
- ❌ High risk, requires careful migration
- ❌ Potential user disruption
- ❌ Requires maintenance window

## Implementation Timeline

### Phase 1 (Today): Immediate Fix
- [x] Create workaround script
- [ ] Test workaround with Peter's account
- [ ] Deploy workaround to production
- [ ] Update application code to read from profile field

### Phase 2 (Next Week): Validation
- [ ] Monitor workaround performance
- [ ] Test all authentication flows
- [ ] Validate webshop functionality

### Phase 3 (Future): Proper Migration
- [ ] Plan maintenance window
- [ ] Create new user pool configuration
- [ ] Test migration process in staging
- [ ] Execute production migration
"""
    
    return plan

def main():
    """Main function to analyze current state and provide solutions."""
    
    user_pool_id = 'eu-west-1_OAT3oPCIm'
    region = 'eu-west-1'
    
    print("🔍 Analyzing Cognito User Pool for custom:member_id attribute...")
    print(f"User Pool ID: {user_pool_id}")
    print(f"Region: {region}")
    print("-" * 60)
    
    # Check current custom attributes
    custom_attrs = check_custom_attributes(user_pool_id, region)
    
    print(f"Current custom attributes ({len(custom_attrs)}):")
    for attr in custom_attrs:
        print(f"  - {attr['Name']}: {attr['AttributeDataType']}")
    
    # Check if custom:member_id exists
    has_member_id = any(attr['Name'] == 'custom:member_id' for attr in custom_attrs)
    
    if has_member_id:
        print("\n✅ custom:member_id attribute already exists!")
        print("You can proceed with the original linking script.")
    else:
        print("\n❌ custom:member_id attribute does NOT exist")
        print("\n📋 SOLUTION OPTIONS:")
        print("1. IMMEDIATE WORKAROUND: Use profile field to store member_id")
        print("2. PROPER SOLUTION: Recreate user pool with custom attribute")
        
        # Generate migration plan
        plan = create_migration_plan(user_pool_id, region)
        
        # Save migration plan to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        plan_file = f'cognito_migration_plan_{timestamp}.md'
        
        with open(plan_file, 'w', encoding='utf-8') as f:
            f.write(plan)
        
        print(f"\n📄 Detailed migration plan saved to: {plan_file}")
        
        # Generate user pool template
        template = generate_user_pool_template(user_pool_id, region)
        if template:
            template_file = f'new_user_pool_template_{timestamp}.json'
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, default=str)
            print(f"📄 New user pool template saved to: {template_file}")
        
        print("\n🚀 RECOMMENDED NEXT STEPS:")
        print("1. Run the workaround script to fix immediate issues:")
        print("   python add_member_id_workaround.py cognito_member_analysis_20260112_153447.json --execute")
        print("2. Update application code to read member_id from profile field")
        print("3. Plan proper migration for next maintenance window")

if __name__ == "__main__":
    main()