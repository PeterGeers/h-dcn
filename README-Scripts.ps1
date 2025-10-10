# H-DCN Deployment Scripts
# Run deployment pipeline from startUpload folder

Write-Host "H-DCN Project Structure:" -ForegroundColor Green
Write-Host "========================" -ForegroundColor Green
Write-Host "startUpload/    - Main deployment pipeline" -ForegroundColor Cyan
Write-Host "git/            - Git operations and setup" -ForegroundColor Cyan
Write-Host "scripts/        - Utility and fix scripts" -ForegroundColor Cyan
Write-Host "frontend/       - React application" -ForegroundColor Cyan
Write-Host "backend/        - AWS Lambda functions" -ForegroundColor Cyan
Write-Host ""
Write-Host "To deploy: cd startUpload && .\startUploadS3.ps1" -ForegroundColor Yellow