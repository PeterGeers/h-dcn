"""
Check handler file integrity
Ensures handlers have required components and aren't truncated
"""
import os
import sys

def check_handler_integrity(filepath):
    """Check if a handler file has required components"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check 1: File should have reasonable length (not truncated)
        # Only flag as error if it's VERY short (< 20 lines) or missing lambda_handler
        lines = content.split('\n')
        if len(lines) < 20:
            issues.append(f"File too short ({len(lines)} lines) - possibly truncated")
        
        # Check 2: Should have lambda_handler function
        if 'def lambda_handler(' not in content:
            issues.append("Missing 'def lambda_handler' function")
        
        # Check 3: Should have auth import (unless it's a Cognito trigger or uses maintenance fallback)
        is_cognito_trigger = 'cognito' in filepath.lower()
        has_maintenance_fallback = 'maintenance_fallback' in content
        has_auth_import = 'from shared.auth_utils import' in content or 'from auth_fallback import' in content
        
        if not has_auth_import and not is_cognito_trigger and not has_maintenance_fallback:
            issues.append("Missing auth import")
        
        # Check 4: sys.exit(0) is OK if it's in a maintenance fallback pattern
        if 'sys.exit(0)' in content and not has_maintenance_fallback:
            issues.append("Contains sys.exit(0) which can break handler initialization")
        
        # Check 5: Should have proper return statements (unless it's a Cognito trigger)
        has_return = 'return create_success_response' in content or 'return create_error_response' in content or 'return {' in content
        if not has_return and not is_cognito_trigger:
            issues.append("No return statements found")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        return False, [f"Error reading file: {str(e)}"]

def main():
    """Check all handler files"""
    handler_dir = 'backend/handler'
    errors = []
    warnings = []
    checked = 0
    
    print("🔍 Checking handler file integrity...")
    print("=" * 60)
    
    for root, dirs, files in os.walk(handler_dir):
        for file in files:
            if file == 'app.py':
                filepath = os.path.join(root, file)
                checked += 1
                is_ok, issues = check_handler_integrity(filepath)
                
                if not is_ok:
                    print(f"❌ {filepath}")
                    for issue in issues:
                        print(f"   - {issue}")
                    
                    # Determine if it's an error or warning
                    if any('truncated' in i or 'lambda_handler' in i for i in issues):
                        errors.append((filepath, issues))
                    else:
                        warnings.append((filepath, issues))
                else:
                    print(f"✅ {filepath}")
    
    print("=" * 60)
    print(f"\n📊 Checked {checked} handler files")
    
    if errors:
        print(f"\n❌ Found {len(errors)} files with ERRORS:")
        for filepath, issues in errors:
            print(f"   {filepath}:")
            for issue in issues:
                print(f"      - {issue}")
    
    if warnings:
        print(f"\n⚠️  Found {len(warnings)} files with WARNINGS:")
        for filepath, issues in warnings:
            print(f"   {filepath}:")
            for issue in issues:
                print(f"      - {issue}")
        print("\n💡 Warnings are informational - they may be false positives for simple handlers")
    
    if errors:
        print("\n🚫 Handler integrity check FAILED!")
        sys.exit(1)
    elif warnings:
        print("\n⚠️  Handler integrity check passed with warnings")
        sys.exit(0)
    else:
        print("\n✅ All handlers passed integrity check!")
        sys.exit(0)

if __name__ == '__main__':
    main()
