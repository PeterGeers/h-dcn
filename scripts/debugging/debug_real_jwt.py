#!/usr/bin/env python3
"""
Debug the real JWT token issue by examining what the frontend is sending
"""

import base64
import json
import sys

def decode_jwt_payload(jwt_token):
    """Decode JWT payload to see what's inside"""
    try:
        # Remove 'Bearer ' prefix if present
        if jwt_token.startswith('Bearer '):
            jwt_token = jwt_token[7:]
        
        # Split JWT into parts
        parts = jwt_token.split('.')
        if len(parts) != 3:
            print(f"❌ Invalid JWT format - has {len(parts)} parts instead of 3")
            return None
        
        # Decode payload (second part)
        payload_encoded = parts[1]
        # Add padding if needed
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        
        try:
            payload_decoded = base64.urlsafe_b64decode(payload_encoded)
            payload = json.loads(payload_decoded)
            return payload
        except Exception as e:
            print(f"❌ Error decoding payload: {str(e)}")
            return None
            
    except Exception as e:
        print(f"❌ Error processing JWT: {str(e)}")
        return None

def analyze_cognito_jwt():
    """Analyze what might be wrong with Cognito JWT tokens"""
    
    print("🔍 JWT Token Analysis")
    print("=" * 50)
    
    # This is what a typical Cognito JWT payload should look like
    expected_fields = [
        'sub',           # Subject (user ID)
        'email',         # User email
        'cognito:groups', # User groups
        'iss',           # Issuer
        'aud',           # Audience
        'exp',           # Expiration
        'iat',           # Issued at
        'token_use'      # Token use (access/id)
    ]
    
    print("✅ Expected Cognito JWT payload fields:")
    for field in expected_fields:
        print(f"   - {field}")
    
    print("\n🔍 Common issues with Cognito JWT tokens:")
    print("   1. Token expired (exp field)")
    print("   2. Wrong token type (should be 'access' token, not 'id' token)")
    print("   3. Missing cognito:groups field")
    print("   4. Invalid base64 encoding")
    print("   5. Token signature verification (backend doesn't verify signature)")
    
    print("\n💡 To debug the real issue:")
    print("   1. Copy the actual JWT token from browser network tab")
    print("   2. Paste it below to decode and analyze")
    print("   3. Check if all required fields are present")
    
    # Interactive JWT analysis
    while True:
        print("\n" + "=" * 50)
        jwt_input = input("Paste JWT token here (or 'quit' to exit): ").strip()
        
        if jwt_input.lower() in ['quit', 'exit', 'q']:
            break
        
        if not jwt_input:
            continue
        
        print(f"\n🔍 Analyzing JWT token...")
        payload = decode_jwt_payload(jwt_input)
        
        if payload:
            print("✅ JWT payload decoded successfully:")
            print(json.dumps(payload, indent=2))
            
            # Check for required fields
            print("\n🔍 Field analysis:")
            for field in expected_fields:
                if field in payload:
                    value = payload[field]
                    print(f"   ✅ {field}: {value}")
                else:
                    print(f"   ❌ {field}: MISSING")
            
            # Check token type
            token_use = payload.get('token_use')
            if token_use == 'access':
                print("   ✅ Token type: access (correct)")
            elif token_use == 'id':
                print("   ⚠️  Token type: id (should be access for API calls)")
            else:
                print(f"   ❌ Token type: {token_use} (unknown)")
            
            # Check groups
            groups = payload.get('cognito:groups', [])
            if 'hdcnLeden' in groups:
                print("   ✅ hdcnLeden group found")
            else:
                print(f"   ❌ hdcnLeden group not found. Groups: {groups}")
        
        print("\n" + "-" * 30)

if __name__ == "__main__":
    analyze_cognito_jwt()