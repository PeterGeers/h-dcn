"""
Check CloudWatch logs for get_members_filtered Lambda function
"""
import boto3
from datetime import datetime, timedelta
import json

# Initialize CloudWatch Logs client
logs_client = boto3.client('logs', region_name='eu-west-1')

# Lambda function name
FUNCTION_NAME = 'webshop-backend-dev-GetMembersFilteredFunction-dSATIeNyPrh6'
LOG_GROUP = f'/aws/lambda/{FUNCTION_NAME}'

print("=" * 80)
print(f"Checking logs for: {FUNCTION_NAME}")
print("=" * 80)
print()

try:
    # Get log streams (most recent first)
    response = logs_client.describe_log_streams(
        logGroupName=LOG_GROUP,
        orderBy='LastEventTime',
        descending=True,
        limit=5
    )
    
    if not response['logStreams']:
        print("No log streams found")
        exit(1)
    
    print(f"Found {len(response['logStreams'])} recent log streams")
    print()
    
    # Get logs from the most recent stream
    latest_stream = response['logStreams'][0]
    stream_name = latest_stream['logStreamName']
    
    print(f"Reading from stream: {stream_name}")
    print(f"Last event: {datetime.fromtimestamp(latest_stream['lastEventTimestamp']/1000)}")
    print()
    print("=" * 80)
    print()
    
    # Get log events
    log_response = logs_client.get_log_events(
        logGroupName=LOG_GROUP,
        logStreamName=stream_name,
        startFromHead=False,  # Get most recent
        limit=100
    )
    
    events = log_response['events']
    
    if not events:
        print("No log events found")
        exit(1)
    
    print(f"Showing last {len(events)} log events:")
    print()
    
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp']/1000)
        message = event['message'].strip()
        
        # Highlight important messages
        if any(keyword in message for keyword in ['ERROR', 'HANDLER', 'FILTER', 'Regional info', 'allowed_regions']):
            print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
        else:
            # Print other messages in gray (if terminal supports it)
            print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
    
    print()
    print("=" * 80)
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
