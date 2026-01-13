#!/usr/bin/env python3
"""
Check CloudFormation stacks for GetMemberSelfFunction
"""

import boto3
import json

def check_cloudformation_stacks():
    """Check all CloudFormation stacks for GetMemberSelfFunction"""
    
    print("=" * 60)
    print("Checking CloudFormation stacks for GetMemberSelfFunction")
    print("=" * 60)
    
    try:
        cf_client = boto3.client('cloudformation', region_name='eu-west-1')
        
        # List all stacks
        stacks_response = cf_client.list_stacks(
            StackStatusFilter=[
                'CREATE_COMPLETE',
                'UPDATE_COMPLETE',
                'UPDATE_ROLLBACK_COMPLETE'
            ]
        )
        
        stacks = stacks_response.get('StackSummaries', [])
        
        print(f"✅ Found {len(stacks)} active CloudFormation stacks")
        
        member_self_found = False
        
        for stack in stacks:
            stack_name = stack['StackName']
            stack_status = stack['StackStatus']
            
            # Check stacks that might contain our function
            if any(keyword in stack_name.lower() for keyword in ['backend', 'webshop', 'hdcn', 'member']):
                print(f"\n📦 Stack: {stack_name} ({stack_status})")
                
                try:
                    # Get stack resources
                    resources_response = cf_client.list_stack_resources(StackName=stack_name)
                    resources = resources_response.get('StackResourceSummaries', [])
                    
                    # Look for GetMemberSelfFunction
                    for resource in resources:
                        resource_type = resource['ResourceType']
                        logical_id = resource['LogicalResourceId']
                        physical_id = resource.get('PhysicalResourceId', 'N/A')
                        
                        if 'memberself' in logical_id.lower() or 'member_self' in logical_id.lower():
                            member_self_found = True
                            print(f"   🎯 FOUND: {logical_id}")
                            print(f"      Type: {resource_type}")
                            print(f"      Physical ID: {physical_id}")
                            
                            # If it's a Lambda function, check its logs
                            if resource_type == 'AWS::Lambda::Function':
                                print(f"      📝 Checking logs for: {physical_id}")
                                check_function_logs_direct(physical_id)
                        
                        elif 'lambda' in resource_type.lower() and 'member' in logical_id.lower():
                            print(f"   📋 Member-related Lambda: {logical_id} -> {physical_id}")
                    
                    # Also check for API Gateway resources
                    api_resources = [r for r in resources if 'Api' in r['ResourceType']]
                    if api_resources:
                        print(f"   🌐 API Gateway resources:")
                        for api_resource in api_resources:
                            print(f"      {api_resource['LogicalResourceId']} -> {api_resource.get('PhysicalResourceId', 'N/A')}")
                
                except Exception as e:
                    print(f"   ❌ Error checking stack resources: {str(e)}")
        
        if not member_self_found:
            print(f"\n❌ GetMemberSelfFunction not found in any CloudFormation stack!")
            print(f"🔍 This suggests it might not be deployed yet.")
        
        # Also check if there are any stacks with 'sam' in the name (SAM deployments)
        print(f"\n🔍 Checking for SAM-deployed stacks:")
        sam_stacks = [s for s in stacks if 'sam' in s['StackName'].lower()]
        
        for stack in sam_stacks:
            print(f"   📦 SAM Stack: {stack['StackName']}")
    
    except Exception as e:
        print(f"❌ Error checking CloudFormation stacks: {str(e)}")

def check_function_logs_direct(function_name):
    """Check logs for a function directly"""
    
    try:
        logs_client = boto3.client('logs', region_name='eu-west-1')
        log_group_name = f"/aws/lambda/{function_name}"
        
        from datetime import datetime, timedelta
        
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=30)
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)
        
        # Get recent log events
        events_response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time_ms,
            endTime=end_time_ms,
            limit=10
        )
        
        events = events_response.get('events', [])
        
        if events:
            print(f"      📊 Found {len(events)} recent log events:")
            for event in events[-3:]:  # Show last 3
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                print(f"      ⏰ {timestamp.strftime('%H:%M:%S')} - {message[:100]}...")
                
                # Highlight errors
                if any(keyword in message.lower() for keyword in ['error', 'exception', 'traceback', 'failed', '500']):
                    print("      🚨 ERROR DETECTED!")
        else:
            print(f"      ❌ No recent log events")
            
    except Exception as e:
        print(f"      ❌ Error checking logs: {str(e)}")

if __name__ == "__main__":
    check_cloudformation_stacks()