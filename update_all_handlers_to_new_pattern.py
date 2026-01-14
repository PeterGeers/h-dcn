"""
Update all Lambda handlers to use the correct fallback pattern:
1. Use shared.maintenance_fallback instead of local auth_fallback.py
2. Use try/except/else to prevent overwriting the fallback handler
"""
import os
import re

def update_handler_pattern(filepath):
    """Update a handler to use the new fallback pattern"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if this handler needs updating
    if 'from shared.auth_utils import' not in content:
        return False, "No auth import found"
    
    # Pattern 1: Replace old fallback with new maintenance fallback
    old_fallback_pattern = r'''except ImportError:
    # Fallback to local auth_fallback\.py \(UPDATED FOR NEW ROLE STRUCTURE\)
    from auth_fallback import \(
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    \)
    print\("Using fallback auth - ensure auth_fallback\.py is updated"\)'''
    
    new_fallback = '''except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"❌ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("HANDLER_NAME")
else:'''
    
    # Extract handler name from filepath
    handler_name = os.path.basename(os.path.dirname(filepath))
    if handler_name == 'handler':
        handler_name = 'unknown'
    
    new_fallback = new_fallback.replace('HANDLER_NAME', handler_name)
    
    # Replace the old pattern
    content = re.sub(old_fallback_pattern, new_fallback, content, flags=re.MULTILINE)
    
    # Pattern 2: If handler already has maintenance_fallback but no else, add else
    if 'create_smart_fallback_handler' in content and '\nelse:\n' not in content:
        # Find the line after lambda_handler = create_smart_fallback_handler(...)
        pattern = r'(lambda_handler = create_smart_fallback_handler\([^)]+\))\n'
        content = re.sub(pattern, r'\1\nelse:\n', content)
    
    # Pattern 3: Indent all code after 'else:' that should be inside the else block
    lines = content.split('\n')
    new_lines = []
    in_else_block = False
    else_indent_done = False
    
    for i, line in enumerate(lines):
        if line.strip() == 'else:' and 'create_smart_fallback_handler' in '\n'.join(lines[max(0,i-5):i]):
            in_else_block = True
            else_indent_done = False
            new_lines.append(line)
            continue
        
        if in_else_block and not else_indent_done:
            # Start indenting from the next non-empty line
            if line.strip() == '':
                new_lines.append(line)
                continue
            else:
                # This is the first line after else: - start indenting everything
                else_indent_done = True
                # Indent this line and all following lines
                if not line.startswith('    ') and line.strip() != '':
                    new_lines.append('    ' + line)
                else:
                    new_lines.append(line)
        elif in_else_block and else_indent_done:
            # Continue indenting
            if line.strip() != '' and not line.startswith('    '):
                new_lines.append('    ' + line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True, "Updated"

def main():
    """Update all handler files"""
    handler_dir = 'backend/handler'
    updated_count = 0
    skipped_count = 0
    
    for root, dirs, files in os.walk(handler_dir):
        for file in files:
            if file == 'app.py':
                filepath = os.path.join(root, file)
                success, message = update_handler_pattern(filepath)
                if success:
                    print(f"✅ Updated: {filepath}")
                    updated_count += 1
                else:
                    print(f"⏭️  Skipped: {filepath} - {message}")
                    skipped_count += 1
    
    print(f"\n🎉 Updated {updated_count} handler files")
    print(f"⏭️  Skipped {skipped_count} handler files")

if __name__ == '__main__':
    main()
