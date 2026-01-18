#!/usr/bin/env python3
"""
Find ALL API Gateways and look for /members/me endpoint
"""

import boto3
import json

def find_all_apis_members_me():
    """Find all API Gateways and look for /members/me"""
    
    print("=" * 60)
    print("Searching ALL API Gateways for /members/me endpoint")
    print("=" * 60)
    
    try:
        apigateway = boto3.client('apigateway', region_name='eu-west-1')
        
        # List ALL REST APIs
        apis_response = apigateway.get_rest_apis()
        apis = apis_response.get('items', [])
        
        print(f"✅ Found {len(apis)} API Gateways")
        
        members_me_found = False
        
        for api in apis:
            api_id = api['id']
            api_name = api['name']
            
            print(f"\n📡 API: {api_name} (ID: {api_id})")
            
            # Get resources for this API
            try:
                resources_response = apigateway.get_resources(restApiId=api_id)
                resources = resources_response.get('items', [])
                
                # Look for /members/me specifically
                members_me_resource = None
                
                for resource in resources:
                    path = resource.get('path', '')
                    
                    if path == '/members/me':
                        members_me_found = True
                        members_me_resource = resource
                        print(f"   🎯 FOUND /members/me!")
                        
                        # Check methods
                        methods = resource.get('resourceMethods', {})
                        for method, method_config in methods.items():
                            if method != 'OPTIONS':
                                print(f"      🔗 {method} method available")
                                
                                # Get integration to see which Lambda it points to
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
                                            
                                            # This is our function! Let's check its logs
                                            print(f"         📝 Checking logs for this function...")
                                            check_function_logs(func_name)
                                            
                                except Exception as e:
                                    print(f"         ❌ Could not get integration: {str(e)}")
                    
                    elif '/members' in path:
                        print(f"   📍 Related path: {path}")
                
                if not members_me_resource:
                    print(f"   ❌ No /members/me endpoint found in this API")
            
            except Exception as e:
                print(f"   ❌ Error getting resources: {str(e)}")
        
        if not members_me_found:
            print(f"\n❌ /members/me endpoint not found in any API Gateway!")
            print(f"🔍 This means the GetMemberSelfFunction might not be deployed yet.")
        
    except Exception as e:
        print(f"❌ Error checking API Gateways: {str(e)}")

def check_function_logs(function_name):
    """Check recent logs for a specific function"""
    
    try:
        logs_client = boto3.client('logs', region_name='eu-west-1')
        log_group_name = f"/aws/lambda/{function_name}"
        
        from datetime import datetime, timedelta
        
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=10)
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)
        
        # Get recent log events
        events_response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time_ms,
            endTime=end_time_ms,
            limit=10
        )
        
        events = events_response.get('events', [])
        
        if events:
            print(f"         📊 Found {len(events)} recent log events:")
            for event in events[-5:]:  # Show last 5
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                print(f"         ⏰ {timestamp.strftime('%H:%M:%S')} - {message}")
                
                # Highlight errors
                if any(keyword in message.lower() for keyword in ['error', 'exception', 'traceback', 'failed', '500']):
                    print("         🚨 ERROR DETECTED!")
        else:
            print(f"         ❌ No recent log events")
            
    except Exception as e:
        print(f"         ❌ Error checking logs: {str(e)}")

if __name__ == "__main__":
    find_all_apis_members_me()