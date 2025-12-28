# Simple PowerShell Profile for H-DCN
Write-Host "H-DCN Dashboard PowerShell Profile Loaded!" -ForegroundColor Magenta

# Simple function to navigate to project
function hdcn {
    Set-Location "C:\path\to\your\h-dcn\project"
}

# Add any other simple functions here
function ll {
    Get-ChildItem -Force
}

Write-Host "Profile loaded successfully. Use 'hdcn' to navigate to project." -ForegroundColor Green