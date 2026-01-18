#!/usr/bin/env python3
"""
Test script to verify cart functionality with Decimal conversion fix
"""

import requests
import json
import time

# Configuration
API_BASE_URL = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"
TEST_USER_EMAIL = "test@example.com"

# Test JWT token (you'll need to get this from the frontend)
# This is just a placeholder - you'll need to replace with actual token
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwZ..."

def get_auth_headers():
    """Get authentication headers for API requests"""
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {JWT_TOKEN}',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Enhanced-Groups': '["hdcnLeden"]'
    }

def test_cart_workflow():
    """Test complete cart workflow: create → add items → read cart"""
    
    print("🛒 Testing Cart Decimal Conversion Fix")
    print("=" * 50)
    
    headers = get_auth_headers()
    
    # Step 1: Create a cart
    print("\n1. Creating cart...")
    create_cart_data = {
        "user_email": TEST_USER_EMAIL,
        "customer_id": "test-customer-123"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/carts",
            headers=headers,
            json=create_cart_data
        )
        
        if response.status_code == 201:
            cart_data = response.json()
            cart_id = cart_data.get('cart_id')
            print(f"✅ Cart created successfully: {cart_id}")
        else:
            print(f"❌ Failed to create cart: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Error creating cart: {str(e)}")
        return
    
    # Step 2: Add items to cart (with float prices that need Decimal conversion)
    print("\n2. Adding items to cart...")
    cart_items = [
        {
            "product_id": "test-product-1",
            "name": "Test Product 1",
            "price": 29.99,  # Float value that needs Decimal conversion
            "quantity": 2
        },
        {
            "product_id": "test-product-2", 
            "name": "Test Product 2",
            "price": 15.50,  # Float value that needs Decimal conversion
            "quantity": 1
        }
    ]
    
    update_cart_data = {
        "items": cart_items,
        "total_amount": 75.48,  # Float value that needs Decimal conversion
        "item_count": 3
    }
    
    try:
        response = requests.put(
            f"{API_BASE_URL}/carts/{cart_id}/items",
            headers=headers,
            json=update_cart_data
        )
        
        if response.status_code == 200:
            print("✅ Items added to cart successfully")
        else:
            print(f"❌ Failed to add items to cart: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Error adding items to cart: {str(e)}")
        return
    
    # Step 3: Read cart (this should now work with Decimal conversion)
    print("\n3. Reading cart...")
    try:
        response = requests.get(
            f"{API_BASE_URL}/carts/{cart_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            cart_data = response.json()
            print("✅ Cart retrieved successfully!")
            print(f"📊 Cart details:")
            print(f"   - Cart ID: {cart_data.get('cart_id')}")
            print(f"   - User Email: {cart_data.get('user_email')}")
            print(f"   - Total Amount: {cart_data.get('total_amount')}")
            print(f"   - Item Count: {cart_data.get('item_count')}")
            print(f"   - Items: {len(cart_data.get('items', []))}")
            
            # Verify that numeric values are properly converted
            total_amount = cart_data.get('total_amount')
            if isinstance(total_amount, (int, float)):
                print("✅ Total amount is properly converted to numeric type")
            else:
                print(f"❌ Total amount type issue: {type(total_amount)}")
                
            # Check items for proper conversion
            items = cart_data.get('items', [])
            for i, item in enumerate(items):
                price = item.get('price')
                if isinstance(price, (int, float)):
                    print(f"✅ Item {i+1} price properly converted: {price}")
                else:
                    print(f"❌ Item {i+1} price type issue: {type(price)}")
                    
        else:
            print(f"❌ Failed to read cart: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error reading cart: {str(e)}")
    
    print("\n🎉 Cart workflow test completed!")

if __name__ == "__main__":
    print("⚠️  Note: You need to update JWT_TOKEN with a valid token from the frontend")
    print("⚠️  This script is for testing the backend Decimal conversion fix")
    print()
    
    # Uncomment the line below when you have a valid JWT token
    # test_cart_workflow()
    
    print("✅ Test script created. Update JWT_TOKEN and run to test.")