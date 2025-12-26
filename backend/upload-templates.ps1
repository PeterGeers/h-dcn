# Upload Email Templates to S3
# This script uploads the initial email templates and configuration to S3

param(
    [string]$BucketName = "",
    [string]$Region = "eu-west-1"
)

# Get bucket name from SAM stack if not provided
if ([string]::IsNullOrEmpty($BucketName)) {
    Write-Host "🔍 Getting bucket name from SAM stack..." -ForegroundColor Yellow
    $stackName = "sam-app"  # Default SAM stack name
    try {
        $BucketName = aws cloudformation describe-stacks --stack-name $stackName --region $Region --query "Stacks[0].Outputs[?OutputKey=='EmailTemplatesBucket'].OutputValue" --output text
        if ([string]::IsNullOrEmpty($BucketName)) {
            Write-Host "❌ Could not find EmailTemplatesBucket in stack outputs. Please provide bucket name manually." -ForegroundColor Red
            Write-Host "Usage: .\upload-templates.ps1 -BucketName 'your-bucket-name'" -ForegroundColor Yellow
            exit 1
        }
    } catch {
        Write-Host "❌ Error getting bucket name from stack: $_" -ForegroundColor Red
        Write-Host "Usage: .\upload-templates.ps1 -BucketName 'your-bucket-name'" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "📧 Uploading email templates to S3 bucket: $BucketName" -ForegroundColor Green

# Check if bucket exists
Write-Host "🔍 Checking if bucket exists..." -ForegroundColor Yellow
try {
    aws s3api head-bucket --bucket $BucketName --region $Region
    Write-Host "✅ Bucket exists!" -ForegroundColor Green
} catch {
    Write-Host "❌ Bucket $BucketName does not exist or is not accessible." -ForegroundColor Red
    exit 1
}

# Upload configuration
Write-Host "📝 Uploading configuration..." -ForegroundColor Yellow
aws s3 cp email-templates/config/variables.json s3://$BucketName/config/variables.json --region $Region
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Configuration uploaded successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to upload configuration!" -ForegroundColor Red
    exit 1
}

# Upload templates
Write-Host "📧 Uploading email templates..." -ForegroundColor Yellow
$templates = @(
    "welcome-user.html",
    "resend-code.html", 
    "passwordless-recovery.html"
)

foreach ($template in $templates) {
    Write-Host "  📄 Uploading $template..." -ForegroundColor Cyan
    aws s3 cp "email-templates/templates/$template" "s3://$BucketName/templates/$template" --region $Region --content-type "text/html"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ $template uploaded!" -ForegroundColor Green
    } else {
        Write-Host "    ❌ Failed to upload $template!" -ForegroundColor Red
        exit 1
    }
}

# Verify uploads
Write-Host "🔍 Verifying uploads..." -ForegroundColor Yellow
aws s3 ls s3://$BucketName/config/ --region $Region
aws s3 ls s3://$BucketName/templates/ --region $Region

Write-Host "🎉 All email templates uploaded successfully!" -ForegroundColor Green
Write-Host "📧 Templates are now ready for use by the Lambda function." -ForegroundColor Cyan
Write-Host "🔧 You can now edit templates through the admin interface or directly in S3." -ForegroundColor Cyan