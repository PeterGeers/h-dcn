"""
Smart Maintenance Fallback for H-DCN Lambda Functions
Provides graceful failure when shared authentication system is unavailable
with structured logging and professional user experience
"""

import json
from datetime import datetime


def create_maintenance_response():
    """
    Create a standardized maintenance response when auth system is unavailable
    
    Returns:
        dict: Lambda response with 503 status and user-friendly message
    """
    return {
        'statusCode': 503,
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,DELETE,PATCH",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Enhanced-Groups,x-requested-with",
            "Access-Control-Allow-Credentials": "false"
        },
        'body': json.dumps({
            'error': 'Service Temporarily Unavailable',
            'message': 'Our authentication system is currently undergoing maintenance. Please try again in a few minutes.',
            'contact': 'webmaster@h-dcn.nl',
            'status': 'maintenance',
            'retry_after': '300',  # 5 minutes in seconds
            'timestamp': datetime.now().isoformat()
        })
    }


def log_auth_system_failure(context, import_error):
    """
    Log structured error information for easy debugging when auth system fails
    
    Args:
        context: Lambda context object
        import_error: The ImportError that occurred
    """
    error_details = {
        'timestamp': datetime.now().isoformat(),
        'error_type': 'AUTH_SYSTEM_FAILURE',
        'function_name': context.function_name if context else 'unknown',
        'import_error': str(import_error),
        'severity': 'CRITICAL',
        'action_required': 'Check shared auth system deployment',
        'contact': 'webmaster@h-dcn.nl',
        'log_group': f'/aws/lambda/{context.function_name}' if context else 'unknown'
    }

    # Log structured error for easy CloudWatch searching
    print(f"🚨 AUTH_SYSTEM_FAILURE: {json.dumps(error_details)}")
    print(f"🔍 FIND THIS LOG: CloudWatch → /aws/lambda/{context.function_name if context else 'FUNCTION_NAME'}")
    print(f"📧 CONTACT: webmaster@h-dcn.nl")
    
    return error_details


def create_smart_fallback_handler(handler_name="unknown"):
    """
    Create a smart fallback handler that provides structured error logging
    and professional maintenance messages when auth system fails
    
    Args:
        handler_name: Name of the handler for logging purposes
        
    Returns:
        function: Lambda handler that returns maintenance response with structured logging
    """
    def smart_fallback_lambda_handler(event, context):
        """
        Smart fallback handler - logs structured error and returns professional maintenance response
        """
        # Create structured error details
        error_details = {
            'timestamp': datetime.now().isoformat(),
            'error_type': 'AUTH_SYSTEM_FAILURE',
            'function_name': context.function_name if context else handler_name,
            'handler_name': handler_name,
            'severity': 'CRITICAL',
            'action_required': 'Check shared auth system deployment',
            'contact': 'webmaster@h-dcn.nl',
            'log_group': f'/aws/lambda/{context.function_name}' if context else f'/aws/lambda/{handler_name}'
        }

        # Log structured error for easy CloudWatch searching
        print(f"🚨 AUTH_SYSTEM_FAILURE: {json.dumps(error_details)}")
        print(f"🔍 FIND THIS LOG: CloudWatch → {error_details['log_group']}")
        print(f"📧 CONTACT: webmaster@h-dcn.nl")
        print(f"🔄 User should retry in 5 minutes")
        
        # Handle OPTIONS requests for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,DELETE,PATCH",
                    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Enhanced-Groups,x-requested-with",
                    "Access-Control-Allow-Credentials": "false"
                },
                'body': ''
            }
        
        return create_maintenance_response()
    
    return smart_fallback_lambda_handler


# For direct import in handlers - maintains backward compatibility
def lambda_handler(event, context):
    """
    Default maintenance handler for direct import
    """
    return create_smart_fallback_handler("maintenance_fallback")(event, context)


# Smart fallback pattern for handlers to use
def create_smart_fallback_pattern(context, import_error, handler_name="unknown"):
    """
    Create the smart fallback pattern that handlers should use when auth import fails
    
    Args:
        context: Lambda context object
        import_error: The ImportError that occurred
        handler_name: Name of the handler for logging
        
    Returns:
        function: Handler function that provides structured logging and maintenance response
    """
    # Log the auth system failure with structured data
    log_auth_system_failure(context, import_error)
    
    # Return the smart fallback handler
    return create_smart_fallback_handler(handler_name)