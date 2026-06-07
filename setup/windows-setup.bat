@echo off
:: JobPilot AI — ChromeDriver setup helper (Windows)
:: Author: Md. Mahamudul Hasan
:: License: GNU Affero General Public License v3

setlocal enabledelayedexpansion

echo JobPilot AI: Installing ChromeDriver for Testing...

set "CHROME_DIR=C:\Program Files\Google\Chrome"
set "JSON_URL=https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
set "TEMP_JSON=%TEMP%\chrome-for-testing.json"
set "TEMP_ZIP=%TEMP%\chromedriver-win64.zip"

powershell -NoProfile -Command ^
  "$json = Invoke-RestMethod '%JSON_URL%';" ^
  "$url = ($json.channels.Stable.downloads | Where-Object { $_.platform -eq 'win64' -and $_.url -match 'chromedriver' }).url;" ^
  "if (-not $url) { throw 'Could not resolve ChromeDriver download URL.' };" ^
  "Invoke-WebRequest -Uri $url -OutFile '%TEMP_ZIP%';" ^
  "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%TEMP%\chromedriver_extract' -Force;" ^
  "New-Item -ItemType Directory -Force -Path '%CHROME_DIR%' | Out-Null;" ^
  "Copy-Item -Force '%TEMP%\chromedriver_extract\chromedriver-win64\chromedriver.exe' '%CHROME_DIR%\chromedriver.exe';"

if errorlevel 1 (
    echo Failed to download or install ChromeDriver.
    pause
    exit /b 1
)

echo ChromeDriver installed to %CHROME_DIR%\chromedriver.exe
echo Setup complete for JobPilot AI.
pause
