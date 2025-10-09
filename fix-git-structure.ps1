# Fix Git Structure - Remove submodule .git folders
Write-Host "🔧 Fixing Git repository structure..." -ForegroundColor Yellow

# Remove .git folders from subdirectories
$subGitFolders = @("backend\.git", "frontend\.git")

foreach ($folder in $subGitFolders) {
    if (Test-Path $folder) {
        Write-Host "📁 Removing $folder..." -ForegroundColor Cyan
        Remove-Item -Recurse -Force $folder
        Write-Host "✅ Removed $folder" -ForegroundColor Green
    } else {
        Write-Host "ℹ️ $folder not found (already clean)" -ForegroundColor Gray
    }
}

# Check git status to see if files are now visible
Write-Host ""
Write-Host "📋 Checking git status..." -ForegroundColor Yellow
git status --porcelain

Write-Host ""
Write-Host "🎉 Git structure fixed!" -ForegroundColor Green
Write-Host "Now run: .\git-upload.ps1 -Message 'Fixed git structure - added backend and frontend content'" -ForegroundColor Cyan