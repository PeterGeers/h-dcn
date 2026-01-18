#!/usr/bin/env python3
"""
Check logs for the /members/me endpoint specifically
"""

import boto3
import json
from datetime import datetime, timedelta

def check_members_me_endpoint_logs():
    """Check logs for functions that might handle /members/me"""
    
    print("=" * 60)
    print("Checking logs for /members/me endpoint")
    print("=" * 60)
    
    # CloudWatch logs client
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    # Possible function names that might handle /members/me
    possible_functions = [
        'webshop-backend-GetMemberSelfFunction',
        'webshop-backend-GetMembersFunction',  # This might handle /members/me as well
        'hdcn-backend-GetMemberSelfFunction',
        'backend-GetMemberSelfFunction'
    ]
    
    # Also search for any function that has recent activity with "members/me" in logs
    try:
        # List all log groups for Lambda functions
        response = logs_client.describe_log_groups(
            logGroupNamePrefix='/aws/lambda/'
        )
        
        log_groups = response.get('logGroups', [])
        
        print(f"✅ Found {len(log_groups)} Lambda log groups")
        
        # Time range for recent logs
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=30)
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)
        
        print(f"🔍 Searching for '/members/me' in logs from {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')}")
        
        found_relevant_logs = False
        
        for log_group in log_groups:
            log_group_name = log_group['logGroupName']
            
            # Skip non-Lambda log groups
            if not log_group_name.startswith('/aws/lambda/'):
                continue
            
            try:
                # Search for logs containing "members/me" or "member_self" or error messages
                events_response = logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    startTime=start_time_ms,
                    endTime=end_time_ms,
                    filterPattern='[timestamp, request_id, level="ERROR"] OR "members/me" OR "member_self" OR "500" OR "Internal Server Error"',
                    limit=10
                )
                
                events = events_response.get('events', [])
                
                if events:
                    found_relevant_logs = True
                    function_name = log_group_name.replace('/aws/lambda/', '')
                    print(f"\n🔧 Function: {function_name}")
                    print(f"📝 Log group: {log_group_name}")
                    print(f"📊 Found {len(events)} relevant events:")
                    
                    for event in events:
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        message = event['message'].strip()
                        print(f"   ⏰ {timestamp.strftime('%H:%M:%S')} - {message}")
                        
                        # Highlight errors
                        if any(keyword in message.lower() for keyword in ['error', 'exception', 'traceback', 'failed', '500']):
                            print("   🚨 ERROR DETECTED!")
                    
                    print("-" * 60)
                    
            except Exception as e:
                # Skip log groups that we can't access or that don't exist
                if "does not exist" not in str(e):
                    print(f"   ⚠️  Could not check {log_group_name}: {str(e)}")
        
        if not found_relevant_logs:
            print("❌ No relevant logs found for /members/me endpoint")
            print("\n🔍 Let's check the most recent logs from GetMembers function:")
            
            # Check GetMembersFunction specifically
            members_function_logs = [lg for lg in log_groups if 'GetMembers' in lg['logGroupName']]
            
            for log_group in members_function_logs:
                log_group_name = log_group['logGroupName']
                print(f"\n📝 Checking: {log_group_name}")
                
                try:
                    events_response = logs_client.filter_log_events(
                        logGroupName=log_group_name,
                        startTime=start_time_ms,
                        endTime=end_time_ms,
                        limit=20
                    )
                    
                    events = events_response.get('events', [])
                    if events:
                        print(f"   📊 Found {len(events)} recent events:")
                        for event in events[-5:]:  # Show last 5
                            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                            message = event['message'].strip()
                            print(f"   ⏰ {timestamp.strftime('%H:%M:%S')} - {message[:150]}...")
                    else:
                        print("   ❌ No recent events")
                        
                except Exception as e:
                    print(f"   ❌ Error: {str(e)}")
        
    except Exception as e:
        print(f"❌ Error searching logs: {str(e)}")

if __name__ == "__main__":
    check_members_me_endpoint_logs()