# Test the deployment validation
Write-Host "Testing deployment validation..." -ForegroundColor Cyan

# Test the standalone validation script
& "scripts/deployment/validate-deployment.ps1" -Type both -Detailed

Write-Host ""
Write-Host "Validation test completed!" -ForegroundColor Green