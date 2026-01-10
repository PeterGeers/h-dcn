#!/usr/bin/env python3
"""Test basic Python import functionality"""

print("Testing basic Python functionality...")

# Test 1: Basic imports
try:
    import os
    import sys
    import json
    print("✅ Basic imports work")
except Exception as e:
    print(f"❌ Basic imports failed: {e}")

# Test 2: Create and import a simple module
try:
    with open('test_module.py', 'w') as f:
        f.write('def test_function():\n    return "Hello from test module"')
    
    import test_module
    result = test_module.test_function()
    print(f"✅ Simple module import works: {result}")
    
    # Clean up
    os.remove('test_module.py')
    if os.path.exists('test_module.pyc'):
        os.remove('test_module.pyc')
        
except Exception as e:
    print(f"❌ Simple module import failed: {e}")

# Test 3: Test importlib directly
try:
    import importlib.util
    
    # Create a test file
    with open('test_importlib.py', 'w') as f:
        f.write('TEST_VAR = "importlib test"')
    
    spec = importlib.util.spec_from_file_location("test_importlib", "test_importlib.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    print(f"✅ importlib works: {module.TEST_VAR}")
    
    # Clean up
    os.remove('test_importlib.py')
    
except Exception as e:
    print(f"❌ importlib failed: {e}")

# Test 4: Test with subdirectory structure
try:
    os.makedirs('test_package', exist_ok=True)
    
    with open('test_package/__init__.py', 'w') as f:
        f.write('')
    
    with open('test_package/submodule.py', 'w') as f:
        f.write('def sub_function():\n    return "Hello from submodule"')
    
    from test_package.submodule import sub_function
    result = sub_function()
    print(f"✅ Package import works: {result}")
    
    # Clean up
    import shutil
    shutil.rmtree('test_package')
    
except Exception as e:
    print(f"❌ Package import failed: {e}")

print("Basic import tests completed.")