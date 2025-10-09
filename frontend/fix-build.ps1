Write-Host "Fixing build and redeploying..." -ForegroundColor Yellow

# Clean previous build
Write-Host "1. Cleaning previous build..." -ForegroundColor Cyan
if (Test-Path "build") {
    Remove-Item -Recurse -Force build
    Write-Host "   Build folder removed" -ForegroundColor Green
}

# Clean node_modules cache
Write-Host "2. Cleaning npm cache..." -ForegroundColor Cyan
npm cache clean --force

# Fix vulnerabilities first
Write-Host "3. Fixing vulnerabilities..." -ForegroundColor Cyan
npm audit fix

# Reinstall dependencies
Write-Host "4. Reinstalling dependencies..." -ForegroundColor Cyan
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
npm install

# Create fresh build
Write-Host "5. Creating fresh build..." -ForegroundColor Cyan
$env:GENERATE_SOURCEMAP="false"
npm run build

if (Test-Path "build") {
    Write-Host "6. Build successful! Ready to deploy." -ForegroundColor Green
    Write-Host "   Now run your deployment script to upload to S3" -ForegroundColor Yellow
} else {
    Write-Host "6. Build failed!" -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")