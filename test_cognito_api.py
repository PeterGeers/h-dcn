#!/usr/bin/env python3
import requests
import json

# Test the actual API endpoint that the frontend calls
API_BASE_URL = "https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod"

try:
    # Test the /cognito/groups endpoint
    response = requests.get(f"{API_BASE_URL}/cognito/groups")
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print()
    
    if response.status_code == 200:
        groups = response.json()
        print(f"Total groups returned by API: {len(groups)}")
        print()
        
        # Look for Regio_All
        regio_all_found = False
        for group in groups:
            if group.get('GroupName') == 'Regio_All':
                regio_all_found = True
                print("✅ Regio_All found in API response:")
                print(f"  {json.dumps(group, indent=2, default=str)}")
                break
        
        if not regio_all_found:
            print("❌ Regio_All NOT found in API response")
            print()
            print("Groups containing 'Regio':")
            for group in groups:
                if 'Regio' in group.get('GroupName', ''):
                    print(f"  - {group.get('GroupName')}")
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"Error calling API: {e}")