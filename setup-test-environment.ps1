# Setup Test Environment for testportal.h-dcn.nl
# Run this script to create the test infrastructure

# Variables
$BUCKET_NAME = "testportal-h-dcn-frontend"
$REGION = "eu-west-1"
$DOMAIN = "testportal.h-dcn.nl"

Write-Host "Setting up test environment for $DOMAIN" -ForegroundColor Green

# Step 1: Create S3 bucket
Write-Host "Creating S3 bucket: $BUCKET_NAME" -ForegroundColor Yellow
aws s3 mb s3://$BUCKET_NAME --region $REGION

# Step 2: Configure bucket for website hosting
Write-Host "Configuring S3 bucket for website hosting" -ForegroundColor Yellow
aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document index.html

# Step 3: Set bucket policy for public read access
Write-Host "Setting bucket policy for public access" -ForegroundColor Yellow
$bucketPolicy = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
        }
    ]
}
"@

$bucketPolicy | Out-File -FilePath "bucket-policy.json" -Encoding UTF8
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://bucket-policy.json
Remove-Item "bucket-policy.json"

# Step 4: Request SSL certificate (manual step)
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Request SSL certificate in AWS Certificate Manager for $DOMAIN"
Write-Host "2. Create CloudFront distribution using cloudfront-config.json"
Write-Host "3. Update DNS to point $DOMAIN to CloudFront domain"
Write-Host ""
Write-Host "SSL Certificate ARN will be needed for CloudFront setup"
Write-Host "Run: aws acm request-certificate --domain-name $DOMAIN --validation-method DNS --region us-east-1"
Write-Host ""
Write-Host "Note: SSL certificates for CloudFront must be in us-east-1 region!"