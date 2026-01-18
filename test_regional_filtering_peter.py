"""
Test script to check regional filtering for Peter Geers
"""
import boto3
import json

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
members_table = dynamodb.Table('Members')

# Scan all members
response = members_table.scan()
members = response['Items']

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = members_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    members.extend(response['Items'])

print(f"Total members in database: {len(members)}")
print()

# Count by region
regions = {}
for member in members:
    region = member.get('regio', 'Unknown')
    regions[region] = regions.get(region, 0) + 1

print("Members by region:")
for region, count in sorted(regions.items()):
    print(f"  {region}: {count}")
print()

# Filter for Utrecht (what Peter should see)
utrecht_members = [m for m in members if m.get('regio') == 'Utrecht']
print(f"Utrecht members (what Peter should see): {len(utrecht_members)}")

# Show first 5 Utrecht members
print("\nFirst 5 Utrecht members:")
for member in utrecht_members[:5]:
    print(f"  - {member.get('voornaam')} {member.get('achternaam')} ({member.get('lidnummer')})")

# Filter for Noord-Holland (what Peter is seeing incorrectly)
noord_holland_members = [m for m in members if m.get('regio') == 'Noord-Holland']
print(f"\nNoord-Holland members (what Peter is incorrectly seeing): {len(noord_holland_members)}")

# Show first 5 Noord-Holland members
print("\nFirst 5 Noord-Holland members:")
for member in noord_holland_members[:5]:
    print(f"  - {member.get('voornaam')} {member.get('achternaam')} ({member.get('lidnummer')})")
