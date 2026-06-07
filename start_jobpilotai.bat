@echo off
setlocal EnableExtensions
:: JobPilot AI launcher — double-click this file to start.

title JobPilot AI
cd /d "%~dp0"
if errorlevel 1 (
    echo ERROR: Could not open project folder.
    pause
    exit /b 1
)

set "PYTHONUNBUFFERED=1"
set "PYCMD="

:: Pick Python that has project dependencies (python often has pip packages; py -3 may be a newer empty install)
call :try_python python
if not defined PYCMD call :try_python "%LocalAppData%\Programs\Python\Python311\python.exe"
if not defined PYCMD call :try_python "%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PYCMD call :try_python py -3

if not defined PYCMD (
    echo.
    echo ERROR: No working Python found for JobPilot AI.
    echo 1. Install Python 3.11+ from https://www.python.org/downloads/
    echo 2. Open Command Prompt in this folder and run:
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo ========================================
echo   JobPilot AI - Job Application Bot
echo ========================================
echo Project: %CD%
echo Python : %PYCMD%
echo.
echo IMPORTANT: Close ALL Chrome windows completely
echo            (not just tabs — quit Chrome from the taskbar).
echo.

echo [1/3] Stopping ALL Chrome processes...
taskkill /F /IM chrome.exe /T >nul 2>&1
taskkill /F /IM chromedriver.exe /T >nul 2>&1
if errorlevel 1 (
    echo        No Chrome was running — OK.
) else (
    echo        Chrome closed.
)
ping -n 4 127.0.0.1 >nul

echo [2/3] Validating configuration...
call %PYCMD% scripts\preflight.py
if errorlevel 1 (
    echo.
    echo Preflight FAILED. See messages above.
    echo.
    pause
    exit /b 1
)

echo [3/3] Starting JobPilot AI...
echo.
call %PYCMD% main.py
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" (
    echo JobPilot AI exited with error code %EXITCODE%.
) else (
    echo JobPilot AI finished.
)
echo Results: all excels\all_applied_applications_history.csv
echo Logs    : logs\log.txt
echo.
pause
exit /b %EXITCODE%

:try_python
set "CAND=%~1"
%CAND% -c "import pyautogui, selenium" >nul 2>&1
if errorlevel 1 exit /b 1
set "PYCMD=%CAND%"
exit /b 0
