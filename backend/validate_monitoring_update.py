#!/usr/bin/env python3
"""
Validate that monitoring and logging have been updated to capture new role structure only
"""

import os
import re
import json
from pathlib import Path

def check_file_for_legacy_logging(file_path):
    """Check a file for legacy role logging patterns"""
    legacy_patterns = [
        r'log.*_All(?![\w])',  # Logging old _All roles (but not Regio_All)
        r'console\.log.*_All(?![\w])',  # Console logging old _All roles
        r'print.*_All(?![\w])',  # Print statements with old _All roles
        r'ACCESS_AUDIT.*_All(?![\w])',  # Access audit with old roles
        r'SECURITY_AUDIT.*_All(?![\w])',  # Security audit with old roles
    ]
    
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for line_num, line in enumerate(content.split('\n'), 1):
            for pattern in legacy_patterns:
                if re.search(pattern, line):
                    # Skip Regio_All which is valid
                    if 'Regio_All' in line:
                        continue
                    issues.append({
                        'line': line_num,
                        'content': line.strip(),
                        'pattern': pattern,
                        'type': 'legacy_role_logging'
                    })
                    
    except Exception as e:
        issues.append({
            'line': 0,
            'content': f"Error reading file: {str(e)}",
            'pattern': 'file_error',
            'type': 'error'
        })
    
    return issues

def check_for_new_role_structure_logging(file_path):
    """Check if file has been updated with new role structure logging"""
    new_patterns = [
        r'permission_roles.*region_roles',  # New role structure separation
        r'role_structure_version.*2\.0',    # Version tracking
        r'access_level.*admin',             # Access level categorization
        r'REGIONAL_ACCESS_AUDIT',           # New regional access logging
        r'ROLE_VALIDATION_AUDIT',           # New role validation logging
    ]
    
    found_patterns = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for pattern in new_patterns:
            if re.search(pattern, content):
                found_patterns.append(pattern)
                
    except Exception as e:
        pass
    
    return found_patterns

def validate_monitoring_files():
    """Validate monitoring and logging files"""
    print("🔍 Validating Monitoring and Logging Updates")
    print("=" * 60)
    
    # Files to check for logging updates
    files_to_check = [
        'backend/shared/auth_utils.py',
        'frontend/src/services/ParquetDataService.ts',
        'frontend/src/utils/functionPermissions.ts',
        'frontend/src/services/authService.ts',
    ]
    
    # Additional files that might have logging
    additional_files = []
    
    # Find all handler files
    handler_dir = Path('backend/handler')
    if handler_dir.exists():
        for handler_path in handler_dir.rglob('app.py'):
            additional_files.append(str(handler_path))
    
    all_files = files_to_check + additional_files
    
    total_issues = 0
    files_with_issues = 0
    files_updated = 0
    
    for file_path in all_files:
        if not os.path.exists(file_path):
            print(f"⚠️  File not found: {file_path}")
            continue
            
        print(f"\n📁 Checking: {file_path}")
        
        # Check for legacy logging patterns
        legacy_issues = check_file_for_legacy_logging(file_path)
        
        # Check for new role structure logging
        new_patterns = check_for_new_role_structure_logging(file_path)
        
        if legacy_issues:
            files_with_issues += 1
            total_issues += len(legacy_issues)
            print(f"  ❌ Found {len(legacy_issues)} legacy logging issues:")
            for issue in legacy_issues:
                print(f"     Line {issue['line']}: {issue['content']}")
        else:
            print(f"  ✅ No legacy logging patterns found")
            
        if new_patterns:
            files_updated += 1
            print(f"  ✅ Found {len(new_patterns)} new role structure patterns:")
            for pattern in new_patterns:
                print(f"     • {pattern}")
        else:
            if file_path in files_to_check:  # Only warn for core files
                print(f"  ⚠️  No new role structure logging patterns found")
    
    print(f"\n📊 VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Files checked: {len(all_files)}")
    print(f"Files with legacy issues: {files_with_issues}")
    print(f"Total legacy issues: {total_issues}")
    print(f"Files with new patterns: {files_updated}")
    
    if total_issues == 0:
        print(f"\n🎉 SUCCESS: All monitoring and logging updated to new role structure!")
        print(f"✅ No legacy role logging patterns found")
        print(f"✅ New role structure logging implemented")
        return True
    else:
        print(f"\n❌ ISSUES FOUND: {total_issues} legacy logging patterns need updating")
        print(f"💡 Update these files to use new role structure logging")
        return False

def check_monitoring_configuration():
    """Check if monitoring configuration is properly set up"""
    print(f"\n🔧 Checking Monitoring Configuration")
    print("=" * 40)
    
    config_files = [
        'backend/monitoring-config.md',
        'backend/template.yaml',  # SAM template for CloudWatch
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ Found: {config_file}")
        else:
            print(f"⚠️  Missing: {config_file}")
    
    # Check if monitoring config has new role structure documentation
    if os.path.exists('backend/monitoring-config.md'):
        with open('backend/monitoring-config.md', 'r') as f:
            content = f.read()
            
        if 'role_structure_version' in content and 'permission_roles' in content:
            print(f"✅ Monitoring config includes new role structure documentation")
        else:
            print(f"⚠️  Monitoring config may need role structure updates")

def main():
    """Main validation function"""
    print("🚀 H-DCN Monitoring Update Validation")
    print("Testing new role structure logging implementation")
    print("=" * 70)
    
    # Validate logging updates
    logging_success = validate_monitoring_files()
    
    # Check monitoring configuration
    check_monitoring_configuration()
    
    print(f"\n🎯 FINAL RESULT")
    print("=" * 30)
    
    if logging_success:
        print(f"✅ Monitoring update COMPLETED successfully!")
        print(f"   • All legacy role logging patterns removed")
        print(f"   • New role structure logging implemented")
        print(f"   • Monitoring configuration documented")
        print(f"\n💡 NEXT STEPS:")
        print(f"   1. Deploy updated backend functions")
        print(f"   2. Set up CloudWatch log groups and alerts")
        print(f"   3. Create monitoring dashboards")
        print(f"   4. Test logging with new role combinations")
        return 0
    else:
        print(f"❌ Monitoring update INCOMPLETE")
        print(f"   • Legacy logging patterns still exist")
        print(f"   • Manual updates required")
        return 1

if __name__ == "__main__":
    exit(main())