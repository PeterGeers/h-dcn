#!/usr/bin/env python3
"""
Read the very latest CloudWatch logs for webshop functions
"""

import boto3
import json
from datetime import datetime, timedelta

def read_latest_logs():
    """Read the most recent logs from webshop functions"""
    
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    # Get all log groups
    response = logs_client.describe_log_groups()
    webshop_groups = [
        group['logGroupName'] 
        for group in response['logGroups'] 
        if 'webshop-backend' in group['logGroupName'] and 
           ('scanProduct' in group['logGroupName'] or 'CreateCart' in group['logGroupName'])
    ]
    
    print("🔍 Latest Webshop Logs (Last 10 minutes)")
    print("=" * 60)
    
    # Calculate time range - last 10 minutes
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=10)
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)
    
    print(f"Time range: {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')}")
    print()
    
    for log_group in webshop_groups:
        print(f"📋 LOG GROUP: {log_group}")
        print("-" * 40)
        
        try:
            # Get recent log events
            response = logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=start_timestamp,
                endTime=end_timestamp,
                limit=20
            )
            
            events = response.get('events', [])
            if not events:
                print("   No recent events")
                print()
                continue
            
            # Show all recent events
            for event in events[-10:]:  # Last 10 events
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                
                # Highlight important messages
                if any(keyword in message for keyword in ['JWT token full', 'Parts breakdown', 'Token preview', 'FIX_']):
                    print(f"🔍 [{timestamp.strftime('%H:%M:%S')}] {message}")
                elif 'ERROR' in message or '❌' in message:
                    print(f"❌ [{timestamp.strftime('%H:%M:%S')}] {message}")
                elif 'SUCCESS' in message or '✅' in message:
                    print(f"✅ [{timestamp.strftime('%H:%M:%S')}] {message}")
                else:
                    print(f"   [{timestamp.strftime('%H:%M:%S')}] {message}")
            
            print()
            
        except Exception as e:
            print(f"   Error reading logs: {str(e)}")
            print()

if __name__ == "__main__":
    read_latest_logs()