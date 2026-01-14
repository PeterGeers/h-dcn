"""
Validate Python syntax for all handler files
Run this after any script that modifies Python files
"""
import os
import py_compile
import sys

def validate_python_file(filepath):
    """Validate Python syntax for a single file"""
    try:
        py_compile.compile(filepath, doraise=True)
        return True, "OK"
    except py_compile.PyCompileError as e:
        return False, str(e)

def main():
    """Validate all Python files in backend/handler"""
    handler_dir = 'backend/handler'
    errors = []
    checked = 0
    skipped = 0
    
    print("Validating Python syntax in all handlers...")
    print("=" * 60)
    
    for root, dirs, files in os.walk(handler_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                
                # Skip non-critical files
                if file == '__init__.py' or 'migration_template' in file or 'docker-build-temp' in filepath:
                    skipped += 1
                    continue
                
                checked += 1
                success, message = validate_python_file(filepath)
                
                if not success:
                    print(f"❌ {filepath}")
                    print(f"   Error: {message}")
                    errors.append((filepath, message))
                else:
                    print(f"✅ {filepath}")
    
    print("=" * 60)
    print(f"\n📊 Checked {checked} Python files (skipped {skipped} non-critical files)")
    
    if errors:
        print(f"❌ Found {len(errors)} files with syntax errors:")
        for filepath, message in errors:
            print(f"   - {filepath}")
        sys.exit(1)
    else:
        print("✅ All Python files have valid syntax!")
        sys.exit(0)

if __name__ == '__main__':
    main()
