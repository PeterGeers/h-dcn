import boto3
from datetime import datetime, timedelta

# Initialize CloudWatch Logs client
logs_client = boto3.client('logs', region_name='eu-west-1')

# Lambda function name
function_name = 'webshop-backend-dev-GetMembersFilteredFunction-dSATIeNyPrh6'
log_group_name = f'/aws/lambda/{function_name}'

# Get logs from the last 10 minutes
start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)
end_time = int(datetime.now().timestamp() * 1000)

print(f"🔍 Checking logs for: {function_name}")
print(f"📅 Time range: Last 10 minutes")
print("=" * 80)

try:
    # Get log streams (most recent first)
    streams_response = logs_client.describe_log_streams(
        logGroupName=log_group_name,
        orderBy='LastEventTime',
        descending=True,
        limit=5
    )
    
    if not streams_response['logStreams']:
        print("❌ No log streams found")
        exit(1)
    
    # Get events from the most recent stream
    latest_stream = streams_response['logStreams'][0]
    stream_name = latest_stream['logStreamName']
    
    print(f"📋 Latest log stream: {stream_name}")
    print(f"🕐 Last event: {datetime.fromtimestamp(latest_stream['lastEventTimestamp']/1000)}")
    print("=" * 80)
    
    # Get log events
    events_response = logs_client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=stream_name,
        startTime=start_time,
        endTime=end_time,
        startFromHead=False,  # Get most recent first
        limit=100
    )
    
    events = events_response['events']
    
    if not events:
        print("❌ No log events found in the time range")
        exit(1)
    
    print(f"\n📝 Found {len(events)} log events:\n")
    
    # Print events in chronological order
    for event in reversed(events):
        timestamp = datetime.fromtimestamp(event['timestamp']/1000).strftime('%H:%M:%S')
        message = event['message'].strip()
        
        # Highlight important messages
        if '[AUTH_DEBUG]' in message or '[HANDLER]' in message or '[FILTER]' in message:
            print(f"🔍 {timestamp} | {message}")
        elif 'ERROR' in message or 'Error' in message:
            print(f"❌ {timestamp} | {message}")
        elif 'regional_info' in message.lower() or 'allowed_regions' in message.lower():
            print(f"🎯 {timestamp} | {message}")
        else:
            print(f"   {timestamp} | {message}")
    
    print("\n" + "=" * 80)
    print("✅ Log check complete")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
