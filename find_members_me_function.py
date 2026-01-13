#!/usr/bin/env python3
"""
Find the actual function handling /members/me
"""

import boto3
import json

def find_members_me_function():
    """Find the function handling /members/me"""
    
    print("=" * 60)
    print("Finding function handling /members/me")
    print("=" * 60)
    
    # Lambda client
    lambda_client = boto3.client('lambda', region_name='eu-west-1')
    
    try:
        # List all Lambda functions
        response = lambda_client.list_functions()
        functions = response.get('Functions', [])
        
        print(f"✅ Found {len(functions)} Lambda functions")
        
        # Look for functions that might handle /members/me
        candidates = []
        
        for func in functions:
            func_name = func['FunctionName']
            
            # Check for various patterns
            if any(pattern in func_name.lower() for pattern in [
                'memberself', 'member_self', 'getmemberself', 'self'
            ]):
                candidates.append(func_name)
                print(f"🎯 CANDIDATE: {func_name}")
        
        if not candidates:
            print("❌ No obvious candidates found")
            print("\n🔍 Let's check all webshop-backend functions:")
            
            webshop_functions = [f['FunctionName'] for f in functions if 'webshop-backend' in f['FunctionName']]
            
            for func_name in sorted(webshop_functions):
                print(f"   🔧 {func_name}")
                
                # Check if this could be our function by looking at its configuration
                try:
                    func_config = lambda_client.get_function(FunctionName=func_name)
                    code_uri = func_config.get('Code', {}).get('Location', '')
                    
                    # If we can't get the code location, skip detailed check
                    if 'member' in func_name.lower():
                        print(f"      📋 This is a member-related function")
                        
                        # Try to invoke it with a test event to see if it handles /members/me
                        # (We won't actually invoke, just check if it exists)
                        
                except Exception as e:
                    print(f"      ❌ Error checking function: {str(e)}")
        
        # Let's also check the API Gateway to see what endpoints are configured
        print(f"\n🌐 Checking API Gateway configuration...")
        
        try:
            apigateway = boto3.client('apigateway', region_name='eu-west-1')
            
            # List REST APIs
            apis_response = apigateway.get_rest_apis()
            apis = apis_response.get('items', [])
            
            for api in apis:
                api_id = api['id']
                api_name = api['name']
                
                if 'hdcn' in api_name.lower() or 'webshop' in api_name.lower():
                    print(f"\n📡 API: {api_name} (ID: {api_id})")
                    
                    # Get resources
                    try:
                        resources_response = apigateway.get_resources(restApiId=api_id)
                        resources = resources_response.get('items', [])
                        
                        for resource in resources:
                            path = resource.get('path', '')
                            if '/members' in path:
                                print(f"   📍 Path: {path}")
                                
                                # Check methods
                                methods = resource.get('resourceMethods', {})
                                for method, method_config in methods.items():
                                    if method != 'OPTIONS':
                                        print(f"      🔗 {method}")
                                        
                                        # Try to get integration to see which Lambda it points to
                                        try:
                                            integration = apigateway.get_integration(
                                                restApiId=api_id,
                                                resourceId=resource['id'],
                                                httpMethod=method
                                            )
                                            
                                            uri = integration.get('uri', '')
                                            if 'lambda' in uri:
                                                # Extract function name from URI
                                                if ':function:' in uri:
                                                    func_name = uri.split(':function:')[1].split('/')[0]
                                                    print(f"         🎯 Lambda: {func_name}")
                                                    
                                        except Exception as e:
                                            print(f"         ❌ Could not get integration: {str(e)}")
                    
                    except Exception as e:
                        print(f"   ❌ Error getting resources: {str(e)}")
        
        except Exception as e:
            print(f"❌ Error checking API Gateway: {str(e)}")
        
    except Exception as e:
        print(f"❌ Error listing functions: {str(e)}")

if __name__ == "__main__":
    find_members_me_function()