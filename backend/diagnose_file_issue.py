#!/usr/bin/env python3
"""Diagnose the specific file import issue"""

import os
import sys
import importlib.util

def diagnose_file(filepath):
    """Diagnose a specific Python file for import issues"""
    print(f"\n🔍 Diagnosing: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"❌ File does not exist")
        return
    
    # Check file size
    size = os.path.getsize(filepath)
    print(f"📏 File size: {size} bytes")
    
    # Check for null bytes
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        null_count = content.count(b'\x00')
        print(f"🔍 Null bytes: {null_count}")
        
        if null_count > 0:
            print(f"❌ Found {null_count} null bytes!")
            # Find positions of null bytes
            positions = [i for i, b in enumerate(content) if b == 0]
            print(f"   Positions: {positions[:10]}...")  # Show first 10
            return False
    except Exception as e:
        print(f"❌ Binary read failed: {e}")
        return False
    
    # Check text encoding
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text_content = f.read()
        print(f"✅ UTF-8 read successful, {len(text_content)} characters")
    except Exception as e:
        print(f"❌ UTF-8 read failed: {e}")
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                text_content = f.read()
            print(f"⚠️ Latin-1 read successful, {len(text_content)} characters")
        except Exception as e2:
            print(f"❌ Latin-1 read also failed: {e2}")
            return False
    
    # Check compilation
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        compile(source, filepath, 'exec')
        print(f"✅ Compilation successful")
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        return False
    
    # Check importlib
    try:
        module_name = os.path.basename(filepath).replace('.py', '')
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None:
            print(f"❌ Could not create spec")
            return False
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"✅ importlib execution successful")
        return True
    except Exception as e:
        print(f"❌ importlib execution failed: {e}")
        print(f"   Error type: {type(e)}")
        return False

def main():
    print("🔧 Diagnosing Python file import issues")
    
    # Test files
    test_files = [
        'handler/get_events/app.py',
        'handler/create_member/app.py',
        'shared/auth_utils.py'
    ]
    
    results = {}
    for filepath in test_files:
        results[filepath] = diagnose_file(filepath)
    
    print(f"\n📊 Summary:")
    for filepath, success in results.items():
        status = "✅ OK" if success else "❌ FAILED"
        print(f"   {filepath}: {status}")
    
    # If files are corrupted, let's try to fix them
    failed_files = [f for f, success in results.items() if not success]
    if failed_files:
        print(f"\n🔧 Attempting to fix {len(failed_files)} corrupted files...")
        for filepath in failed_files:
            fix_file(filepath)

def fix_file(filepath):
    """Attempt to fix a corrupted file"""
    print(f"\n🔧 Fixing: {filepath}")
    
    try:
        # Read with different encodings and clean
        content = None
        
        # Try UTF-8 first
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            print("   ✅ Read with UTF-8")
        except:
            # Try latin-1
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    content = f.read()
                print("   ⚠️ Read with latin-1")
            except:
                # Try binary and decode
                try:
                    with open(filepath, 'rb') as f:
                        binary_content = f.read()
                    # Remove null bytes
                    clean_binary = binary_content.replace(b'\x00', b'')
                    content = clean_binary.decode('utf-8', errors='ignore')
                    print("   ⚠️ Read binary and cleaned null bytes")
                except Exception as e:
                    print(f"   ❌ Could not read file: {e}")
                    return False
        
        if content:
            # Create backup
            backup_path = f"{filepath}.backup_corrupted"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   ✅ Created backup: {backup_path}")
            
            # Write clean version
            with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            print(f"   ✅ Wrote clean version")
            
            # Test the fix
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    test_content = f.read()
                compile(test_content, filepath, 'exec')
                print(f"   ✅ Fix successful - file compiles")
                return True
            except Exception as e:
                print(f"   ❌ Fix failed - still doesn't compile: {e}")
                return False
    
    except Exception as e:
        print(f"   ❌ Fix attempt failed: {e}")
        return False

if __name__ == "__main__":
    main()