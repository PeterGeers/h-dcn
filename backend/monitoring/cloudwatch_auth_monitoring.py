"""
CloudWatch Authentication Monitoring Setup
Creates comprehensive monitoring for H-DCN authentication system failures
"""

import boto3
import json
from datetime import datetime, timedelta


class AuthMonitoringSetup:
    """
    Sets up CloudWatch monitoring for authentication failures
    """
    
    def __init__(self, region='eu-west-1'):
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.logs = boto3.client('logs', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.region = region
        
    def create_log_groups(self):
        """
        Create dedicated log groups for authentication monitoring
        """
        log_groups = [
            {
                'name': '/aws/lambda/auth-failures',
                'description': 'Authentication failure events',
                'retention_days': 30
            },
            {
                'name': '/aws/lambda/auth-security-events',
                'description': 'Security-related authentication events',
                'retention_days': 90
            },
            {
                'name': '/aws/lambda/auth-performance',
                'description': 'Authentication performance metrics',
                'retention_days': 14
            }
        ]
        
        for log_group in log_groups:
            try:
                self.logs.create_log_group(
                    logGroupName=log_group['name']
                )
                print(f"✅ Created log group: {log_group['name']}")
                
                # Set retention policy
                self.logs.put_retention_policy(
                    logGroupName=log_group['name'],
                    retentionInDays=log_group['retention_days']
                )
                print(f"✅ Set retention policy: {log_group['retention_days']} days")
                
            except self.logs.exceptions.ResourceAlreadyExistsException:
                print(f"ℹ️ Log group already exists: {log_group['name']}")
            except Exception as e:
                print(f"❌ Error creating log group {log_group['name']}: {str(e)}")
    
    def create_sns_topic(self):
        """
        Create SNS topic for authentication alerts
        """
        try:
            response = self.sns.create_topic(
                Name='hdcn-auth-alerts',
                Attributes={
                    'DisplayName': 'H-DCN Authentication Alerts',
                    'DeliveryPolicy': json.dumps({
                        'http': {
                            'defaultHealthyRetryPolicy': {
                                'minDelayTarget': 20,
                                'maxDelayTarget': 20,
                                'numRetries': 3,
                                'numMaxDelayRetries': 0,
                                'numMinDelayRetries': 0,
                                'numNoDelayRetries': 0,
                                'backoffFunction': 'linear'
                            }
                        }
                    })
                }
            )
            
            topic_arn = response['TopicArn']
            print(f"✅ Created SNS topic: {topic_arn}")
            
            # Subscribe webmaster email
            self.sns.subscribe(
                TopicArn=topic_arn,
                Protocol='email',
                Endpoint='webmaster@h-dcn.nl'
            )
            print("✅ Subscribed webmaster@h-dcn.nl to alerts")
            
            return topic_arn
            
        except Exception as e:
            print(f"❌ Error creating SNS topic: {str(e)}")
            return None
    
    def create_metric_filters(self):
        """
        Create CloudWatch metric filters for authentication events
        """
        filters = [
            {
                'name': 'AuthFailureCount',
                'pattern': '[timestamp, request_id, level="ERROR", message="AUTH_SYSTEM_FAILURE" || message="PERMISSION_DENIED" || message="INVALID_TOKEN"]',
                'log_group': '/aws/lambda/auth-failures',
                'metric_name': 'AuthenticationFailures',
                'metric_namespace': 'HDCN/Authentication',
                'metric_value': '1',
                'description': 'Count of authentication failures'
            },
            {
                'name': 'SecurityEventCount',
                'pattern': '[timestamp, request_id, level, event_type="SECURITY_AUDIT" || event_type="PERMISSION_DENIED" || event_type="SUSPICIOUS_ACTIVITY"]',
                'log_group': '/aws/lambda/auth-security-events',
                'metric_name': 'SecurityEvents',
                'metric_namespace': 'HDCN/Security',
                'metric_value': '1',
                'description': 'Count of security-related events'
            },
            {
                'name': 'AuthLatency',
                'pattern': '[timestamp, request_id, level, message="AUTH_PERFORMANCE", duration]',
                'log_group': '/aws/lambda/auth-performance',
                'metric_name': 'AuthenticationLatency',
                'metric_namespace': 'HDCN/Performance',
                'metric_value': '$duration',
                'description': 'Authentication processing time in milliseconds'
            },
            {
                'name': 'MaintenanceModeActivations',
                'pattern': '[timestamp, request_id, level, message="MAINTENANCE_MODE"]',
                'log_group': '/aws/lambda/auth-failures',
                'metric_name': 'MaintenanceModeActivations',
                'metric_namespace': 'HDCN/System',
                'metric_value': '1',
                'description': 'Count of maintenance mode activations'
            }
        ]
        
        for filter_config in filters:
            try:
                self.logs.put_metric_filter(
                    logGroupName=filter_config['log_group'],
                    filterName=filter_config['name'],
                    filterPattern=filter_config['pattern'],
                    metricTransformations=[
                        {
                            'metricName': filter_config['metric_name'],
                            'metricNamespace': filter_config['metric_namespace'],
                            'metricValue': filter_config['metric_value'],
                            'defaultValue': 0
                        }
                    ]
                )
                print(f"✅ Created metric filter: {filter_config['name']}")
                
            except Exception as e:
                print(f"❌ Error creating metric filter {filter_config['name']}: {str(e)}")
    
    def create_alarms(self, sns_topic_arn):
        """
        Create CloudWatch alarms for authentication monitoring
        """
        if not sns_topic_arn:
            print("❌ No SNS topic ARN provided, skipping alarm creation")
            return
            
        alarms = [
            {
                'name': 'HDCN-Auth-High-Failure-Rate',
                'description': 'High authentication failure rate detected',
                'metric_name': 'AuthenticationFailures',
                'namespace': 'HDCN/Authentication',
                'statistic': 'Sum',
                'period': 300,  # 5 minutes
                'evaluation_periods': 2,
                'threshold': 10,  # More than 10 failures in 10 minutes
                'comparison_operator': 'GreaterThanThreshold',
                'treat_missing_data': 'notBreaching'
            },
            {
                'name': 'HDCN-Auth-Critical-Failure-Rate',
                'description': 'Critical authentication failure rate - immediate attention required',
                'metric_name': 'AuthenticationFailures',
                'namespace': 'HDCN/Authentication',
                'statistic': 'Sum',
                'period': 60,  # 1 minute
                'evaluation_periods': 1,
                'threshold': 25,  # More than 25 failures in 1 minute
                'comparison_operator': 'GreaterThanThreshold',
                'treat_missing_data': 'notBreaching'
            },
            {
                'name': 'HDCN-Auth-Maintenance-Mode',
                'description': 'Authentication system in maintenance mode',
                'metric_name': 'MaintenanceModeActivations',
                'namespace': 'HDCN/System',
                'statistic': 'Sum',
                'period': 60,  # 1 minute
                'evaluation_periods': 1,
                'threshold': 1,  # Any maintenance mode activation
                'comparison_operator': 'GreaterThanOrEqualToThreshold',
                'treat_missing_data': 'notBreaching'
            },
            {
                'name': 'HDCN-Auth-High-Latency',
                'description': 'Authentication system experiencing high latency',
                'metric_name': 'AuthenticationLatency',
                'namespace': 'HDCN/Performance',
                'statistic': 'Average',
                'period': 300,  # 5 minutes
                'evaluation_periods': 2,
                'threshold': 3000,  # More than 3 seconds average
                'comparison_operator': 'GreaterThanThreshold',
                'treat_missing_data': 'notBreaching'
            },
            {
                'name': 'HDCN-Security-Events',
                'description': 'Unusual security events detected',
                'metric_name': 'SecurityEvents',
                'namespace': 'HDCN/Security',
                'statistic': 'Sum',
                'period': 300,  # 5 minutes
                'evaluation_periods': 1,
                'threshold': 5,  # More than 5 security events in 5 minutes
                'comparison_operator': 'GreaterThanThreshold',
                'treat_missing_data': 'notBreaching'
            }
        ]
        
        for alarm in alarms:
            try:
                self.cloudwatch.put_metric_alarm(
                    AlarmName=alarm['name'],
                    AlarmDescription=alarm['description'],
                    ActionsEnabled=True,
                    AlarmActions=[sns_topic_arn],
                    MetricName=alarm['metric_name'],
                    Namespace=alarm['namespace'],
                    Statistic=alarm['statistic'],
                    Period=alarm['period'],
                    EvaluationPeriods=alarm['evaluation_periods'],
                    Threshold=alarm['threshold'],
                    ComparisonOperator=alarm['comparison_operator'],
                    TreatMissingData=alarm['treat_missing_data']
                )
                print(f"✅ Created alarm: {alarm['name']}")
                
            except Exception as e:
                print(f"❌ Error creating alarm {alarm['name']}: {str(e)}")
    
    def create_dashboard(self):
        """
        Create CloudWatch dashboard for authentication monitoring
        """
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["HDCN/Authentication", "AuthenticationFailures"],
                            ["HDCN/System", "MaintenanceModeActivations"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Authentication Failures & Maintenance Mode",
                        "yAxis": {
                            "left": {
                                "min": 0
                            }
                        }
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["HDCN/Performance", "AuthenticationLatency"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Authentication Latency (ms)",
                        "yAxis": {
                            "left": {
                                "min": 0
                            }
                        }
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["HDCN/Security", "SecurityEvents"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Security Events",
                        "yAxis": {
                            "left": {
                                "min": 0
                            }
                        }
                    }
                },
                {
                    "type": "log",
                    "x": 12,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "query": "SOURCE '/aws/lambda/auth-failures'\n| fields @timestamp, @message\n| filter @message like /AUTH_SYSTEM_FAILURE/\n| sort @timestamp desc\n| limit 20",
                        "region": self.region,
                        "title": "Recent Authentication Failures",
                        "view": "table"
                    }
                },
                {
                    "type": "log",
                    "x": 0,
                    "y": 12,
                    "width": 24,
                    "height": 6,
                    "properties": {
                        "query": "SOURCE '/aws/lambda/auth-security-events'\n| fields @timestamp, user_email, event_type, severity, @message\n| filter event_type = \"PERMISSION_DENIED\" or event_type = \"SECURITY_AUDIT\"\n| sort @timestamp desc\n| limit 50",
                        "region": self.region,
                        "title": "Security Events Log",
                        "view": "table"
                    }
                }
            ]
        }
        
        try:
            self.cloudwatch.put_dashboard(
                DashboardName='HDCN-Authentication-Monitoring',
                DashboardBody=json.dumps(dashboard_body)
            )
            print("✅ Created CloudWatch dashboard: HDCN-Authentication-Monitoring")
            
        except Exception as e:
            print(f"❌ Error creating dashboard: {str(e)}")
    
    def setup_complete_monitoring(self):
        """
        Set up complete authentication monitoring system
        """
        print("🚀 Setting up H-DCN Authentication Monitoring...")
        print("=" * 60)
        
        # Step 1: Create log groups
        print("\n📋 Step 1: Creating log groups...")
        self.create_log_groups()
        
        # Step 2: Create SNS topic for alerts
        print("\n📧 Step 2: Creating SNS topic for alerts...")
        sns_topic_arn = self.create_sns_topic()
        
        # Step 3: Create metric filters
        print("\n📊 Step 3: Creating metric filters...")
        self.create_metric_filters()
        
        # Step 4: Create alarms
        print("\n🚨 Step 4: Creating CloudWatch alarms...")
        self.create_alarms(sns_topic_arn)
        
        # Step 5: Create dashboard
        print("\n📈 Step 5: Creating monitoring dashboard...")
        self.create_dashboard()
        
        print("\n" + "=" * 60)
        print("✅ H-DCN Authentication Monitoring Setup Complete!")
        print("\n📋 What was created:")
        print("   • Log groups for auth failures, security events, and performance")
        print("   • SNS topic with email subscription to webmaster@h-dcn.nl")
        print("   • Metric filters for automated monitoring")
        print("   • CloudWatch alarms for failure detection")
        print("   • Monitoring dashboard: HDCN-Authentication-Monitoring")
        print("\n🔍 Access your dashboard:")
        print(f"   https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name=HDCN-Authentication-Monitoring")
        print("\n📧 Alert notifications will be sent to: webmaster@h-dcn.nl")


def main():
    """
    Main function to set up authentication monitoring
    """
    monitoring = AuthMonitoringSetup()
    monitoring.setup_complete_monitoring()


if __name__ == "__main__":
    main()