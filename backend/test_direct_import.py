#!/usr/bin/env python3
"""Test direct import without sys.path manipulation"""

import os
import importlib.util

def test_direct_import():
    """Test importing handler files directly using absolute paths"""
    
    # Get absolute paths
    current_dir = os.getcwd()
    get_events_path = os.path.join(current_dir, 'handler', 'get_events', 'app.py')
    create_member_path = os.path.join(current_dir, 'handler', 'create_member', 'app.py')
    
    print(f"Current directory: {current_dir}")
    print(f"get_events path: {get_events_path}")
    print(f"create_member path: {create_member_path}")
    
    # Test get_events
    print("\n🔍 Testing get_events direct import:")
    try:
        spec = importlib.util.spec_from_file_location("get_events_app", get_events_path)
        if spec is None:
            print("❌ Could not create spec")
        else:
            print("✅ Spec created successfully")
            
            module = importlib.util.module_from_spec(spec)
            print("✅ Module created successfully")
            
            # This is where the error usually occurs
            spec.loader.exec_module(module)
            print("✅ Module executed successfully")
            
            # Test if lambda_handler exists
            if hasattr(module, 'lambda_handler'):
                print("✅ lambda_handler function found")
            else:
                print("❌ lambda_handler function not found")
                
    except Exception as e:
        print(f"❌ Import failed: {e}")
        print(f"   Error type: {type(e)}")
        
        # Get more details about the error
        import traceback
        print("   Full traceback:")
        traceback.print_exc()
    
    # Test create_member
    print("\n🔍 Testing create_member direct import:")
    try:
        spec = importlib.util.spec_from_file_location("create_member_app", create_member_path)
        if spec is None:
            print("❌ Could not create spec")
        else:
            print("✅ Spec created successfully")
            
            module = importlib.util.module_from_spec(spec)
            print("✅ Module created successfully")
            
            spec.loader.exec_module(module)
            print("✅ Module executed successfully")
            
            if hasattr(module, 'lambda_handler'):
                print("✅ lambda_handler function found")
            else:
                print("❌ lambda_handler function not found")
                
    except Exception as e:
        print(f"❌ Import failed: {e}")
        print(f"   Error type: {type(e)}")
        
        import traceback
        print("   Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_import()