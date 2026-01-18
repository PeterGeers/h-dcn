#!/usr/bin/env python3
"""
Check for live logs from the frontend requests
"""

import boto3
from datetime import datetime, timedelta
import time

def check_live_logs():
    """Check for logs from the last few minutes"""
    
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    # Look for logs from the last 5 minutes
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=5)
    start_timestamp = int(start_time.timestamp() * 1000)
    
    log_group = "/aws/lambda/webshop-backend-dev-scanProductFunction-Mh5zoyqU5ATT"
    
    print(f"Checking for LIVE frontend requests from {start_time}")
    
    try:
        # Get all recent events
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_timestamp,
            limit=50
        )
        
        events = response.get('events', [])
        if not events:
            print("❌ No recent events found - frontend requests may not be reaching this function")
            return
        
        print(f"\nFound {len(events)} recent events:")
        
        # Look for events that match frontend requests
        frontend_requests = []
        test_requests = []
        
        for event in events:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            
            # Skip AWS runtime messages
            if any(x in message for x in ['START RequestId:', 'END RequestId:', 'REPORT RequestId:']):
                continue
            
            # Check if this looks like a frontend request
            if 'JWT token extracted (length: 449)' in message or 'JWT token extracted (length: 408)' in message:
                frontend_requests.append((timestamp, message))
            elif 'JWT token extracted (length: 4)' in message or 'test' in message:
                test_requests.append((timestamp, message))
            else:
                print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
        
        if frontend_requests:
            print(f"\n✅ FOUND {len(frontend_requests)} FRONTEND REQUESTS:")
            for timestamp, message in frontend_requests:
                print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
        else:
            print(f"\n❌ NO FRONTEND REQUESTS FOUND")
        
        if test_requests:
            print(f"\n🔧 Found {len(test_requests)} test requests:")
            for timestamp, message in test_requests[-3:]:  # Show last 3
                print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_live_logs()