# Script to add Runtime and Handler properties to all ZIP-based functions
# This implements Step 2 from the Container Function Analysis

Write-Host "🔧 Adding Runtime and Handler to all ZIP-based functions..."

$templatePath = "template.yaml"
$content = Get-Content $templatePath -Raw

# List of functions that need Runtime and Handler (all except GenerateMemberParquetFunction)
$zipFunctions = @(
    "InsertProductFunction",
    "DeleteProductFunction", 
    "GetProductByIdFunction",
    "scanProductFunction",
    "UpdateProductFunction",
    "CreateMemberFunction",
    "GetMembersFunction",
    "GetMemberByIdFunction",
    "UpdateMemberFunction",
    "DeleteMemberFunction",
    "CreatePaymentFunction",
    "GetPaymentsFunction",
    "GetPaymentByIdFunction",
    "UpdatePaymentFunction",
    "DeletePaymentFunction",
    "GetMemberPaymentsFunction",
    "CreateEventFunction",
    "GetEventsFunction",
    "HdcnCognitoAdminFunction",
    "GetMembershipsFunction",
    "CreateMembershipFunction",
    "GetMembershipByIdFunction",
    "UpdateMembershipFunction",
    "DeleteMembershipFunction",
    "CreateCartFunction",
    "GetCartFunction",
    "ClearCartFunction",
    "CreateOrderFunction",
    "GetOrdersFunction",
    "GetOrderByIdFunction",
    "UpdateOrderStatusFunction",
    "GetCustomerOrdersFunction",
    "GetEventByIdFunction",
    "UpdateEventFunction",
    "DeleteEventFunction",
    "UpdateCartItemsFunction",
    "S3FileManagerFunction"
)

foreach ($functionName in $zipFunctions) {
    Write-Host "  Adding Runtime/Handler to $functionName"
    
    # Pattern to match the function and add Runtime/Handler after CodeUri
    $pattern = "($functionName):\s*\n(\s*)Type: AWS::Serverless::Function\s*\n(\s*)Properties:\s*\n(\s*)CodeUri: ([^\n]+)"
    $replacement = "`$1:`n`$2Type: AWS::Serverless::Function`n`$3Properties:`n`$4CodeUri: `$5`n`$4Handler: app.lambda_handler`n`$4Runtime: python3.11"
    
    $content = $content -replace $pattern, $replacement
}

# Save the updated content
$content | Set-Content $templatePath -NoNewline

Write-Host "✅ Runtime and Handler properties added to all ZIP functions"
Write-Host "📝 Please review the changes and test deployment"