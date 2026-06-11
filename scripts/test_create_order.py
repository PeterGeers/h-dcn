"""Test the create_order endpoint directly via API Gateway."""
import boto3
import json
import requests

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')

# Get the API base URL
API_BASE = "https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod"

# Make the POST /orders call without auth (to see what error we get)
print("Testing POST /orders without auth...")
resp = requests.post(
    f"{API_BASE}/orders",
    json={"event_id": None, "items": []},
    headers={"Content-Type": "application/json"}
)
print(f"  Status: {resp.status_code}")
print(f"  Body: {resp.text[:500]}")
print()

# Now check what the frontend's API base URL is
print("Checking frontend API base URL...")
print(f"  Expected: {API_BASE}")
