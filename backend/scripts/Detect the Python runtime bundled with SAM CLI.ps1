# Detect the Python runtime bundled with AWS SAM CLI
$samPython = "C:\Program Files\Amazon\AWSSAMCLI\runtime\python.exe"

if (Test-Path $samPython) {
    Write-Host "SAM CLI Python runtime found at: $samPython"
} else {
    Write-Host "Could not find SAM CLI runtime at expected path."
    Write-Host "Falling back to system Python (py launcher)."
    $samPython = (Get-Command py).Source
}

# Show version
& $samPython --version

# Install or upgrade pywin32
& $samPython -m pip install --upgrade pip
& $samPython -m pip install --upgrade pywin32