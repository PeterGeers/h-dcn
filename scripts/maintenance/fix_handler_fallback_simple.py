"""
Fix the fallback pattern in Lambda handlers using try/except/else
This prevents the real lambda_handler from overwriting the fallback handler
"""
import os
import re

def fix_handler_file(filepath):
    """Fix the fallback pattern in a handler file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the try/except block
    try_line_idx = None
    except_line_idx = None
    sys_exit_line_idx = None
    
    for i, line in enumerate(lines):
        if 'from shared.auth_utils import' in line and try_line_idx is None:
            # Find the try statement before this
            for j in range(i-1, -1, -1):
                if line.strip().startswith('try:'):
                    try_line_idx = j
                    break
        
        if 'except ImportError as e:' in line:
            except_line_idx = i
        
        if 'sys.exit(0)' in line:
            sys_exit_line_idx = i
    
    if try_line_idx is None or except_line_idx is None:
        return False, "Could not find try/except block"
    
    # Remove sys.exit(0) and related lines
    if sys_exit_line_idx:
        # Remove the comment line before sys.exit
        if sys_exit_line_idx > 0 and 'Exit early' in lines[sys_exit_line_idx - 2]:
            del lines[sys_exit_line_idx - 2:sys_exit_line_idx + 1]
        else:
            # Just remove sys.exit lines
            for i in range(len(lines) - 1, -1, -1):
                if 'sys.exit(0)' in lines[i] or (i > 0 and 'import sys' in lines[i] and 'sys.exit' in lines[i+1] if i+1 < len(lines) else False):
                    del lines[i]
    
    # Find the end of the except block and add 'else:'
    # The except block ends when we find a line that's not indented (or less indented)
    except_block_end = None
    for i in range(except_line_idx + 1, len(lines)):
        line = lines[i]
        # Skip empty lines
        if line.strip() == '':
            continue
        # Check if this line is less indented than except block content (should be 4 spaces)
        if not line.startswith('    ') or line.startswith('# ') and not line.startswith('    #'):
            except_block_end = i
            break
    
    if except_block_end is None:
        except_block_end = len(lines)
    
    # Insert 'else:' after the except block
    lines.insert(except_block_end, 'else:\n')
    
    # Now indent everything after 'else:' that was at module level
    # Find where the real code starts (after else:)
    for i in range(except_block_end + 1, len(lines)):
        line = lines[i]
        # Skip lines that are already indented or empty or comments at module level
        if line.strip() == '':
            continue
        if line.startswith('# ') or line.startswith('def ') or line.startswith('class ') or line.startswith('dynamodb') or line.startswith('table') or line.startswith('s3') or line.startswith('cognito'):
            # Indent this line and all following lines
            for j in range(i, len(lines)):
                if lines[j].strip() != '':  # Don't indent empty lines
                    lines[j] = '    ' + lines[j]
            break
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True, "Fixed"

def main():
    """Fix all handler files"""
    handler_dir = 'backend/handler'
    fixed_count = 0
    failed = []
    
    for root, dirs, files in os.walk(handler_dir):
        for file in files:
            if file == 'app.py':
                filepath = os.path.join(root, file)
                success, message = fix_handler_file(filepath)
                if success:
                    print(f"✅ Fixed: {filepath}")
                    fixed_count += 1
                else:
                    print(f"❌ Failed: {filepath} - {message}")
                    failed.append(filepath)
    
    print(f"\n🎉 Fixed {fixed_count} handler files")
    if failed:
        print(f"⚠️  Failed to fix {len(failed)} files:")
        for f in failed:
            print(f"   - {f}")

if __name__ == '__main__':
    main()
