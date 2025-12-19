#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Clone H-DCN security setup to a new project
.DESCRIPTION
    Copies security configuration and Kiro setup from H-DCN to any new project
.PARAMETER TargetPath
    Path to the target project directory
.EXAMPLE
    .\clone-with-security.ps1 -TargetPath "C:\Projects\new-project"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$TargetPath
)

$sourceFiles = @{
    ".gitguardian.yaml"             = "GitGuardian configuration"
    ".kiro/settings/mcp.json"       = "MCP server configuration"
    ".kiro/settings/workspace.json" = "Kiro workspace settings"
    "scripts/setup-security.ps1"    = "Security setup script"
}

Write-Host "🔄 Cloning H-DCN security setup to: $TargetPath" -ForegroundColor Green

foreach ($file in $sourceFiles.Keys) {
    $sourcePath = Join-Path $PWD $file
    $targetPath = Join-Path $TargetPath $file
    $targetDir = Split-Path $targetPath -Parent
    
    if (Test-Path $sourcePath) {
        # Create target directory if it doesn't exist
        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        
        # Copy file
        Copy-Item $sourcePath $targetPath -Force
        Write-Host "✅ Copied: $file ($($sourceFiles[$file]))" -ForegroundColor Cyan
    }
    else {
        Write-Host "⚠️  Source file not found: $file" -ForegroundColor Yellow
    }
}

Write-Host "`n🎉 Security setup cloned successfully!" -ForegroundColor Green
Write-Host "📋 Next steps in target project:" -ForegroundColor Blue
Write-Host "  1. cd '$TargetPath'"
Write-Host "  2. .\scripts\setup-security.ps1"
Write-Host "  3. Customize .gitguardian.yaml for your project type"