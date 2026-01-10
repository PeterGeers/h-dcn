#!/usr/bin/env python3
"""Final verification that everything works"""

import os
import importlib.util

def test_imports():
    """Test that all imports work correctly"""
    print("Testing imports...")
    
    # Test shared auth_utils import
    try:
        from shared.auth_utils import (
            extract_user_credentials,
            validate_permissions_with_regions
        )
        print("SUCCESS: shared auth_utils imported")
    except Exception as e:
        print(f"FAILED: shared auth_utils import failed: {e}")
        return False
    
    # Test handler imports
    current_dir = os.getcwd()
    
    # Test get_events
    try:
        get_events_path = os.path.join(current_dir, 'handler', 'get_events', 'app.py')
        spec = importlib.util.spec_from_file_location("get_events_handler", get_events_path)
        get_events_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(get_events_module)
        
        if hasattr(get_events_module, 'lambda_handler'):
            print("SUCCESS: get_events handler imported and lambda_handler found")
        else:
            print("FAILED: get_events lambda_handler not found")
            return False
    except Exception as e:
        print(f"FAILED: get_events import failed: {e}")
        return False
    
    # Test create_member
    try:
        create_member_path = os.path.join(current_dir, 'handler', 'create_member', 'app.py')
        spec = importlib.util.spec_from_file_location("create_member_handler", create_member_path)
        create_member_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_member_module)
        
        if hasattr(create_member_module, 'lambda_handler'):
            print("SUCCESS: create_member handler imported and lambda_handler found")
        else:
            print("FAILED: create_member lambda_handler not found")
            return False
    except Exception as e:
        print(f"FAILED: create_member import failed: {e}")
        return False
    
    return True

def test_dependencies():
    """Test that required dependencies are available"""
    print("Testing dependencies...")
    
    try:
        import boto3
        print("SUCCESS: boto3 available")
    except ImportError:
        print("FAILED: boto3 not available")
        return False
    
    try:
        import gspread
        print("SUCCESS: gspread available")
    except ImportError:
        print("FAILED: gspread not available")
        return False
    
    try:
        import requests
        print("SUCCESS: requests available")
    except ImportError:
        print("FAILED: requests not available")
        return False
    
    return True

def main():
    print("Final Verification Test")
    print("=" * 40)
    
    imports_ok = test_imports()
    deps_ok = test_dependencies()
    
    print("=" * 40)
    if imports_ok and deps_ok:
        print("ALL TESTS PASSED!")
        print("Your Python environment is working correctly.")
        print("Virtual environment (.venv) is ready for development.")
    else:
        print("SOME TESTS FAILED!")
        print("Please check the errors above.")
    
    print("=" * 40)

if __name__ == "__main__":
    main()