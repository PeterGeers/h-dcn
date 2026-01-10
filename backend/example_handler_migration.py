#!/usr/bin/env python3
"""
Example of how to use role migration helper functions in handlers
This demonstrates the migration patterns for updating handlers from legacy to new role structure
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from auth_utils import (
    validate_permissions_with_legacy_fallback,
    create_backward_compatible_role_check,
    generate_migration_report_for_handler,
    validate_user_has_new_role_structure,
    create_error_response,
    create_success_response
)


def example_legacy_handler_before_migration(event, context):
    """
    Example of a handler BEFORE migration - uses old role checking
    This is the pattern that needs to be updated
    """
    # OLD PATTERN - Hard-coded legacy role checks
    admin_roles = [
        'hdcnAdmins', 'Webmaster', 
        'National_Chairman', 'National_Secretary'
    ]
    
    # Simulate getting user roles from event
    user_roles = ['Members_CRUD', 'Regio_All', 'Some_Other_Role']  # Example user roles with new structure
    
    # OLD VALIDATION - Simple role list check
    if not any(role in admin_roles for role in user_roles):
        return create_error_response(403, 'Access denied: Insufficient permissions')
    
    # Handler logic here...
    return create_success_response({'message': 'Operation successful'})


def example_handler_during_migration(event, context):
    """
    Example of a handler DURING migration - uses backward compatibility
    This provides smooth transition while maintaining functionality
    """
    # MIGRATION PATTERN - Use backward compatible role checker
    # NOTE: Legacy _All roles have been removed - this is for reference only
    legacy_roles_to_check = ['Members_CRUD', 'Products_CRUD']  # Updated to new role structure
    role_checker = create_backward_compatible_role_check(legacy_roles_to_check)
    
    # Simulate getting user roles from event
    user_roles = ['Members_CRUD', 'Regio_All']  # Example user with new structure
    
    # BACKWARD COMPATIBLE VALIDATION
    has_access, access_details = role_checker(user_roles)
    
    if not has_access:
        return create_error_response(403, 'Access denied', access_details)
    
    # Log migration information
    if access_details.get('access_type') == 'legacy':
        print(f"MIGRATION_NEEDED: Handler using legacy roles: {access_details['matching_roles']}")
    elif access_details.get('access_type') == 'new_structure':
        print(f"SUCCESS: Handler using new role structure: {access_details['matching_roles']}")
    
    # Handler logic here...
    return create_success_response({
        'message': 'Operation successful',
        'access_info': access_details
    })


def example_handler_after_migration(event, context):
    """
    Example of a handler AFTER migration - uses new role structure only
    This is the final target pattern
    """
    # NEW PATTERN - Use enhanced validation with regions
    from auth_utils import extract_user_credentials, validate_permissions_with_regions
    
    # Extract credentials (includes both legacy and new role support)
    user_email, user_roles, auth_error = extract_user_credentials(event)
    if auth_error:
        return auth_error
    
    # NEW VALIDATION - Permission-based with regional support
    required_permissions = ['members_update', 'members_read']
    is_authorized, error_response, regional_info = validate_permissions_with_regions(
        user_roles, required_permissions, user_email
    )
    
    if not is_authorized:
        return error_response
    
    # Log successful access with regional info
    print(f"ACCESS_GRANTED: {user_email} with regional access: {regional_info}")
    
    # Handler logic here with regional filtering if needed...
    return create_success_response({
        'message': 'Operation successful',
        'regional_access': regional_info
    })


def demonstrate_migration_analysis():
    """
    Demonstrate how to analyze handlers for migration needs
    """
    print("=== Handler Migration Analysis ===\n")
    
    # Analyze different handler patterns
    handlers_to_analyze = [
        {
            'name': 'update_member',
            'current_roles': ['Members_CRUD', 'Products_CRUD', 'Regio_All', 'hdcnAdmins']  # Updated to new structure
        },
        {
            'name': 'admin_only_handler', 
            'current_roles': ['hdcnAdmins', 'Webmaster']
        },
        {
            'name': 'mixed_handler',
            'current_roles': ['Members_CRUD', 'Events_Read', 'Regio_All']  # Updated to new structure
        }
    ]
    
    for handler_info in handlers_to_analyze:
        report = generate_migration_report_for_handler(
            handler_info['name'], 
            handler_info['current_roles']
        )
        
        print(f"Handler: {report['handler_name']}")
        print(f"Migration needed: {report['migration_needed']}")
        print(f"Current roles: {report['current_roles']}")
        
        if report['migration_needed']:
            print("Recommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
            print(f"New role structure: {report['new_role_structure']}")
        else:
            print("✅ No migration needed")
        
        print("-" * 50)


def demonstrate_user_role_validation():
    """
    Demonstrate user role structure validation
    """
    print("\n=== User Role Structure Validation ===\n")
    
    test_users = [
        {
            'name': 'Admin User',
            'roles': ['hdcnAdmins']
        },
        {
            'name': 'New Structure User',
            'roles': ['Members_CRUD', 'Regio_All']
        },
        {
            'name': 'Regional User',
            'roles': ['Members_Read', 'Events_Read', 'Regio_Groningen/Drenthe']
        },
        {
            'name': 'Legacy User',
            'roles': ['Members_CRUD', 'Events_Read', 'Regio_All']  # Updated to new structure
        },
        {
            'name': 'Incomplete User',
            'roles': ['Members_CRUD']  # Missing region role
        }
    ]
    
    for user in test_users:
        validation = validate_user_has_new_role_structure(user['roles'])
        
        print(f"User: {user['name']}")
        print(f"Roles: {user['roles']}")
        print(f"Has new structure: {validation['has_new_structure']}")
        print(f"Message: {validation['validation_message']}")
        
        if validation['legacy_roles']:
            print(f"⚠️  Legacy roles found: {validation['legacy_roles']}")
        
        print("-" * 40)


def main():
    """
    Demonstrate the migration helper functions
    """
    print("🔄 Role Migration Helper Functions Demo\n")
    
    # Show migration analysis
    demonstrate_migration_analysis()
    
    # Show user validation
    demonstrate_user_role_validation()
    
    print("\n=== Handler Examples ===\n")
    
    # Simulate different handler patterns
    print("1. Legacy handler (before migration):")
    try:
        result = example_legacy_handler_before_migration({}, {})
        print(f"   Result: {result['statusCode']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n2. Handler during migration (backward compatible):")
    try:
        result = example_handler_during_migration({}, {})
        print(f"   Result: {result['statusCode']} - {result.get('body', '')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n3. Handler after migration (new structure):")
    print("   (Would require full event structure with JWT token)")
    
    print("\n✅ Migration helper functions are ready for use!")
    print("\nNext steps:")
    print("1. Use generate_migration_report_for_handler() to analyze each handler")
    print("2. Update handlers to use create_backward_compatible_role_check() during transition")
    print("3. Gradually migrate to validate_permissions_with_regions() for final implementation")


if __name__ == '__main__':
    main()