# JobPilot AI — setup helper (PowerShell)
# Author: Md. Mahamudul Hasan

while (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python is not installed. Install from https://www.python.org/downloads/ then re-run."
    Read-Host "Press Enter after installing Python"
}

while (-not (Test-Path "C:\Program Files\Google\Chrome\Application\chrome.exe")) {
    Write-Host "Install Google Chrome from https://www.google.com/chrome/ then re-run."
    Read-Host "Press Enter after installing Chrome"
}

pip install -r requirements.txt

$jsonUrl = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
$json = Invoke-RestMethod $jsonUrl
$url = ($json.channels.Stable.downloads | Where-Object { $_.platform -eq "win64" -and $_.url -match "chromedriver" }).url
$zip = "$env:TEMP\chromedriver-win64.zip"
Invoke-WebRequest -Uri $url -OutFile $zip
Expand-Archive -Path $zip -DestinationPath "$env:TEMP\chromedriver_extract" -Force
$dest = "C:\Program Files\Google\Chrome"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Force "$env:TEMP\chromedriver_extract\chromedriver-win64\chromedriver.exe" "$dest\chromedriver.exe"

Write-Host "JobPilot AI setup complete."
Read-Host "Press Enter to exit"
