#!/usr/bin/env python3
"""Test handler directory structure and imports"""

import os
import sys

print("Testing handler directory structure...")

# Test 1: Check if handler directory exists and is accessible
try:
    handler_path = 'handler'
    if os.path.exists(handler_path):
        print(f"✅ Handler directory exists: {handler_path}")
        subdirs = [d for d in os.listdir(handler_path) if os.path.isdir(os.path.join(handler_path, d))]
        print(f"   Subdirectories: {len(subdirs)} found")
        print(f"   First few: {subdirs[:5]}")
    else:
        print(f"❌ Handler directory not found: {handler_path}")
except Exception as e:
    print(f"❌ Error accessing handler directory: {e}")

# Test 2: Check specific handler directories
test_handlers = ['get_events', 'create_member']
for handler_name in test_handlers:
    try:
        handler_dir = f'handler/{handler_name}'
        if os.path.exists(handler_dir):
            print(f"✅ {handler_name} directory exists")
            files = os.listdir(handler_dir)
            print(f"   Files: {files}")
            
            app_py = f'{handler_dir}/app.py'
            if os.path.exists(app_py):
                print(f"   ✅ app.py exists")
                # Check file size
                size = os.path.getsize(app_py)
                print(f"   File size: {size} bytes")
                
                # Check if file is readable
                with open(app_py, 'r', encoding='utf-8') as f:
                    content = f.read(100)  # Read first 100 chars
                print(f"   First 100 chars: {repr(content)}")
            else:
                print(f"   ❌ app.py not found")
        else:
            print(f"❌ {handler_name} directory not found")
    except Exception as e:
        print(f"❌ Error checking {handler_name}: {e}")

# Test 3: Try to create __init__.py files
try:
    # Create __init__.py in handler directory
    init_file = 'handler/__init__.py'
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write('# Handler package init')
        print("✅ Created handler/__init__.py")
    else:
        print("✅ handler/__init__.py already exists")
    
    # Create __init__.py in specific handler directories
    for handler_name in test_handlers:
        handler_init = f'handler/{handler_name}/__init__.py'
        if not os.path.exists(handler_init):
            with open(handler_init, 'w') as f:
                f.write(f'# {handler_name} handler init')
            print(f"✅ Created {handler_init}")
        else:
            print(f"✅ {handler_init} already exists")
            
except Exception as e:
    print(f"❌ Error creating __init__.py files: {e}")

# Test 4: Try importing with __init__.py files
try:
    import handler
    print("✅ handler package import works")
    
    # Try importing specific handlers
    import handler.get_events
    print("✅ handler.get_events import works")
    
    import handler.create_member  
    print("✅ handler.create_member import works")
    
except Exception as e:
    print(f"❌ Handler package import failed: {e}")
    print(f"   Error type: {type(e)}")

print("Handler structure tests completed.")