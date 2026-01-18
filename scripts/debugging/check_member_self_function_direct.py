#!/usr/bin/env python3
"""
Check if GetMemberSelfFunction exists and check its logs
"""

import boto3
import json
from datetime import datetime, timedelta

def check_member_self_function():
    """Check if the function exists and get its logs"""
    
    print("=" * 60)
    print("Checking GetMemberSelfFunction")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name='eu-west-1')
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    # List all functions and find ones with 'member' and 'self' in the name
    try:
        response = lambda_client.list_functions()
        functions = response.get('Functions', [])
        
        member_self_functions = []
        
        for func in functions:
            func_name = func['FunctionName']
            if 'member' in func_name.lower() and 'self' in func_name.lower():
                member_self_functions.append(func_name)
        
        if not member_self_functions:
            print("❌ No GetMemberSelfFunction found!")
            print("\n🔍 Let's check what's handling /members/me by looking at recent 500 errors...")
            
            # Check all Lambda functions for recent 500 errors
            for func in functions:
                func_name = func['FunctionName']
                if 'webshop-backend-dev' in func_name or 'member' in func_name.lower():
                    log_group_name = f"/aws/lambda/{func_name}"
                    
                    try:
                        end_time = datetime.now()
                        start_time = end_time - timedelta(minutes=5)
                        start_time_ms = int(start_time.timestamp() * 1000)
                        end_time_ms = int(end_time.timestamp() * 1000)
                        
                        # Look for 500 errors or /members/me
                        events_response = logs_client.filter_log_events(
                            logGroupName=log_group_name,
                            startTime=start_time_ms,
                            endTime=end_time_ms,
                            limit=5
                        )
                        
                        events = events_response.get('events', [])
                        
                        if events:
                            # Check if any event mentions /members/me or 500 error
                            for event in events:
                                message = event['message']
                                if '/members/me' in message or '500' in message or 'Internal Server Error' in message or 'member_self' in message.lower():
                                    print(f"\n🎯 FOUND RELEVANT LOGS in: {func_name}")
                                    print(f"📝 Log group: {log_group_name}")
                                    
                                    # Get more logs from this function
                                    all_events = logs_client.filter_log_events(
                                        logGroupName=log_group_name,
                                        startTime=start_time_ms,
                                        endTime=end_time_ms,
                                        limit=20
                                    )
                                    
                                    print(f"📊 Recent logs:")
                                    for evt in all_events.get('events', [])[-10:]:
                                        timestamp = datetime.fromtimestamp(evt['timestamp'] / 1000)
                                        msg = evt['message'].strip()
                                        print(f"   ⏰ {timestamp.strftime('%H:%M:%S')} - {msg}")
                                        
                                        if any(keyword in msg.lower() for keyword in ['error', 'exception', 'traceback', 'failed']):
                                            print("   🚨 ERROR!")
                                    
                                    return
                    
                    except Exception as e:
                        # Skip functions we can't access
                        pass
            
            print("\n❌ No recent logs found for /members/me endpoint")
            return
        
        print(f"✅ Found {len(member_self_functions)} GetMemberSelf function(s):")
        
        for func_name in member_self_functions:
            print(f"\n🔧 Function: {func_name}")
            
            # Get function details
            try:
                func_details = lambda_client.get_function(FunctionName=func_name)
                print(f"   Runtime: {func_details['Configuration']['Runtime']}")
                print(f"   Handler: {func_details['Configuration']['Handler']}")
                print(f"   Last Modified: {func_details['Configuration']['LastModified']}")
                
                # Check logs
                log_group_name = f"/aws/lambda/{func_name}"
                print(f"   📝 Checking logs: {log_group_name}")
                
                end_time = datetime.now()
                start_time = end_time - timedelta(minutes=10)
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
                    print(f"   📊 Found {len(events)} recent log events:")
                    for event in events[-10:]:
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        message = event['message'].strip()
                        print(f"   ⏰ {timestamp.strftime('%H:%M:%S')} - {message}")
                        
                        if any(keyword in message.lower() for keyword in ['error', 'exception', 'traceback', 'failed', '500']):
                            print("   🚨 ERROR DETECTED!")
                else:
                    print(f"   ❌ No recent log events")
                
            except Exception as e:
                print(f"   ❌ Error checking function: {str(e)}")
    
    except Exception as e:
        print(f"❌ Error listing functions: {str(e)}")

if __name__ == "__main__":
    check_member_self_function()