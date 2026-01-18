#!/usr/bin/env python3
"""
Decode the real JWT token from frontend logs to compare with working test token
"""

import json
import base64
from datetime import datetime

def decode_jwt_token(jwt_token):
    """
    Decode JWT token and return payload
    """
    try:
        # Split JWT token into parts
        parts = jwt_token.split('.')
        if len(parts) != 3:
            print(f"❌ Invalid JWT token format - parts: {len(parts)}")
            return None
        
        # Decode header
        header_encoded = parts[0]
        header_encoded += '=' * (4 - len(header_encoded) % 4)
        header_decoded = base64.urlsafe_b64decode(header_encoded)
        header = json.loads(header_decoded)
        
        # Decode payload
        payload_encoded = parts[1]
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_decoded)
        
        return {
            'header': header,
            'payload': payload,
            'signature': parts[2]
        }
        
    except Exception as e:
        print(f"❌ Error decoding JWT token: {str(e)}")
        return None

def main():
    print("🔍 JWT Token Analysis")
    print("=" * 50)
    
    # Test JWT token (sanitized)
    real_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImNvZ25pdG86Z3JvdXBzIjpbImhkY25MZWRlbiJdLCJhdXRoX3RpbWUiOjE3NjgzMDE0OTIsImlhdCI6MTc2ODMwMTQ5MiwiZXhwIjoxNzY4MzA1MDkyLCJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJjbGllbnRfaWQiOiJ0ZXN0X2NsaWVudCIsInVzZXJuYW1lIjoidGVzdEBleGFtcGxlLmNvbSIsImF1dGhfbWV0aG9kIjoicGFzc2tleSJ9.test_signature"
    
    # Working test JWT token (sanitized) 
    working_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImNvZ25pdG86Z3JvdXBzIjpbImhkY25MZWRlbiJdLCJhdXRoX3RpbWUiOjE3MzY3NzkyMDAsImlhdCI6MTczNjc3OTIwMCwiZXhwIjoxNzM2NzgyODAwLCJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJjbGllbnRfaWQiOiJ0ZXN0X2NsaWVudCIsInVzZXJuYW1lIjoidGVzdEBleGFtcGxlLmNvbSJ9.test_signature"
    
    print(f"📊 Token Lengths:")
    print(f"   Real token: {len(real_jwt_token)}")
    print(f"   Working token: {len(working_jwt_token)}")
    print()
    
    # Decode real token
    print("🔍 REAL JWT TOKEN (from frontend logs):")
    real_decoded = decode_jwt_token(real_jwt_token)
    if real_decoded:
        print("Header:", json.dumps(real_decoded['header'], indent=2))
        print("Payload:", json.dumps(real_decoded['payload'], indent=2))
        
        # Check expiration
        exp_timestamp = real_decoded['payload'].get('exp')
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            current_datetime = datetime.now()
            print(f"Expires: {exp_datetime}")
            print(f"Current: {current_datetime}")
            print(f"Is expired: {current_datetime > exp_datetime}")
        print()
    
    # Decode working token
    print("✅ WORKING JWT TOKEN (from tests):")
    working_decoded = decode_jwt_token(working_jwt_token)
    if working_decoded:
        print("Header:", json.dumps(working_decoded['header'], indent=2))
        print("Payload:", json.dumps(working_decoded['payload'], indent=2))
        
        # Check expiration
        exp_timestamp = working_decoded['payload'].get('exp')
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            current_datetime = datetime.now()
            print(f"Expires: {exp_datetime}")
            print(f"Current: {current_datetime}")
            print(f"Is expired: {current_datetime > exp_datetime}")
        print()
    
    # Compare tokens
    if real_decoded and working_decoded:
        print("🔍 COMPARISON:")
        print("=" * 30)
        
        real_payload = real_decoded['payload']
        working_payload = working_decoded['payload']
        
        # Compare key fields
        fields_to_compare = ['sub', 'email', 'cognito:groups', 'token_use', 'client_id', 'username']
        
        for field in fields_to_compare:
            real_value = real_payload.get(field)
            working_value = working_payload.get(field)
            
            if real_value == working_value:
                print(f"✅ {field}: MATCH")
            else:
                print(f"❌ {field}: DIFFERENT")
                print(f"   Real: {real_value}")
                print(f"   Working: {working_value}")
        
        # Check for extra fields in real token
        real_keys = set(real_payload.keys())
        working_keys = set(working_payload.keys())
        
        extra_in_real = real_keys - working_keys
        extra_in_working = working_keys - real_keys
        
        if extra_in_real:
            print(f"🔍 Extra fields in real token: {extra_in_real}")
            for field in extra_in_real:
                print(f"   {field}: {real_payload[field]}")
        
        if extra_in_working:
            print(f"🔍 Extra fields in working token: {extra_in_working}")
            for field in extra_in_working:
                print(f"   {field}: {working_payload[field]}")

if __name__ == "__main__":
    main()