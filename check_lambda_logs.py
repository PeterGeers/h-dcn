#!/usr/bin/env python3
"""
Check CloudWatch logs for GetMembersFilteredFunction to analyze performance
"""

import boto3
from datetime import datetime, timedelta

def get_recent_logs():
    """Get recent logs from GetMembersFilteredFunction"""
    
    client = boto3.client('logs', region_name='eu-west-1')
    
    # Find the log group
    log_groups = client.describe_log_groups(
        logGroupNamePrefix='/aws/lambda/webshop-backend-dev-GetMembersFilteredFunction'
    )
    
    if not log_groups['logGroups']:
        print("❌ Log group not found")
        return
    
    log_group_name = log_groups['logGroups'][0]['logGroupName']
    print(f"📋 Log Group: {log_group_name}")
    print("=" * 80)
    
    # Get logs from last 10 minutes
    start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)
    
    # Query logs
    response = client.filter_log_events(
        logGroupName=log_group_name,
        startTime=start_time,
        endTime=end_time,
        limit=100
    )
    
    print(f"\n📊 Recent Log Events (last 10 minutes):\n")
    
    for event in response['events']:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        
        # Only show relevant log lines
        if any(keyword in message for keyword in ['[HANDLER]', '[LOAD_MEMBERS]', '[FILTER]', 'Duration:', 'Billed Duration:']):
            print(f"{timestamp.strftime('%H:%M:%S')} | {message}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    get_recent_logs()
