"""
Fix indentation in handlers after the 'else:' block
All code after 'else:' should be indented by 4 spaces
"""
import os

def fix_handler_indentation(filepath):
    """Fix indentation in a handler file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the 'else:' line that comes after create_smart_fallback_handler
    else_line_idx = None
    for i, line in enumerate(lines):
        if line.strip() == 'else:':
            # Check if this is after create_smart_fallback_handler
            for j in range(max(0, i-5), i):
                if 'create_smart_fallback_handler' in lines[j]:
                    else_line_idx = i
                    break
            if else_line_idx:
                break
    
    if else_line_idx is None:
        return False, "No else: block found"
    
    # Indent all lines after 'else:' by 4 spaces (if not already indented)
    new_lines = lines[:else_line_idx + 1]  # Keep everything up to and including 'else:'
    
    for i in range(else_line_idx + 1, len(lines)):
        line = lines[i]
        # Skip empty lines
        if line.strip() == '':
            new_lines.append(line)
            continue
        
        # Check current indentation
        stripped = line.lstrip()
        current_indent = len(line) - len(stripped)
        
        # If line starts at column 0 or has less than 4 spaces, add 4 spaces
        if current_indent < 4:
            new_lines.append('    ' + line)
        else:
            # Already indented, keep as is
            new_lines.append(line)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    return True, "Fixed"

def main():
    """Fix all handler files"""
    handler_dir = 'backend/handler'
    fixed_count = 0
    
    for root, dirs, files in os.walk(handler_dir):
        for file in files:
            if file == 'app.py':
                filepath = os.path.join(root, file)
                success, message = fix_handler_indentation(filepath)
                if success:
                    print(f"✅ Fixed: {filepath}")
                    fixed_count += 1
                else:
                    print(f"⏭️  Skipped: {filepath} - {message}")
    
    print(f"\n🎉 Fixed {fixed_count} handler files")

if __name__ == '__main__':
    main()
