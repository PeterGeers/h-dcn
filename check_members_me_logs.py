#!/usr/bin/env python3
"""
Check CloudWatch logs for the /members/me endpoint
"""

import boto3
import json
from datetime import datetime, timedelta

def check_members_me_logs():
    """Check recent logs for the get_member_self function"""
    
    print("=" * 60)
    print("Checking CloudWatch logs for get_member_self function")
    print("=" * 60)
    
    # CloudWatch logs client
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    # Log group name for the get_member_self function
    log_group_name = '/aws/lambda/hdcn-backend-GetMemberSelfFunction-YourFunctionId'
    
    # Try to find the correct log group name
    try:
        # List log groups to find the correct one
        response = logs_client.describe_log_groups(
            logGroupNamePrefix='/aws/lambda/hdcn-backend-GetMemberSelf'
        )
        
        if response['logGroups']:
            log_group_name = response['logGroups'][0]['logGroupName']
            print(f"✅ Found log group: {log_group_name}")
        else:
            print("❌ No log group found for GetMemberSelf function")
            return
            
    except Exception as e:
        print(f"❌ Error finding log group: {str(e)}")
        return
    
    # Get recent log events (last 10 minutes)
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=10)
        
        # Convert to milliseconds since epoch
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)
        
        print(f"🔍 Searching logs from {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')}")
        
        # Get log events
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time_ms,
            endTime=end_time_ms,
            limit=50
        )
        
        events = response.get('events', [])
        
        if not events:
            print("❌ No recent log events found")
            return
        
        print(f"✅ Found {len(events)} log events")
        print("\n" + "=" * 60)
        print("RECENT LOG EVENTS:")
        print("=" * 60)
        
        for event in events[-10:]:  # Show last 10 events
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            
            print(f"\n⏰ {timestamp.strftime('%H:%M:%S')} - {message}")
            
            # Highlight errors
            if any(keyword in message.lower() for keyword in ['error', 'exception', 'traceback', 'failed']):
                print("🚨 ERROR DETECTED!")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Error reading logs: {str(e)}")

if __name__ == "__main__":
    check_members_me_logs()