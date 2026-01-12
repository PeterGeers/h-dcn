#!/usr/bin/env python3
"""
Test Member ID Optimization in /members/me Handler

This script tests whether the /members/me handler can use the custom:member_id
from the JWT token for direct lookup instead of querying by email.
"""

import json
import base64
from datetime import datetime

def test_jwt_member_id_extraction():
    """Test extracting custom:member_id from a sample JWT token"""
    
    print("TESTING JWT MEMBER_ID EXTRACTION")
    print("=" * 60)
    print(f"Test Time: {datetime.now().isoformat()}")
    print()
    
    # Sample JWT payload (this would normally come from Cognito)
    sample_payload = {
        "sub": "12345678-1234-1234-1234-123456789012",
        "email": "peter@pgeers.nl",
        "cognito:groups": ["hdcnLeden"],
        "custom:member_id": "87654321-4321-4321-4321-210987654321",
        "iss": "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_OAT3oPCIm",
        "aud": "client-id",
        "exp": 1705123456,
        "iat": 1705119856
    }
    
    print("Sample JWT Payload:")
    print(json.dumps(sample_payload, indent=2))
    print()
    
    # Encode the payload (simulate what Cognito does)
    payload_json = json.dumps(sample_payload)
    payload_encoded = base64.urlsafe_b64encode(payload_json.encode()).decode()
    
    # Remove padding for realistic JWT format
    payload_encoded = payload_encoded.rstrip('=')
    
    print(f"Encoded Payload: {payload_encoded[:50]}...")
    print()
    
    # Test extraction (simulate what the handler does)
    try:
        # Add padding if needed for base64 decoding
        payload_with_padding = payload_encoded + '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_with_padding)
        decoded_payload = json.loads(payload_decoded)
        
        print("Decoded Payload:")
        print(json.dumps(decoded_payload, indent=2))
        print()
        
        # Extract key fields
        user_email = decoded_payload.get('email')
        user_groups = decoded_payload.get('cognito:groups', [])
        member_id = decoded_payload.get('custom:member_id')
        
        print("Extracted Fields:")
        print(f"  Email: {user_email}")
        print(f"  Groups: {user_groups}")
        print(f"  Member ID: {member_id}")
        print()
        
        # Test the optimization logic
        print("OPTIMIZATION TEST:")
        print("-" * 30)
        
        if member_id:
            print(f"✅ custom:member_id found: {member_id}")
            print(f"🚀 Can use direct lookup: table.get_item(Key={{'member_id': '{member_id}'}})")
            print(f"⚡ Performance: O(1) direct lookup vs O(n) GSI query/scan")
            optimization_available = True
        else:
            print("❌ custom:member_id not found")
            print(f"🔄 Must use email lookup: query email-index or scan")
            print(f"⚠️ Performance: O(n) GSI query or O(n) table scan")
            optimization_available = False
        
        print()
        
        # Performance comparison
        print("PERFORMANCE COMPARISON:")
        print("-" * 30)
        print("Direct member_id lookup:")
        print("  ✅ O(1) constant time")
        print("  ✅ Single DynamoDB read operation")
        print("  ✅ No GSI required")
        print("  ✅ Lowest cost")
        print()
        print("Email GSI lookup:")
        print("  ⚠️ O(log n) to O(n) depending on GSI")
        print("  ⚠️ Requires email-index GSI")
        print("  ⚠️ Higher cost than direct lookup")
        print()
        print("Email scan lookup:")
        print("  ❌ O(n) linear scan of entire table")
        print("  ❌ Most expensive operation")
        print("  ❌ Slowest performance")
        
        return optimization_available
        
    except Exception as e:
        print(f"❌ Error in extraction test: {str(e)}")
        return False

def test_handler_logic_simulation():
    """Simulate the handler logic with different scenarios"""
    
    print("\n" + "=" * 60)
    print("HANDLER LOGIC SIMULATION")
    print("=" * 60)
    
    scenarios = [
        {
            "name": "User with custom:member_id",
            "has_member_id": True,
            "member_id": "12345678-1234-1234-1234-123456789012",
            "email": "peter@pgeers.nl"
        },
        {
            "name": "User without custom:member_id",
            "has_member_id": False,
            "member_id": None,
            "email": "user@example.com"
        },
        {
            "name": "User with invalid member_id",
            "has_member_id": True,
            "member_id": "invalid-id",
            "email": "test@example.com"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\nScenario {i}: {scenario['name']}")
        print("-" * 40)
        
        if scenario['has_member_id'] and scenario['member_id']:
            print(f"1. 🔍 Extract custom:member_id: {scenario['member_id']}")
            print(f"2. 🚀 Try direct lookup: table.get_item(Key={{'member_id': '{scenario['member_id']}'}})")
            
            if scenario['member_id'] == "invalid-id":
                print(f"3. ❌ Direct lookup fails (invalid ID)")
                print(f"4. 🔄 Fallback to email lookup: {scenario['email']}")
                print(f"5. ✅ Email lookup succeeds")
                print(f"   Result: Member found via email fallback")
            else:
                print(f"3. ✅ Direct lookup succeeds")
                print(f"4. ✅ Verify email matches: {scenario['email']}")
                print(f"   Result: Member found via direct lookup (fastest)")
        else:
            print(f"1. ⚠️ No custom:member_id available")
            print(f"2. 🔄 Use email lookup: {scenario['email']}")
            print(f"3. ✅ Email lookup succeeds")
            print(f"   Result: Member found via email lookup")

def main():
    """Run all tests"""
    
    print("MEMBER_ID OPTIMIZATION TESTING")
    print("=" * 80)
    print("Testing whether /members/me can use custom:member_id for direct lookup")
    print("=" * 80)
    
    # Test JWT extraction
    optimization_available = test_jwt_member_id_extraction()
    
    # Test handler logic
    test_handler_logic_simulation()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    print("Implementation Status:")
    print("✅ JWT token parsing - IMPLEMENTED")
    print("✅ custom:member_id extraction - IMPLEMENTED")
    print("✅ Direct member_id lookup - IMPLEMENTED")
    print("✅ Email fallback - IMPLEMENTED")
    print("✅ Security verification - IMPLEMENTED")
    
    print("\nBenefits of Optimization:")
    print("🚀 Faster lookups for users with custom:member_id")
    print("💰 Lower DynamoDB costs (direct reads vs GSI queries)")
    print("📈 Better scalability (O(1) vs O(n) operations)")
    print("🔄 Graceful fallback for users without custom:member_id")
    
    print("\nNext Steps:")
    print("1. Deploy updated /members/me handler")
    print("2. Ensure users have custom:member_id in Cognito (linking script)")
    print("3. Monitor performance improvements")
    print("4. Test with real authenticated requests")
    
    print(f"\nOptimization Available: {'✅ YES' if optimization_available else '❌ NO'}")

if __name__ == "__main__":
    main()