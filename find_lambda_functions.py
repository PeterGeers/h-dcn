#!/usr/bin/env python3
"""
Find all Lambda functions and their log groups
"""

import boto3
import json

def find_lambda_functions():
    """Find all Lambda functions and their log groups"""
    
    print("=" * 60)
    print("Finding Lambda functions and log groups")
    print("=" * 60)
    
    # Lambda client
    lambda_client = boto3.client('lambda', region_name='eu-west-1')
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    try:
        # List all Lambda functions
        response = lambda_client.list_functions()
        functions = response.get('Functions', [])
        
        print(f"✅ Found {len(functions)} Lambda functions")
        
        # Filter for functions related to members or self
        member_functions = []
        for func in functions:
            func_name = func['FunctionName']
            if any(keyword in func_name.lower() for keyword in ['member', 'self', 'hdcn']):
                member_functions.append(func)
        
        print(f"\n📋 Member-related functions:")
        print("-" * 60)
        
        for func in member_functions:
            func_name = func['FunctionName']
            print(f"🔧 {func_name}")
            
            # Check if this could be our get_member_self function
            if 'member' in func_name.lower() and 'self' in func_name.lower():
                print(f"   ⭐ This might be our get_member_self function!")
                
                # Check its log group
                log_group_name = f"/aws/lambda/{func_name}"
                try:
                    logs_response = logs_client.describe_log_groups(
                        logGroupNamePrefix=log_group_name
                    )
                    if logs_response['logGroups']:
                        print(f"   📝 Log group: {log_group_name}")
                        
                        # Get recent logs
                        print(f"   🔍 Checking recent logs...")
                        from datetime import datetime, timedelta
                        
                        end_time = datetime.now()
                        start_time = end_time - timedelta(minutes=30)
                        start_time_ms = int(start_time.timestamp() * 1000)
                        end_time_ms = int(end_time.timestamp() * 1000)
                        
                        events_response = logs_client.filter_log_events(
                            logGroupName=log_group_name,
                            startTime=start_time_ms,
                            endTime=end_time_ms,
                            limit=20
                        )
                        
                        events = events_response.get('events', [])
                        if events:
                            print(f"   📊 Found {len(events)} recent log events")
                            print(f"   📄 Latest logs:")
                            for event in events[-5:]:  # Show last 5 events
                                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                                message = event['message'].strip()
                                print(f"      {timestamp.strftime('%H:%M:%S')} - {message[:100]}...")
                        else:
                            print(f"   ❌ No recent log events")
                    else:
                        print(f"   ❌ No log group found")
                except Exception as e:
                    print(f"   ❌ Error checking logs: {str(e)}")
        
        # Also check for any functions with 'get' and 'member'
        print(f"\n📋 All functions with 'get' and 'member':")
        print("-" * 60)
        
        for func in functions:
            func_name = func['FunctionName']
            if 'get' in func_name.lower() and 'member' in func_name.lower():
                print(f"🔧 {func_name}")
        
    except Exception as e:
        print(f"❌ Error listing functions: {str(e)}")

if __name__ == "__main__":
    find_lambda_functions()