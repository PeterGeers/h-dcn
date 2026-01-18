#!/usr/bin/env python3
"""
Final check and creation of all needed roles
"""

import boto3

cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Complete role structure we need
REQUIRED_ROLES = {
    'Members': ['Members_CRUD', 'Members_Read', 'Members_Export', 'Members_Status_Approve'],
    'Events': ['Events_CRUD', 'Events_Read', 'Events_Export'],
    'Products': ['Products_CRUD', 'Products_Read', 'Products_Export'],
    'Communication': ['Communication_CRUD', 'Communication_Read', 'Communication_Export'],
    'System': ['System_CRUD', 'System_User_Management', 'System_Logs_Read'],
    'Regions': ['Regio_All', 'Regio_Noord-Holland', 'Regio_Zuid-Holland', 'Regio_Friesland', 
               'Regio_Utrecht', 'Regio_Oost', 'Regio_Limburg', 'Regio_Groningen/Drenthe', 
               'Regio_Brabant/Zeeland', 'Regio_Duitsland']
}

def main():
    try:
        # Get current groups
        response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
        existing_groups = [group['GroupName'] for group in response['Groups']]
        
        print("🔍 CHECKING REQUIRED ROLES...")
        print()
        
        all_missing = []
        
        for category, roles in REQUIRED_ROLES.items():
            print(f"📋 {category} roles:")
            missing_in_category = []
            
            for role in roles:
                if role in existing_groups:
                    print(f"   ✅ {role}")
                else:
                    print(f"   ❌ {role} - MISSING")
                    missing_in_category.append(role)
                    all_missing.append(role)
            
            if missing_in_category:
                print(f"   🔧 Creating missing {category} roles...")
                for role in missing_in_category:
                    try:
                        description = f"{category} role: {role}"
                        cognito_client.create_group(
                            GroupName=role,
                            UserPoolId=USER_POOL_ID,
                            Description=description
                        )
                        print(f"      ✅ Created {role}")
                    except Exception as e:
                        print(f"      ❌ Error creating {role}: {e}")
            
            print()
        
        # Final verification
        print("📊 FINAL VERIFICATION:")
        response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
        final_groups = [group['GroupName'] for group in response['Groups']]
        
        for category, roles in REQUIRED_ROLES.items():
            existing_count = len([r for r in roles if r in final_groups])
            total_count = len(roles)
            status = "✅" if existing_count == total_count else "⚠️"
            print(f"   {status} {category}: {existing_count}/{total_count} roles")
        
        print()
        print("🎯 COMPLETE ROLE STRUCTURE:")
        for category, roles in REQUIRED_ROLES.items():
            existing_roles = [r for r in roles if r in final_groups]
            print(f"   {category} ({len(existing_roles)}): {existing_roles}")
        
        return len(all_missing) == 0
        
    except Exception as e:
        print(f'Error: {e}')
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ All required roles are now present!")
    else:
        print("\n❌ Some roles are still missing")
    exit(0 if success else 1)