#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test script for DataProcessingService with various options
.DESCRIPTION
    This script provides convenient ways to run DataProcessingService tests
    with different configurations and reporting options.
#>

param(
    [Parameter(HelpMessage = "Run tests in watch mode")]
    [switch]$Watch,
    
    [Parameter(HelpMessage = "Generate coverage report")]
    [switch]$Coverage,
    
    [Parameter(HelpMessage = "Run tests with verbose output")]
    [switch]$Verbose,
    
    [Parameter(HelpMessage = "Run only specific test pattern")]
    [string]$Pattern = "",
    
    [Parameter(HelpMessage = "Update snapshots")]
    [switch]$UpdateSnapshots
)

Write-Host "🧪 H-DCN DataProcessingService Test Runner" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Change to frontend directory
Set-Location $PSScriptRoot/..

# Build test command
$testCommand = "npm test -- --testPathPattern=DataProcessingService"

if ($Watch) {
    Write-Host "📺 Running tests in watch mode..." -ForegroundColor Yellow
    $testCommand += " --watch"
}
else {
    $testCommand += " --watchAll=false"
}

if ($Coverage) {
    Write-Host "📊 Generating coverage report..." -ForegroundColor Yellow
    $testCommand += " --coverage --coverageDirectory=coverage/data-processing"
}

if ($Verbose) {
    Write-Host "🔍 Running with verbose output..." -ForegroundColor Yellow
    $testCommand += " --verbose"
}

if ($Pattern) {
    Write-Host "🎯 Running tests matching pattern: $Pattern" -ForegroundColor Yellow
    $testCommand += " --testNamePattern='$Pattern'"
}

if ($UpdateSnapshots) {
    Write-Host "📸 Updating snapshots..." -ForegroundColor Yellow
    $testCommand += " --updateSnapshot"
}

Write-Host ""
Write-Host "Executing: $testCommand" -ForegroundColor Gray
Write-Host ""

# Run the tests
Invoke-Expression $testCommand

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "✅ All DataProcessingService tests passed!" -ForegroundColor Green
    
    if ($Coverage) {
        Write-Host "📊 Coverage report generated in: coverage/data-processing/" -ForegroundColor Cyan
        Write-Host "   Open coverage/data-processing/lcov-report/index.html to view detailed report" -ForegroundColor Gray
    }
}
else {
    Write-Host ""
    Write-Host "❌ Some tests failed. Exit code: $exitCode" -ForegroundColor Red
}

exit $exitCode