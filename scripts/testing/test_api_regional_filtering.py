"""
Test the regional filtering API directly
"""
import requests
import json

# You'll need to get a real JWT token from the browser
# Open browser console and run: localStorage.getItem('idToken')
JWT_TOKEN = input("Paste your JWT token from browser (localStorage.getItem('idToken')): ").strip()

API_URL = "https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev/api/members"

headers = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "Content-Type": "application/json"
}

print(f"\nCalling API: {API_URL}")
print("Headers:", {k: v[:50] + "..." if len(v) > 50 else v for k, v in headers.items()})

response = requests.get(API_URL, headers=headers)

print(f"\nStatus Code: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")

if response.status_code == 200:
    data = response.json()
    print(f"\nSuccess: {data.get('success')}")
    print(f"Total members returned: {len(data.get('data', []))}")
    print(f"Metadata: {json.dumps(data.get('metadata', {}), indent=2)}")
    
    # Count by region
    members = data.get('data', [])
    regions = {}
    for member in members:
        region = member.get('regio', 'Unknown')
        regions[region] = regions.get(region, 0) + 1
    
    print("\nMembers by region:")
    for region, count in sorted(regions.items()):
        print(f"  {region}: {count}")
        
    # Show first 5 members
    print("\nFirst 5 members:")
    for member in members[:5]:
        print(f"  - {member.get('voornaam')} {member.get('achternaam')} - {member.get('regio')} ({member.get('lidnummer')})")
else:
    print(f"\nError: {response.text}")
