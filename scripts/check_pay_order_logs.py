"""Check CloudWatch logs for PayOrderFunction."""
import boto3
import time

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
logs = session.client('logs')

log_group = '/aws/lambda/h-dcn-PayOrderFunction-mfmERxxWZgwu'

end_time = int(time.time() * 1000)
start_time = end_time - (10 * 60 * 1000)

try:
    resp = logs.filter_log_events(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        limit=50,
    )
    
    print(f"Log events: {len(resp['events'])}")
    for event in resp['events']:
        msg = event['message'].strip()
        if msg and not msg.startswith('XRAY') and 'DEBUG' not in msg:
            print(msg)
except Exception as e:
    print(f"Error: {e}")
