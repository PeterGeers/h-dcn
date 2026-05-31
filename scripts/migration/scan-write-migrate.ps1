#!/usr/bin/env pwsh
# Simple scan + batch-write migration
param([switch]$CreateOnly)

$tables = @("Producten", "Members", "Payments", "Events", "Memberships", "Carts", "Orders")
$srcProfile = "personal"
$dstProfile = "nonprofit-deploy"
$region = "eu-west-1"

# Check which tables already exist
$existing = (aws dynamodb list-tables --profile $dstProfile --region $region --output json | ConvertFrom-Json).TableNames

foreach ($t in $tables) {
    Write-Host "`n=== $t ===" -ForegroundColor Cyan
    
    # Get source schema
    $srcJson = aws dynamodb describe-table --table-name $t --profile $srcProfile --region $region --output json
    $src = $srcJson | ConvertFrom-Json
    
    # Create table if it doesn't exist
    if ($t -notin $existing) {
        Write-Host "  Creating table..."
        $keySchema = $src.Table.KeySchema | ConvertTo-Json -Compress
        $attrDefs = $src.Table.AttributeDefinitions | ConvertTo-Json -Compress
        
        $args = @("dynamodb", "create-table", "--table-name", $t, "--key-schema", $keySchema, "--attribute-definitions", $attrDefs, "--billing-mode", "PAY_PER_REQUEST", "--profile", $dstProfile, "--region", $region, "--output", "json")
        
        if ($src.Table.GlobalSecondaryIndexes) {
            $gsis = @()
            foreach ($gsi in $src.Table.GlobalSecondaryIndexes) {
                $gsis += @{IndexName=$gsi.IndexName; KeySchema=$gsi.KeySchema; Projection=@{ProjectionType=$gsi.Projection.ProjectionType}}
            }
            $gsiJson = ($gsis | ConvertTo-Json -Depth 5 -Compress)
            if ($gsis.Count -eq 1) { $gsiJson = "[$gsiJson]" }
            $args += @("--global-secondary-indexes", $gsiJson)
        }
        
        aws @args 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Host "  FAIL create" -ForegroundColor Red; continue }
        
        Write-Host "  Waiting for ACTIVE..."
        aws dynamodb wait table-exists --table-name $t --profile $dstProfile --region $region
    } else {
        Write-Host "  Table already exists"
    }
    
    if ($CreateOnly) { continue }
    
    # Scan and write
    Write-Host "  Migrating data..."
    $totalItems = 0
    $lastKey = $null
    
    do {
        $scanArgs = @("dynamodb", "scan", "--table-name", $t, "--profile", $srcProfile, "--region", $region, "--output", "json")
        if ($lastKey) { $scanArgs += @("--exclusive-start-key", $lastKey) }
        
        $scanResult = aws @scanArgs | ConvertFrom-Json
        $items = $scanResult.Items
        
        if ($items -and $items.Count -gt 0) {
            for ($i = 0; $i -lt $items.Count; $i += 25) {
                $end = [Math]::Min($i + 24, $items.Count - 1)
                $batch = $items[$i..$end]
                $putRequests = @()
                foreach ($item in $batch) {
                    $putRequests += @{PutRequest=@{Item=$item}}
                }
                $batchInput = @{RequestItems=@{$t=$putRequests}} | ConvertTo-Json -Depth 10 -Compress
                $tmpFile = "$env:TEMP\batch-$t.json"
                $batchInput | Out-File -FilePath $tmpFile -Encoding utf8NoBOM -Force
                
                aws dynamodb batch-write-item --cli-input-json "file://$tmpFile" --profile $dstProfile --region $region --output json 2>&1 | Out-Null
                if ($LASTEXITCODE -ne 0) { Write-Host "  FAIL batch write at item $i" -ForegroundColor Red }
                Remove-Item $tmpFile -Force -ErrorAction SilentlyContinue
            }
            $totalItems += $items.Count
        }
        
        $lastKey = if ($scanResult.LastEvaluatedKey) { $scanResult.LastEvaluatedKey | ConvertTo-Json -Compress } else { $null }
    } while ($lastKey)
    
    Write-Host "  Done: $totalItems items" -ForegroundColor Green
}

Write-Host "`n=== Migration Complete ===" -ForegroundColor Cyan
