Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
Set-Location frontend
$frontend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm start" -PassThru
Set-Location ..

Write-Host ""
Write-Host "Frontend: http://localhost:3000 (PID: $($frontend.Id))" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")