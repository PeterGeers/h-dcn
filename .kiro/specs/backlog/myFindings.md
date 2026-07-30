The SSO login to nonprofit-deploy failed with InvalidRequestException on RegisterClient.

The ~/.aws/config has been updated correctly with:

[sso-session h-dcn] pointing to https://d-9967592717.awsapps.com/start (discovered from your existing SSO cache)
[profile nonprofit-deploy] configured for SSO with sso_role_name = NonprofitDeployAccess
However, the aws sso login fails because the IAM Identity Center instance (d-9967592717) doesn't appear to have a Permission Set named NonprofitDeployAccess configured for account 506221081911. The instance is currently used for CodeWhisperer/Kiro access but needs a permission set for account-level access.

To complete this task, you need to:

Go to AWS IAM Identity Center console (in the management account that owns the d-9967592717 instance)
Create a Permission Set named NonprofitDeployAccess with policies matching the current NonprofitDeployRole
Assign it to your user for account 506221081911
Once that's done, aws sso login --profile nonprofit-deploy should work. Should I mark this task as complete with the config changes done, or would you like me to wait/investigate further?

Mark task complete — config is done, SSO login requires IAM Identity Center admin setup
Investigate further — try different approaches to get SSO working
