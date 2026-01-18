#!/usr/bin/env python3
"""Check logs for the /members API endpoint"""

import boto3
from datetime import datetime, timedelta

def check_members_logs():
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    log_group = '/aws/lambda/webshop-backend-GetMembersFunction-z0ONYeQsE2ge'
    
    print(f"🔍 Checking logs for: {log_group}")
    print("=" * 60)
    
    # Get logs from last 10 minutes
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=10)
    
    start_time_ms = int(start_time.timestamp() * 1000)
    end_time_ms = int(end_time.timestamp() * 1000)
    
    try:
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time_ms,
            endTime=end_time_ms,
            limit=100
        )
        
        events = response.get('events', [])
        
        if not events:
            print("❌ No logs found in the last 10 minutes")
            print("   This means the Lambda function is NOT being invoked!")
            print("   Possible causes:")
            print("   - API Gateway routing is broken")
            print("   - Lambda function doesn't exist")
            print("   - Wrong log group name")
        else:
            print(f"✅ Found {len(events)} log events\n")
            for event in events:
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
                
    except Exception as e:
        print(f"❌ Error reading logs: {str(e)}")

if __name__ == "__main__":
    check_members_logs()
