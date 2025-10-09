# Cognito Bulk Operations via AWS CLI
$USER_POOL_ID = "eu-west-1_VtKQHhXGN"

# Create multiple users
function Create-CognitoUsers {
    param([string]$CsvPath)
    
    $users = Import-Csv $CsvPath
    
    foreach ($user in $users) {
        Write-Host "Creating user: $($user.username)"
        
        # Create user
        aws cognito-idp admin-create-user `
            --user-pool-id $USER_POOL_ID `
            --username $user.username `
            --user-attributes Name=email,Value=$user.email Name=email_verified,Value=true Name=given_name,Value=$user.given_name Name=family_name,Value=$user.family_name `
            --temporary-password "WelkomHDCN2024!" `
            --message-action SUPPRESS
        
        # Add to groups
        if ($user.groups) {
            $groups = $user.groups -split ";"
            foreach ($group in $groups) {
                aws cognito-idp admin-add-user-to-group `
                    --user-pool-id $USER_POOL_ID `
                    --username $user.username `
                    --group-name $group.Trim()
            }
        }
    }
}

# Bulk assign groups
function Assign-CognitoGroups {
    param([string]$Username, [string]$Groups)
    
    $groupList = $Groups -split ";"
    foreach ($group in $groupList) {
        aws cognito-idp admin-add-user-to-group `
            --user-pool-id $USER_POOL_ID `
            --username $Username `
            --group-name $group.Trim()
    }
}

# Example usage:
# Create-CognitoUsers -CsvPath "cognito-users.csv"
# Assign-CognitoGroups -Username "user@hdcn.nl" -Groups "hdcnLeden;hdcnRegio_NoordHolland"