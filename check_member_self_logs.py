#!/usr/bin/env python3

import boto3
import json
from datetime import datetime, timedelta

def check_member_self_logs():
    """Check logs for GetMemberSelfFunction"""
    
    print("=" * 60)
    print("Checking GetMemberSelfFunction logs")
    print("=" * 60)
    
    # Initialize CloudWatch Logs client
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    # Function name from CloudFormation
    function_name = "webshop-backend-dev-GetMemberSelfFunction-kdgAKM2HTsbg"
    log_group_name = f"/aws/lambda/{function_name}"
    
    print(f"📋 Log group: {log_group_name}")
    
    # Get logs from the last 30 minutes
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=30)
    
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)
    
    print(f"🕐 Time range: {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')}")
    
    try:
        # Get log events
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_timestamp,
            endTime=end_timestamp
        )
        
        events = response.get('events', [])
        
        if not events:
            print("❌ No recent log events found")
            return
        
        print(f"✅ Found {len(events)} log events")
        print()
        
        # Show the most recent events
        for event in events[-10:]:  # Last 10 events
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            
            print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
        
        print()
        print("🔍 Looking for error patterns...")
        
        # Look for specific error patterns
        error_patterns = [
            "Error getting member_id from Cognito",
            "Failed to retrieve user information",
            "Error in lambda_handler",
            "Traceback",
            "Exception"
        ]
        
        for event in events:
            message = event['message']
            for pattern in error_patterns:
                if pattern in message:
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    print(f"❌ [{timestamp.strftime('%H:%M:%S')}] {message.strip()}")
    
    except Exception as e:
        print(f"❌ Error accessing logs: {str(e)}")

if __name__ == "__main__":
    check_member_self_logs()