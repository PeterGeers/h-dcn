# H-DCN Dashboard PowerShell Profile
Write-Host "H-DCN Dashboard PowerShell Profile Loaded!" -ForegroundColor Magenta

# Function to navigate to H-DCN project
function hdcn {
    Set-Location "C:\path\to\your\h-dcn\project"
    Write-Host "Navigated to H-DCN project directory" -ForegroundColor Green
}

# Additional useful functions
function ll {
    Get-ChildItem -Force
}

function .. {
    Set-Location ..
}

function cls {
    Clear-Host
}

# Custom prompt (optional)
function prompt {
    $currentPath = Get-Location
    Write-Host "H-DCN " -NoNewline -ForegroundColor Cyan
    Write-Host "$currentPath" -NoNewline -ForegroundColor Yellow
    Write-Host " > " -NoNewline -ForegroundColor White
    return " "
}

Write-Host "Profile loaded successfully!" -ForegroundColor Green