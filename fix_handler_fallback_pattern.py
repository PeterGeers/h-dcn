"""
Fix the fallback pattern in Lambda handlers to prevent handler redefinition
Instead of sys.exit(0), we'll use a flag to skip the rest of the module
"""
import os
import re

def fix_handler_file(filepath):
    """Fix the fallback pattern in a handler file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if this file has the problematic pattern
    if 'sys.exit(0)' not in content or 'create_smart_fallback_handler' not in content:
        return False
    
    # Pattern 1: Remove sys.exit(0) and the comment
    pattern1 = r'    # Exit early - the fallback handler will handle all requests\n    import sys\n    sys\.exit\(0\)\n'
    content = re.sub(pattern1, '', content)
    
    # Pattern 2: Add a flag after the fallback handler assignment
    # Find the line: lambda_handler = create_smart_fallback_handler("...")
    pattern2 = r'(    lambda_handler = create_smart_fallback_handler\([^)]+\))\n'
    replacement2 = r'\1\n    _auth_layer_available = False\nelse:\n    _auth_layer_available = True\n'
    content = re.sub(pattern2, replacement2, content)
    
    # Pattern 3: Wrap the rest of the code (after the try/except) in an if block
    # Find where the real lambda_handler function starts
    # This is tricky - we need to find the first "def lambda_handler" after the try/except
    
    # Split content into before and after the try/except block
    parts = content.split('except ImportError as e:')
    if len(parts) != 2:
        return False
    
    before_except = parts[0]
    after_except = parts[1]
    
    # Find the end of the except block (look for the next line that's not indented)
    lines = after_except.split('\n')
    except_block_lines = []
    rest_lines = []
    in_except_block = True
    
    for i, line in enumerate(lines):
        if in_except_block:
            # Check if this line is still part of the except block (indented or empty)
            if line.strip() == '' or line.startswith('    ') or line.startswith('\t'):
                except_block_lines.append(line)
            else:
                # Found the end of except block
                in_except_block = False
                rest_lines = lines[i:]
                break
        
    if not rest_lines:
        # All remaining lines are part of except block
        except_block_lines = lines
        rest_lines = []
    
    # Now wrap the rest in "if _auth_layer_available:"
    if rest_lines:
        # Add the conditional wrapper
        wrapped_rest = ['if _auth_layer_available:'] + ['    ' + line for line in rest_lines]
        new_content = before_except + 'except ImportError as e:' + '\n'.join(except_block_lines) + '\n' + '\n'.join(wrapped_rest)
    else:
        new_content = content
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def main():
    """Fix all handler files"""
    # Test with one file first
    test_file = 'backend/handler/scan_product/app.py'
    
    print(f"Testing fix on: {test_file}")
    if fix_handler_file(test_file):
        print(f"✅ Fixed: {test_file}")
        print("\nPlease review the changes before applying to all files!")
    else:
        print(f"❌ Could not fix: {test_file}")

if __name__ == '__main__':
    main()
