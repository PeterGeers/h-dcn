# Infrastructure State Checker
# Run this before making any infrastructure changes

param(
    [string]$StackName = "webshop-backend",
    [string]$Region = "eu-west-1"
)

Write-Host "🔍 Checking Infrastructure State for Stack: $StackName" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Cyan
Write-Host ""

# Check if stack exists
Write-Host "📋 Stack Status:" -ForegroundColor Yellow
try {
    $stackStatus = aws cloudformation describe-stacks --stack-name $StackName --region $Region --query 'Stacks[0].StackStatus' --output text
    Write-Host "✅ Stack exists with status: $stackStatus" -ForegroundColor Green
}
catch {
    Write-Host "❌ Stack does not exist or is not accessible" -ForegroundColor Red
    exit 1
}

# Check Lambda functions
Write-Host ""
Write-Host "🔧 Lambda Functions:" -ForegroundColor Yellow
aws cloudformation describe-stack-resources --stack-name $StackName --region $Region --query 'StackResources[?ResourceType==`AWS::Lambda::Function`].{Name:LogicalResourceId,Status:ResourceStatus}' --output table

# Check API Gateway resources
Write-Host ""
Write-Host "🌐 API Gateway Resources:" -ForegroundColor Yellow
aws cloudformation describe-stack-resources --stack-name $StackName --region $Region --query 'StackResources[?ResourceType==`AWS::ApiGateway::Resource`].{Name:LogicalResourceId,Status:ResourceStatus}' --output table

# Check for Analytics/Parquet related resources
Write-Host ""
Write-Host "📊 Analytics/Parquet Resources:" -ForegroundColor Yellow
aws cloudformation describe-stack-resources --stack-name $StackName --region $Region --query 'StackResources[?contains(LogicalResourceId, `Analytics`) || contains(LogicalResourceId, `Parquet`)].{LogicalId:LogicalResourceId,Type:ResourceType,Status:ResourceStatus}' --output table

# Check ECR repositories
Write-Host ""
Write-Host "🐳 ECR Repositories:" -ForegroundColor Yellow
try {
    aws ecr describe-repositories --region $Region --query 'repositories[?contains(repositoryName, `parquet`) || contains(repositoryName, `hdcn`)].{Name:repositoryName,URI:repositoryUri}' --output table
}
catch {
    Write-Host "No ECR repositories found or access denied" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Infrastructure check complete!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Next steps:" -ForegroundColor Cyan
Write-Host "1. Review the current state above"
Write-Host "2. Check INFRASTRUCTURE.md for guidelines"
Write-Host "3. Make changes incrementally"
Write-Host "4. Test after each change"