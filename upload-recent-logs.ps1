# Upload Recent Test Results and Logs
# This script finds and uploads the most recent test results and log files

param(
    [string]$BucketName = "",
    [string]$Region = "eu-west-1",
    [int]$DaysBack = 7
)

# Get bucket name from SAM stack if not provided
if ([string]::IsNullOrEmpty($BucketName)) {
    Write-Host "🔍 Getting bucket name from SAM stack..." -ForegroundColor Yellow
    $stackName = "sam-app"
    try {
        $BucketName = aws cloudformation describe-stacks --stack-name $stackName --region $Region --query "Stacks[0].Outputs[?OutputKey=='EmailTemplatesBucket'].OutputValue" --output text
        if ([string]::IsNullOrEmpty($BucketName)) {
            Write-Host "❌ Could not find bucket in stack outputs. Please provide bucket name manually." -ForegroundColor Red
            Write-Host "Usage: .\upload-recent-logs.ps1 -BucketName 'your-bucket-name'" -ForegroundColor Yellow
            exit 1
        }
    }
    catch {
        Write-Host "❌ Error getting bucket name from stack: $_" -ForegroundColor Red
        exit 1
    }
}

$cutoffDate = (Get-Date).AddDays(-$DaysBack)
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host "📤 Uploading recent logs and test results..." -ForegroundColor Green
Write-Host "  📅 Looking for files newer than: $($cutoffDate.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan

# Find recent log files
$logPatterns = @(
    "*.json",
    "*.log", 
    "*.txt"
)

$uploadedFiles = @()

foreach ($pattern in $logPatterns) {
    $files = Get-ChildItem -Path . -Filter $pattern -Recurse | Where-Object { 
        $_.LastWriteTime -gt $cutoffDate -and 
        $_.Name -match "(test|result|log|report)" 
    }
    
    foreach ($file in $files) {
        $relativePath = $file.FullName.Replace((Get-Location).Path, "").TrimStart('\', '/')
        $s3Key = "logs/batch-$timestamp/$relativePath"
        
        Write-Host "  📄 Uploading: $relativePath" -ForegroundColor Cyan
        
        try {
            $contentType = switch ($file.Extension.ToLower()) {
                ".json" { "application/json" }
                ".log" { "text/plain" }
                ".txt" { "text/plain" }
                default { "application/octet-stream" }
            }
            
            aws s3 cp $file.FullName "s3://$BucketName/$s3Key" --region $Region --content-type $contentType
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✅ Uploaded successfully" -ForegroundColor Green
                $uploadedFiles += @{
                    LocalPath    = $relativePath
                    S3Key        = $s3Key
                    Size         = $file.Length
                    LastModified = $file.LastWriteTime
                }
            }
            else {
                Write-Host "    ❌ Upload failed" -ForegroundColor Red
            }
        }
        catch {
            Write-Host "    ❌ Error: $_" -ForegroundColor Red
        }
    }
}

if ($uploadedFiles.Count -eq 0) {
    Write-Host "⚠️ No recent log files found to upload" -ForegroundColor Yellow
    exit 0
}

# Create summary report
$summaryReport = @{
    UploadTimestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    TotalFiles      = $uploadedFiles.Count
    TotalSize       = ($uploadedFiles | Measure-Object -Property Size -Sum).Sum
    Files           = $uploadedFiles
} | ConvertTo-Json -Depth 3

$summaryPath = "upload-summary-$timestamp.json"
$summaryReport | Out-File -FilePath $summaryPath -Encoding UTF8

# Upload summary
aws s3 cp $summaryPath "s3://$BucketName/logs/batch-$timestamp/upload-summary.json" --region $Region --content-type "application/json"

Write-Host "🎉 Upload complete!" -ForegroundColor Green
Write-Host "  📊 Files uploaded: $($uploadedFiles.Count)" -ForegroundColor Cyan
Write-Host "  📦 Total size: $([math]::Round(($uploadedFiles | Measure-Object -Property Size -Sum).Sum / 1KB, 2)) KB" -ForegroundColor Cyan
Write-Host "  🔗 S3 prefix: s3://$BucketName/logs/batch-$timestamp/" -ForegroundColor Cyan

# Generate presigned URL for summary
$summaryUrl = aws s3 presign "s3://$BucketName/logs/batch-$timestamp/upload-summary.json" --expires-in 3600 --region $Region
Write-Host "🌐 Summary URL (valid for 1 hour):" -ForegroundColor Green
Write-Host $summaryUrl -ForegroundColor White

# Clean up local summary file
Remove-Item $summaryPath -Force