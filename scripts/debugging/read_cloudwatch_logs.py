#!/usr/bin/env python3
"""
Read CloudWatch logs for webshop functions to debug the authentication issue
"""

import boto3
import json
from datetime import datetime, timedelta
import sys

def read_lambda_logs(function_name_pattern, hours_back=1):
    """Read CloudWatch logs for Lambda functions"""
    
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    # Get log groups that match the pattern
    try:
        response = logs_client.describe_log_groups()
        matching_groups = [
            group['logGroupName'] 
            for group in response['logGroups'] 
            if function_name_pattern in group['logGroupName']
        ]
        
        if not matching_groups:
            print(f"No log groups found matching pattern: {function_name_pattern}")
            return
        
        print(f"Found log groups: {matching_groups}")
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)
        
        print(f"Searching logs from {start_time} to {end_time}")
        
        for log_group in matching_groups:
            print(f"\n{'='*60}")
            print(f"LOG GROUP: {log_group}")
            print(f"{'='*60}")
            
            try:
                # Get recent log events
                response = logs_client.filter_log_events(
                    logGroupName=log_group,
                    startTime=start_timestamp,
                    endTime=end_timestamp,
                    limit=50
                )
                
                events = response.get('events', [])
                if not events:
                    print("No recent log events found")
                    continue
                
                print(f"Found {len(events)} log events:")
                
                for event in events[-10:]:  # Show last 10 events
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message'].strip()
                    
                    # Clean up the message for better readability
                    if message.startswith('START RequestId:') or message.startswith('END RequestId:') or message.startswith('REPORT RequestId:'):
                        continue  # Skip AWS runtime messages
                    
                    print(f"\n[{timestamp.strftime('%H:%M:%S')}] {message}")
                
            except Exception as e:
                print(f"Error reading logs from {log_group}: {str(e)}")
                
    except Exception as e:
        print(f"Error accessing CloudWatch logs: {str(e)}")

def search_for_specific_patterns():
    """Search for specific patterns in the logs"""
    
    logs_client = boto3.client('logs', region_name='eu-west-1')
    
    # Log groups to search
    log_groups = [
        "/aws/lambda/webshop-backend-dev-scanProductFunction-Mh5zoyqU5ATT",
        "/aws/lambda/webshop-backend-dev-CreateCartFunction-1Ej8Ej8Ej8Ej"  # This might be different
    ]
    
    # Find the actual CreateCart log group
    try:
        response = logs_client.describe_log_groups()
        create_cart_groups = [
            group['logGroupName'] 
            for group in response['logGroups'] 
            if 'CreateCartFunction' in group['logGroupName'] and 'webshop-backend-dev' in group['logGroupName']
        ]
        if create_cart_groups:
            log_groups[1] = create_cart_groups[0]
    except:
        pass
    
    # Search patterns
    patterns = [
        "FIX_2026_01_13_001",
        "AUTH_LAYER",
        "SHARED_AUTH_LAYER", 
        "FALLBACK_AUTH_LOCAL",
        "Invalid JWT token format",
        "Authorization header",
        "test@example.com",
        "hdcnLeden"
    ]
    
    # Time range - last 2 hours
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=2)
    start_timestamp = int(start_time.timestamp() * 1000)
    
    print(f"Searching for patterns in logs from {start_time}")
    
    for log_group in log_groups:
        print(f"\n{'='*60}")
        print(f"SEARCHING: {log_group}")
        print(f"{'='*60}")
        
        try:
            # Check if log group exists
            logs_client.describe_log_groups(logGroupNamePrefix=log_group)
            
            for pattern in patterns:
                try:
                    response = logs_client.filter_log_events(
                        logGroupName=log_group,
                        startTime=start_timestamp,
                        filterPattern=f'"{pattern}"',
                        limit=10
                    )
                    
                    events = response.get('events', [])
                    if events:
                        print(f"\nPattern '{pattern}' found {len(events)} times:")
                        for event in events:
                            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                            message = event['message'].strip()
                            print(f"  [{timestamp.strftime('%H:%M:%S')}] {message}")
                
                except Exception as e:
                    if "ResourceNotFoundException" not in str(e):
                        print(f"Error searching for pattern '{pattern}': {str(e)}")
        
        except Exception as e:
            print(f"Log group {log_group} not found or error: {str(e)}")

if __name__ == "__main__":
    print("CloudWatch Logs Reader for Webshop Authentication Debug")
    print("=" * 60)
    
    # First, search for specific patterns
    search_for_specific_patterns()
    
    # Then read recent logs from webshop functions
    print(f"\n\n{'='*60}")
    print("RECENT LOGS FROM WEBSHOP FUNCTIONS")
    print(f"{'='*60}")
    
    read_lambda_logs("scanProductFunction", hours_back=2)
    read_lambda_logs("CreateCartFunction", hours_back=2)