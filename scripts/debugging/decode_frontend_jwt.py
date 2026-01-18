#!/usr/bin/env python3
"""
Decode the JWT token from the frontend to see if it's valid
"""

import base64
import json
from datetime import datetime

def decode_jwt_token(jwt_token):
    """Decode and analyze a JWT token"""
    
    try:
        # Remove Bearer prefix if present
        if jwt_token.startswith('Bearer '):
            jwt_token = jwt_token[7:]
        
        # Split into parts
        parts = jwt_token.split('.')
        if len(parts) != 3:
            print(f"❌ Invalid JWT format: {len(parts)} parts")
            return None
        
        # Decode header
        header_encoded = parts[0]
        header_encoded += '=' * (4 - len(header_encoded) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_encoded))
        
        # Decode payload
        payload_encoded = parts[1]
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_encoded))
        
        print(f"✅ JWT Token Analysis")
        print(f"Length: {len(jwt_token)}")
        print(f"Parts: {len(parts)}")
        print(f"\n📋 Header:")
        print(json.dumps(header, indent=2))
        print(f"\n📋 Payload:")
        print(json.dumps(payload, indent=2))
        
        # Check expiration
        if 'exp' in payload:
            exp_time = datetime.fromtimestamp(payload['exp'])
            now = datetime.now()
            if exp_time < now:
                print(f"\n❌ TOKEN EXPIRED!")
                print(f"Expired: {exp_time}")
                print(f"Now: {now}")
            else:
                print(f"\n✅ Token valid until: {exp_time}")
        
        # Check required fields
        required_fields = ['email', 'cognito:groups']
        for field in required_fields:
            if field in payload:
                print(f"✅ {field}: {payload[field]}")
            else:
                print(f"❌ Missing {field}")
        
        return payload
        
    except Exception as e:
        print(f"❌ Error decoding JWT: {str(e)}")
        return None

if __name__ == "__main__":
    # This is the JWT token from the latest frontend logs (length 449)
    # We need to get the actual token from the browser
    print("To test the frontend JWT token:")
    print("1. Open browser developer tools")
    print("2. Go to webshop page")
    print("3. Look for the Authorization header in the network tab")
    print("4. Copy the full JWT token and paste it here")
    
    # Test with a sanitized token
    working_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiY29nbml0bzpncm91cHMiOlsiaGRjbkxlZGVuIl0sImlzcyI6Imh0dHBzOi8vY29nbml0by1pZHAuZXUtd2VzdC0xLmFtYXpvbmF3cy5jb20vZXUtd2VzdC0xX1RBVDNPUENJBCJ9.test_signature"
    
    print(f"\n🔍 Testing known working token (length {len(working_token)}):")
    decode_jwt_token(working_token)