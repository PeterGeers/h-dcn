#!/usr/bin/env python3
"""
Check the most recent logs to see the new timestamp-based fix versions
"""

import boto3
from datetime import datetime, timedelta

def check_recent_logs():
    """Check for very recent log events"""
    
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    # Look for logs from the last 10 minutes
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=10)
    start_timestamp = int(start_time.timestamp() * 1000)
    
    log_group = "/aws/lambda/webshop-backend-dev-scanProductFunction-Mh5zoyqU5ATT"
    
    print(f"Checking logs from {start_time} to {end_time}")
    print(f"Looking for timestamp-based fix versions (FIX_20260113_*)")
    
    try:
        # Get all recent events
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_timestamp,
            limit=20
        )
        
        events = response.get('events', [])
        if not events:
            print("No recent events found")
            return
        
        print(f"\nFound {len(events)} recent events:")
        
        for event in events:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            
            # Skip AWS runtime messages
            if any(x in message for x in ['START RequestId:', 'END RequestId:', 'REPORT RequestId:']):
                continue
            
            print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
            
            # Look for our new timestamp-based fix versions
            if 'FIX_20260113_' in message:
                print(f"  *** NEW DEPLOYMENT DETECTED: {message} ***")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_recent_logs()