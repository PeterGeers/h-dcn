#!/usr/bin/env python3
"""
Handler Authentication Standardization Script
Automatically migrates handlers from various authentication patterns to the shared auth system

Usage:
    python migrate_handlers_to_shared_auth.py --analyze    # Analyze current state
    python migrate_handlers_to_shared_auth.py --migrate    # Perform migrations
    python migrate_handlers_to_shared_auth.py --validate   # Validate migrations
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import re

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir / 'shared'))

try:
    from auth_utils import (
        update_auth_fallback_file,
        create_handler_migration_template,
        get_new_role_structure_mapping
    )
    SHARED_AUTH_AVAILABLE = True
except ImportError:
    print("⚠️  Shared auth_utils not available - running in analysis mode only")
    SHARED_AUTH_AVAILABLE = False

class HandlerAuthAnalyzer:
    """Analyzes and categorizes handler authentication patterns"""
    
    def __init__(self):
        self.handlers_dir = backend_dir / 'handler'
        self.analysis_results = {
            'shared_auth_system': [],      # Pattern 1: Using shared auth system
            'no_authentication': [],       # Pattern 2: No authentication
            'custom_jwt_hdcnleden': [],   # Pattern 3: Custom JWT + hdcnLeden
            'cognito_special': [],         # Pattern 4: Cognito-specific handlers
            'mixed_partial': [],           # Pattern 5: Mixed/partial implementation
            'unknown': []                  # Unclassified patterns
        }
        
    def analyze_all_handlers(self):
        """Analyze all handlers and categorize their authentication patterns"""
        print("🔍 Analyzing handler authentication patterns...")
        
        for handler_dir in self.handlers_dir.iterdir():
            if handler_dir.is_dir():
                self.analyze_handler(handler_dir)
        
        return self.analysis_results
    
    def analyze_handler(self, handler_dir):
        """Analyze a single handler's authentication pattern"""
        handler_name = handler_dir.name
        app_py = handler_dir / 'app.py'
        
        if not app_py.exists():
            return
        
        try:
            with open(app_py, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(app_py, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Analyze authentication pattern
        pattern = self.classify_auth_pattern(content, handler_name)
        
        handler_info = {
            'name': handler_name,
            'path': str(handler_dir),
            'app_py_path': str(app_py),
            'pattern_details': self.get_pattern_details(content, pattern),
            'migration_complexity': self.assess_migration_complexity(content, pattern),
            'estimated_time_minutes': self.estimate_migration_time(content, pattern)
        }
        
        self.analysis_results[pattern].append(handler_info)
    
    def classify_auth_pattern(self, content, handler_name):
        """Classify the authentication pattern used by a handler"""
        
        # Pattern 4: Cognito-specific handlers
        if handler_name.startswith('cognito_'):
            return 'cognito_special'
        
        # Pattern 1: Shared auth system
        if 'from shared.auth_utils import' in content or 'from auth_utils import' in content:
            if 'validate_permissions_with_regions' in content:
                return 'shared_auth_system'
            else:
                return 'mixed_partial'  # Partial migration
        
        # Pattern 2: No authentication
        if not self.has_authentication_check(content):
            return 'no_authentication'
        
        # Pattern 3: Custom JWT + hdcnLeden
        if 'extract_user_roles_from_jwt' in content and 'hdcnLeden' in content:
            return 'custom_jwt_hdcnleden'
        
        # Pattern 5: Mixed/partial or unknown
        if any(auth_indicator in content for auth_indicator in [
            'Authorization', 'Bearer', 'JWT', 'cognito:groups', 'user_roles'
        ]):
            return 'mixed_partial'
        
        return 'unknown'
    
    def has_authentication_check(self, content):
        """Check if handler has any form of authentication"""
        auth_indicators = [
            'Authorization',
            'Bearer',
            'JWT',
            'user_roles',
            'cognito:groups',
            'extract_user_credentials',
            'validate_permissions',
            'auth_header'
        ]
        return any(indicator in content for indicator in auth_indicators)
    
    def get_pattern_details(self, content, pattern):
        """Get detailed information about the authentication pattern"""
        details = {'pattern': pattern}
        
        if pattern == 'shared_auth_system':
            details['uses_regional_validation'] = 'validate_permissions_with_regions' in content
            details['has_fallback'] = 'from auth_fallback import' in content
            details['has_logging'] = 'log_successful_access' in content
        
        elif pattern == 'custom_jwt_hdcnleden':
            details['jwt_function_lines'] = self.count_jwt_function_lines(content)
            details['has_audit_logging'] = 'log_cart_audit' in content or 'log_payment_audit' in content
            details['has_security_logging'] = 'log_security_event' in content
        
        elif pattern == 'no_authentication':
            details['security_risk'] = 'HIGH'
            details['direct_db_access'] = 'table.scan()' in content or 'table.get_item' in content
        
        return details
    
    def count_jwt_function_lines(self, content):
        """Count lines in custom JWT extraction function"""
        if 'def extract_user_roles_from_jwt' not in content:
            return 0
        
        lines = content.split('\n')
        in_function = False
        line_count = 0
        indent_level = None
        
        for line in lines:
            if 'def extract_user_roles_from_jwt' in line:
                in_function = True
                line_count = 1
                indent_level = len(line) - len(line.lstrip())
                continue
            
            if in_function:
                if line.strip() == '':
                    line_count += 1
                    continue
                
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and line.strip():
                    # Function ended
                    break
                
                line_count += 1
        
        return line_count
    
    def assess_migration_complexity(self, content, pattern):
        """Assess the complexity of migrating this handler"""
        if pattern == 'shared_auth_system':
            return 'NONE'
        elif pattern == 'no_authentication':
            return 'LOW'
        elif pattern == 'cognito_special':
            return 'SPECIAL'
        elif pattern == 'custom_jwt_hdcnleden':
            jwt_lines = self.count_jwt_function_lines(content)
            if jwt_lines > 100:
                return 'HIGH'
            elif jwt_lines > 50:
                return 'MEDIUM'
            else:
                return 'LOW'
        else:
            return 'MEDIUM'
    
    def estimate_migration_time(self, content, pattern):
        """Estimate time required to migrate this handler (in minutes)"""
        complexity_time = {
            'NONE': 0,
            'LOW': 30,
            'MEDIUM': 45,
            'HIGH': 90,
            'SPECIAL': 0  # Requires special handling
        }
        
        complexity = self.assess_migration_complexity(content, pattern)
        return complexity_time.get(complexity, 60)

class HandlerMigrator:
    """Performs actual migration of handlers to shared auth system"""
    
    def __init__(self, analysis_results):
        self.analysis_results = analysis_results
        self.migration_results = []
    
    def migrate_all_handlers(self, dry_run=False):
        """Migrate all handlers that need migration"""
        print(f"🚀 Starting handler migration (dry_run={dry_run})...")
        
        # Priority order for migration
        migration_order = [
            ('no_authentication', 'CRITICAL'),
            ('custom_jwt_hdcnleden', 'HIGH'),
            ('mixed_partial', 'MEDIUM')
        ]
        
        for pattern, priority in migration_order:
            handlers = self.analysis_results.get(pattern, [])
            if handlers:
                print(f"\n📋 Migrating {len(handlers)} handlers with pattern '{pattern}' (Priority: {priority})")
                for handler_info in handlers:
                    self.migrate_handler(handler_info, dry_run)
        
        return self.migration_results
    
    def migrate_handler(self, handler_info, dry_run=False):
        """Migrate a single handler"""
        handler_name = handler_info['name']
        pattern = handler_info['pattern_details']['pattern']
        
        print(f"  🔧 Migrating {handler_name} ({pattern})...")
        
        if dry_run:
            print(f"    [DRY RUN] Would migrate {handler_name}")
            self.migration_results.append({
                'handler': handler_name,
                'status': 'DRY_RUN',
                'pattern': pattern,
                'estimated_time': handler_info['estimated_time_minutes']
            })
            return
        
        try:
            if pattern == 'no_authentication':
                result = self.migrate_no_auth_handler(handler_info)
            elif pattern == 'custom_jwt_hdcnleden':
                result = self.migrate_custom_jwt_handler(handler_info)
            elif pattern == 'mixed_partial':
                result = self.migrate_mixed_handler(handler_info)
            else:
                result = {'status': 'SKIPPED', 'reason': f'Pattern {pattern} not supported'}
            
            result['handler'] = handler_name
            result['pattern'] = pattern
            self.migration_results.append(result)
            
            if result['status'] == 'SUCCESS':
                print(f"    ✅ Successfully migrated {handler_name}")
            else:
                print(f"    ❌ Failed to migrate {handler_name}: {result.get('reason', 'Unknown error')}")
        
        except Exception as e:
            error_result = {
                'handler': handler_name,
                'pattern': pattern,
                'status': 'ERROR',
                'reason': str(e)
            }
            self.migration_results.append(error_result)
            print(f"    ❌ Error migrating {handler_name}: {str(e)}")
    
    def migrate_no_auth_handler(self, handler_info):
        """Migrate handler with no authentication"""
        handler_name = handler_info['name']
        app_py_path = handler_info['app_py_path']
        
        # Create backup
        backup_path = f"{app_py_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(app_py_path, backup_path)
        
        # Read current content
        with open(app_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Determine appropriate permission based on handler name
        permission_mapping = {
            'get_events': ['events_read'],
            'create_member': ['members_create'],
            'get_products': ['products_read'],
            'create_event': ['events_create'],
            'create_payment': ['payments_create']
        }
        
        required_permissions = permission_mapping.get(handler_name, ['basic_access'])
        
        # Generate new handler content
        new_content = self.generate_secure_handler_content(content, handler_name, required_permissions)
        
        # Write updated content
        with open(app_py_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return {
            'status': 'SUCCESS',
            'backup_created': backup_path,
            'permissions_added': required_permissions,
            'changes': ['Added shared auth imports', 'Added authentication check', 'Added permission validation']
        }
    
    def migrate_custom_jwt_handler(self, handler_info):
        """Migrate handler with custom JWT logic"""
        handler_name = handler_info['name']
        app_py_path = handler_info['app_py_path']
        
        # Create backup
        backup_path = f"{app_py_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(app_py_path, backup_path)
        
        # Read current content
        with open(app_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove custom JWT function and replace with shared auth
        new_content = self.replace_custom_jwt_with_shared_auth(content, handler_name)
        
        # Write updated content
        with open(app_py_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        jwt_lines_removed = handler_info['pattern_details'].get('jwt_function_lines', 0)
        
        return {
            'status': 'SUCCESS',
            'backup_created': backup_path,
            'jwt_lines_removed': jwt_lines_removed,
            'changes': ['Removed custom JWT function', 'Added shared auth imports', 'Replaced hdcnLeden check with permission validation']
        }
    
    def migrate_mixed_handler(self, handler_info):
        """Migrate handler with mixed/partial implementation"""
        # For now, create a migration template for manual review
        handler_name = handler_info['name']
        handler_dir = Path(handler_info['path'])
        
        template_content = f"""
# Migration Template for {handler_name}
# This handler has a mixed/partial authentication implementation
# Manual review and migration required

# Current pattern: Mixed/Partial
# Recommended action: Review current implementation and migrate to shared auth system

# Template for shared auth system:
{self.get_shared_auth_template(handler_name)}
"""
        
        template_path = handler_dir / f"{handler_name}_migration_template.py"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        return {
            'status': 'TEMPLATE_CREATED',
            'template_path': str(template_path),
            'reason': 'Mixed/partial implementation requires manual review'
        }
    
    def generate_secure_handler_content(self, original_content, handler_name, required_permissions):
        """Generate secure handler content with shared auth system"""
        
        # Extract the original handler logic (everything after imports and before lambda_handler)
        lines = original_content.split('\n')
        
        # Find lambda_handler function
        handler_start = None
        for i, line in enumerate(lines):
            if 'def lambda_handler' in line:
                handler_start = i
                break
        
        if handler_start is None:
            raise ValueError("Could not find lambda_handler function")
        
        # Extract original handler logic (inside lambda_handler)
        original_handler_logic = []
        in_handler = False
        indent_level = None
        
        for i in range(handler_start, len(lines)):
            line = lines[i]
            
            if 'def lambda_handler' in line:
                in_handler = True
                indent_level = len(line) - len(line.lstrip())
                continue
            
            if in_handler:
                if line.strip() == '':
                    original_handler_logic.append(line)
                    continue
                
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and line.strip() and not line.strip().startswith('#'):
                    # Function ended
                    break
                
                original_handler_logic.append(line)
        
        # Generate new secure handler
        new_content = f'''import json
import boto3
from datetime import datetime

# Import from shared auth layer (REQUIRED)
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("Using shared auth layer")
except ImportError:
    # Fallback to local auth_fallback.py
    from auth_fallback import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("Using fallback auth - ensure auth_fallback.py is updated")

# Original imports and setup (if any)
{self.extract_original_setup(original_content)}

def lambda_handler(event, context):
    """
    Secure handler using shared authentication system
    Migrated from no-auth pattern to shared auth system
    """
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Validate permissions
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, {required_permissions}, user_email, {{'operation': '{handler_name}'}}
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, '{handler_name}')
        
        # Original handler logic (secured)
{chr(10).join("        " + line for line in original_handler_logic if line.strip())}
        
    except Exception as e:
        print(f"Error in {handler_name}: {{str(e)}}")
        return create_error_response(500, f"Internal server error in {handler_name}")
'''
        
        return new_content
    
    def extract_original_setup(self, content):
        """Extract original imports and setup code (excluding lambda_handler)"""
        lines = content.split('\n')
        setup_lines = []
        
        for line in lines:
            if 'def lambda_handler' in line:
                break
            if line.strip() and not line.startswith('import') and not line.startswith('from'):
                setup_lines.append(line)
        
        return '\n'.join(setup_lines)
    
    def replace_custom_jwt_with_shared_auth(self, content, handler_name):
        """Replace custom JWT logic with shared auth system"""
        
        # Remove custom JWT function
        content_without_jwt = self.remove_custom_jwt_function(content)
        
        # Replace imports
        new_content = self.add_shared_auth_imports(content_without_jwt)
        
        # Replace authentication logic in lambda_handler
        new_content = self.replace_auth_logic_in_handler(new_content, handler_name)
        
        return new_content
    
    def remove_custom_jwt_function(self, content):
        """Remove the custom extract_user_roles_from_jwt function"""
        lines = content.split('\n')
        new_lines = []
        
        skip_function = False
        function_indent = None
        
        for line in lines:
            if 'def extract_user_roles_from_jwt' in line:
                skip_function = True
                function_indent = len(line) - len(line.lstrip())
                continue
            
            if skip_function:
                if line.strip() == '':
                    continue
                
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= function_indent and line.strip():
                    skip_function = False
                    new_lines.append(line)
                continue
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def add_shared_auth_imports(self, content):
        """Add shared auth system imports"""
        import_block = '''
# Import from shared auth layer (REQUIRED)
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("Using shared auth layer")
except ImportError:
    # Fallback to local auth_fallback.py
    from auth_fallback import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("Using fallback auth - ensure auth_fallback.py is updated")
'''
        
        # Find where to insert imports (after existing imports)
        lines = content.split('\n')
        insert_index = 0
        
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_index = i + 1
            elif line.strip() and not line.startswith('#'):
                break
        
        lines.insert(insert_index, import_block)
        return '\n'.join(lines)
    
    def replace_auth_logic_in_handler(self, content, handler_name):
        """Replace authentication logic in lambda_handler function"""
        
        # Map handler names to appropriate permissions
        permission_mapping = {
            'get_payments': ['payments_read'],
            'get_cart': ['webshop_access'],
            'clear_cart': ['webshop_access'],
            'create_cart': ['webshop_access'],
            'update_cart_items': ['webshop_access'],
            'create_order': ['orders_create'],
            'get_orders': ['orders_read']
        }
        
        required_permissions = permission_mapping.get(handler_name, ['webshop_access'])
        
        # Replace the authentication section
        old_auth_pattern = r'user_email, user_roles, auth_error = extract_user_roles_from_jwt\(event\).*?return.*?}'
        
        new_auth_logic = f'''user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Validate permissions (replaced hdcnLeden check with permission-based validation)
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, {required_permissions}, user_email, {{'operation': '{handler_name}'}}
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, '{handler_name}')'''
        
        # Use regex to replace the authentication section
        import re
        
        # Pattern to match the old authentication logic
        pattern = r"user_email, user_roles, auth_error = extract_user_roles_from_jwt\(event\).*?if 'hdcnLeden' not in user_roles:.*?}\s*}"
        
        new_content = re.sub(pattern, new_auth_logic, content, flags=re.DOTALL)
        
        # If regex replacement didn't work, try a simpler approach
        if new_content == content:
            # Manual replacement for specific patterns
            lines = content.split('\n')
            new_lines = []
            
            in_auth_section = False
            auth_indent = None
            
            for line in lines:
                if 'extract_user_roles_from_jwt(event)' in line:
                    in_auth_section = True
                    auth_indent = len(line) - len(line.lstrip())
                    # Replace with new auth logic
                    new_lines.extend([
                        ' ' * auth_indent + 'user_email, user_roles, auth_error = extract_user_credentials(event)',
                        ' ' * auth_indent + 'if auth_error:',
                        ' ' * auth_indent + '    return auth_error',
                        ' ' * auth_indent + '',
                        ' ' * auth_indent + f'# Validate permissions (replaced hdcnLeden check)',
                        ' ' * auth_indent + 'is_authorized, error_response, regional_info = validate_permissions_with_regions(',
                        ' ' * auth_indent + f'    user_roles, {required_permissions}, user_email, {{"operation": "{handler_name}"}}',
                        ' ' * auth_indent + ')',
                        ' ' * auth_indent + 'if not is_authorized:',
                        ' ' * auth_indent + '    return error_response',
                        ' ' * auth_indent + '',
                        ' ' * auth_indent + f'log_successful_access(user_email, user_roles, "{handler_name}")'
                    ])
                    continue
                
                if in_auth_section:
                    # Skip lines until we're out of the auth section
                    if "'hdcnLeden'" in line and 'return' in line:
                        # Skip the hdcnLeden check and its return statement
                        continue
                    elif line.strip() and len(line) - len(line.lstrip()) <= auth_indent:
                        # We're out of the auth section
                        in_auth_section = False
                        new_lines.append(line)
                    else:
                        # Still in auth section, skip
                        continue
                else:
                    new_lines.append(line)
            
            new_content = '\n'.join(new_lines)
        
        return new_content
    
    def get_shared_auth_template(self, handler_name):
        """Get template for shared auth system implementation"""
        return f'''
def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Validate permissions
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['appropriate_permission'], user_email, {{'operation': '{handler_name}'}}
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, '{handler_name}')
        
        # Your handler logic here
        
        return create_success_response({{"message": "Success"}})
        
    except Exception as e:
        print(f"Error in {handler_name}: {{str(e)}}")
        return create_error_response(500, f"Internal server error in {handler_name}")
'''

def print_analysis_report(analysis_results):
    """Print a comprehensive analysis report"""
    print("\n" + "="*80)
    print("📊 HANDLER AUTHENTICATION ANALYSIS REPORT")
    print("="*80)
    
    total_handlers = sum(len(handlers) for handlers in analysis_results.values())
    print(f"Total Handlers Analyzed: {total_handlers}")
    
    # Pattern breakdown
    for pattern, handlers in analysis_results.items():
        if not handlers:
            continue
        
        pattern_name = pattern.replace('_', ' ').title()
        count = len(handlers)
        
        print(f"\n📋 {pattern_name}: {count} handlers")
        
        if pattern == 'no_authentication':
            print("   ⚠️  SECURITY RISK - These handlers have no authentication!")
        elif pattern == 'custom_jwt_hdcnleden':
            total_jwt_lines = sum(h['pattern_details'].get('jwt_function_lines', 0) for h in handlers)
            print(f"   📝 Total duplicated JWT code: ~{total_jwt_lines} lines")
        
        for handler in handlers:
            complexity = handler['migration_complexity']
            time_est = handler['estimated_time_minutes']
            
            status_emoji = {
                'NONE': '✅',
                'LOW': '🟢', 
                'MEDIUM': '🟡',
                'HIGH': '🔴',
                'SPECIAL': '🔵'
            }.get(complexity, '❓')
            
            print(f"     {status_emoji} {handler['name']} ({complexity} complexity, ~{time_est}min)")
    
    # Summary statistics
    print(f"\n📈 MIGRATION SUMMARY")
    print("-" * 40)
    
    secure_count = len(analysis_results['shared_auth_system'])
    needs_migration = total_handlers - secure_count - len(analysis_results['cognito_special'])
    
    print(f"✅ Already Secure: {secure_count} handlers")
    print(f"🔧 Needs Migration: {needs_migration} handlers")
    print(f"🔵 Special Cases: {len(analysis_results['cognito_special'])} handlers")
    
    # Time estimates
    total_time = sum(
        sum(h['estimated_time_minutes'] for h in handlers)
        for pattern, handlers in analysis_results.items()
        if pattern not in ['shared_auth_system', 'cognito_special']
    )
    
    print(f"⏱️  Estimated Migration Time: {total_time} minutes ({total_time/60:.1f} hours)")
    
    # Priority recommendations
    print(f"\n🎯 PRIORITY RECOMMENDATIONS")
    print("-" * 40)
    
    critical_handlers = analysis_results['no_authentication']
    if critical_handlers:
        print(f"🚨 CRITICAL: Fix {len(critical_handlers)} handlers with no authentication immediately")
        for handler in critical_handlers:
            print(f"     - {handler['name']}")
    
    high_priority = analysis_results['custom_jwt_hdcnleden']
    if high_priority:
        print(f"🔴 HIGH: Migrate {len(high_priority)} handlers with custom JWT logic")
    
    medium_priority = analysis_results['mixed_partial']
    if medium_priority:
        print(f"🟡 MEDIUM: Review {len(medium_priority)} handlers with mixed implementation")

def print_migration_report(migration_results):
    """Print migration results report"""
    print("\n" + "="*80)
    print("🚀 HANDLER MIGRATION RESULTS")
    print("="*80)
    
    successful = [r for r in migration_results if r['status'] == 'SUCCESS']
    failed = [r for r in migration_results if r['status'] in ['ERROR', 'FAILED']]
    templates = [r for r in migration_results if r['status'] == 'TEMPLATE_CREATED']
    skipped = [r for r in migration_results if r['status'] == 'SKIPPED']
    
    print(f"✅ Successful Migrations: {len(successful)}")
    print(f"❌ Failed Migrations: {len(failed)}")
    print(f"📝 Templates Created: {len(templates)}")
    print(f"⏭️  Skipped: {len(skipped)}")
    
    if successful:
        print(f"\n✅ SUCCESSFUL MIGRATIONS")
        for result in successful:
            print(f"   - {result['handler']} ({result['pattern']})")
            if 'jwt_lines_removed' in result:
                print(f"     Removed {result['jwt_lines_removed']} lines of duplicated JWT code")
    
    if failed:
        print(f"\n❌ FAILED MIGRATIONS")
        for result in failed:
            print(f"   - {result['handler']}: {result.get('reason', 'Unknown error')}")
    
    if templates:
        print(f"\n📝 TEMPLATES CREATED (Manual Review Required)")
        for result in templates:
            print(f"   - {result['handler']}: {result['template_path']}")

def main():
    parser = argparse.ArgumentParser(description='Handler Authentication Standardization Tool')
    parser.add_argument('--analyze', action='store_true', help='Analyze current authentication patterns')
    parser.add_argument('--migrate', action='store_true', help='Perform handler migrations')
    parser.add_argument('--validate', action='store_true', help='Validate migrated handlers')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run (no actual changes)')
    parser.add_argument('--handler', type=str, help='Migrate specific handler only')
    
    args = parser.parse_args()
    
    if not any([args.analyze, args.migrate, args.validate]):
        args.analyze = True  # Default to analysis
    
    # Initialize analyzer
    analyzer = HandlerAuthAnalyzer()
    
    if args.analyze or args.migrate:
        print("🔍 Analyzing handler authentication patterns...")
        analysis_results = analyzer.analyze_all_handlers()
        print_analysis_report(analysis_results)
    
    if args.migrate:
        if not SHARED_AUTH_AVAILABLE:
            print("\n❌ Cannot perform migrations: shared auth_utils not available")
            print("   Make sure backend/shared/auth_utils.py is accessible")
            return
        
        migrator = HandlerMigrator(analysis_results)
        
        if args.handler:
            # Migrate specific handler
            handler_info = None
            for handlers in analysis_results.values():
                for h in handlers:
                    if h['name'] == args.handler:
                        handler_info = h
                        break
                if handler_info:
                    break
            
            if handler_info:
                print(f"\n🎯 Migrating specific handler: {args.handler}")
                migrator.migrate_handler(handler_info, args.dry_run)
            else:
                print(f"\n❌ Handler '{args.handler}' not found")
                return
        else:
            # Migrate all handlers
            migration_results = migrator.migrate_all_handlers(args.dry_run)
        
        print_migration_report(migrator.migration_results)
    
    if args.validate:
        print("\n🔍 Validating migrated handlers...")
        # Re-analyze to see current state
        validation_results = analyzer.analyze_all_handlers()
        
        secure_count = len(validation_results['shared_auth_system'])
        total_count = sum(len(handlers) for handlers in validation_results.values())
        
        print(f"✅ Secure handlers: {secure_count}/{total_count}")
        
        remaining_issues = []
        for pattern, handlers in validation_results.items():
            if pattern not in ['shared_auth_system', 'cognito_special'] and handlers:
                remaining_issues.extend(handlers)
        
        if remaining_issues:
            print(f"⚠️  Remaining issues: {len(remaining_issues)} handlers")
            for handler in remaining_issues:
                print(f"   - {handler['name']} ({handler['pattern_details']['pattern']})")
        else:
            print("🎉 All handlers successfully migrated to shared auth system!")

if __name__ == '__main__':
    main()