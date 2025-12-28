# Upload Debug Logs and Test Results to S3
# This script uploads log files and test results for debugging

param(
    [string]$BucketName = "",
    [string]$Region = "eu-west-1",
    [string]$LogPath = "",
    [string]$LogType = "debug"
)

# Get bucket name from SAM stack if not provided
if ([string]::IsNullOrEmpty($BucketName)) {
    Write-Host "🔍 Getting bucket name from SAM stack..." -ForegroundColor Yellow
    $stackName = "sam-app"
    try {
        $BucketName = aws cloudformation describe-stacks --stack-name $stackName --region $Region --query "Stacks[0].Outputs[?OutputKey=='EmailTemplatesBucket'].OutputValue" --output text
        if ([string]::IsNullOrEmpty($BucketName)) {
            Write-Host "❌ Could not find bucket in stack outputs. Please provide bucket name manually." -ForegroundColor Red
            Write-Host "Usage: .\upload-logs.ps1 -BucketName 'your-bucket-name' -LogPath 'path/to/log.json'" -ForegroundColor Yellow
            exit 1
        }
    }
    catch {
        Write-Host "❌ Error getting bucket name from stack: $_" -ForegroundColor Red
        exit 1
    }
}

if ([string]::IsNullOrEmpty($LogPath)) {
    Write-Host "❌ LogPath parameter is required" -ForegroundColor Red
    Write-Host "Usage: .\upload-logs.ps1 -LogPath 'path/to/log.json'" -ForegroundColor Yellow
    exit 1
}

if (!(Test-Path $LogPath)) {
    Write-Host "❌ Log file not found: $LogPath" -ForegroundColor Red
    exit 1
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$fileName = [System.IO.Path]::GetFileName($LogPath)
$s3Key = "logs/$LogType/$timestamp-$fileName"

Write-Host "📤 Uploading log file to S3..." -ForegroundColor Green
Write-Host "  📁 Source: $LogPath" -ForegroundColor Cyan
Write-Host "  🪣 Bucket: $BucketName" -ForegroundColor Cyan
Write-Host "  🔑 Key: $s3Key" -ForegroundColor Cyan

try {
    aws s3 cp $LogPath "s3://$BucketName/$s3Key" --region $Region --content-type "application/json"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Log uploaded successfully!" -ForegroundColor Green
        Write-Host "🔗 S3 URL: s3://$BucketName/$s3Key" -ForegroundColor Cyan
        
        # Generate presigned URL for easy access
        Write-Host "🔗 Generating presigned URL..." -ForegroundColor Yellow
        $presignedUrl = aws s3 presign "s3://$BucketName/$s3Key" --expires-in 3600 --region $Region
        Write-Host "🌐 Presigned URL (valid for 1 hour):" -ForegroundColor Green
        Write-Host $presignedUrl -ForegroundColor White
    }
    else {
        Write-Host "❌ Failed to upload log file!" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "❌ Error uploading log: $_" -ForegroundColor Red
    exit 1
}