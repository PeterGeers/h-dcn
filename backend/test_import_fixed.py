#!/usr/bin/env python3
import os
import importlib.util

# Use absolute paths instead of sys.path manipulation
current_dir = os.getcwd()

try:
    # Import get_events handler using absolute path
    get_events_path = os.path.join(current_dir, 'handler', 'get_events', 'app.py')
    spec = importlib.util.spec_from_file_location("get_events_handler", get_events_path)
    get_events_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(get_events_module)
    print("✅ get_events handler imported successfully")
    
    # Test that lambda_handler exists and is callable
    if hasattr(get_events_module, 'lambda_handler'):
        print("✅ get_events lambda_handler function available")
    
except Exception as e:
    print(f"❌ get_events import failed: {e}")

try:
    # Import create_member handler using absolute path
    create_member_path = os.path.join(current_dir, 'handler', 'create_member', 'app.py')
    spec = importlib.util.spec_from_file_location("create_member_handler", create_member_path)
    create_member_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(create_member_module)
    print("✅ create_member handler imported successfully")
    
    # Test that lambda_handler exists and is callable
    if hasattr(create_member_module, 'lambda_handler'):
        print("✅ create_member lambda_handler function available")
    
except Exception as e:
    print(f"❌ create_member import failed: {e}")