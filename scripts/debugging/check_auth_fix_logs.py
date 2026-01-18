"""
Check CloudWatch logs for GetMembersFilteredFunction to verify auth fix is working
"""
import boto3
import json
from datetime import datetime, timedelta

# Initialize CloudWatch Logs client
logs_client = boto3.client('logs', region_name='eu-west-1')

# Log group name for GetMembersFilteredFunction
log_group_name = '/aws/lambda/hdcn-backend-dev-GetMembersFilteredFunction'

# Get logs from the last 5 minutes
start_time = int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
end_time = int(datetime.now().timestamp() * 1000)

print(f"🔍 Checking logs for GetMembersFilteredFunction")
print(f"📅 Time range: Last 5 minutes")
print(f"=" * 80)

try:
    # Query logs for auth-related messages
    response = logs_client.filter_log_events(
        logGroupName=log_group_name,
        startTime=start_time,
        endTime=end_time,
        limit=100
    )
    
    if not response.get('events'):
        print("⚠️  No recent logs found. Please trigger a request first.")
        print("\n💡 To trigger a request:")
        print("   1. Go to https://de1irtdutlxqu.cloudfront.net/members")
        print("   2. Login as peter@pgeers.nl")
        print("   3. Wait for the page to load")
        print("   4. Run this script again")
    else:
        print(f"📊 Found {len(response['events'])} log events\n")
        
        # Look for auth-related logs
        auth_logs = []
        for event in response['events']:
            message = event['message']
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%H:%M:%S')
            
            # Filter for important auth messages
            if any(keyword in message for keyword in [
                'AUTH_DEBUG',
                'allowed_regions',
                'regional_info',
                'access_type',
                'Regio_Utrecht',
                'User has regional roles'
            ]):
                auth_logs.append((timestamp, message))
        
        if auth_logs:
            print("🔍 Auth-related log messages:")
            print("=" * 80)
            for timestamp, message in auth_logs:
                print(f"[{timestamp}] {message.strip()}")
            print("=" * 80)
            
            # Check if fix is working
            has_regional_roles_log = any('User has regional roles' in msg for _, msg in auth_logs)
            has_utrecht_region = any('Utrecht' in msg for _, msg in auth_logs)
            has_empty_regions = any("'allowed_regions': []" in msg for _, msg in auth_logs)
            
            print("\n📊 Analysis:")
            print(f"   {'✅' if has_regional_roles_log else '❌'} Found 'User has regional roles' log")
            print(f"   {'✅' if has_utrecht_region else '❌'} Found Utrecht region in logs")
            print(f"   {'❌' if has_empty_regions else '✅'} Empty allowed_regions: {has_empty_regions}")
            
            if has_regional_roles_log and has_utrecht_region and not has_empty_regions:
                print("\n✅ FIX IS WORKING! Regional roles are being detected correctly.")
            elif has_empty_regions:
                print("\n❌ FIX NOT WORKING YET. Still seeing empty allowed_regions.")
                print("   This might be due to Lambda cold start or layer caching.")
                print("   Try refreshing the page a few times to force a new Lambda execution.")
            else:
                print("\n⚠️  Inconclusive. Need more log data.")
        else:
            print("⚠️  No auth-related logs found in recent events.")
            print("   The Lambda might not have been invoked yet.")
            
except Exception as e:
    print(f"❌ Error reading logs: {str(e)}")
    import traceback
    traceback.print_exc()
