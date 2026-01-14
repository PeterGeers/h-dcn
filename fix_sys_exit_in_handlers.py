"""
Fix sys.exit(0) in all Lambda handlers that prevents handler from being defined
"""
import os
import re

def fix_handler_file(filepath):
    """Remove sys.exit(0) from fallback code in handler"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match the sys.exit(0) block in the fallback
    pattern = r'(\s+# Exit early - the fallback handler will handle all requests\n\s+import sys\n\s+sys\.exit\(0\)\n)'
    
    if re.search(pattern, content):
        # Remove the sys.exit block but keep the comment
        new_content = re.sub(pattern, '', content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    return False

def main():
    """Fix all handler files"""
    handler_dir = 'backend/handler'
    fixed_count = 0
    
    for root, dirs, files in os.walk(handler_dir):
        for file in files:
            if file == 'app.py':
                filepath = os.path.join(root, file)
                if fix_handler_file(filepath):
                    print(f"✅ Fixed: {filepath}")
                    fixed_count += 1
    
    print(f"\n🎉 Fixed {fixed_count} handler files")

if __name__ == '__main__':
    main()
