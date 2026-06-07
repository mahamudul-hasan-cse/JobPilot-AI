# JobPilot AI launcher for PowerShell (run: .\start_jobpilotai.ps1)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONUNBUFFERED = "1"

Write-Host "========================================"
Write-Host "  JobPilot AI - Job Application Bot"
Write-Host "========================================"

if (Get-Command py -ErrorAction SilentlyContinue) { $py = "py -3" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
else { throw "Python not found. Install Python 3.11+ and add to PATH." }

Get-Process chrome, chromedriver -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

Invoke-Expression "$py scripts\preflight.py"
Invoke-Expression "$py main.py"

Read-Host "Press Enter to close"
