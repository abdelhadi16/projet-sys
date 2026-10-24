@echo off
REM ===========================================================================
REM  run-dashboard.bat - start the React dashboard on your server and point it
REM  at the VM that is running kbmonitor.exe. Double-click it.
REM  Needs Node.js 18+ installed.
REM ===========================================================================

REM Work from the frontend folder (this script sits at the repo root).
cd /d "%~dp0frontend"

echo ============================================
echo   Dashboard launcher
echo ============================================
echo.

REM --- Ask where the agent (VM) is ---
set /p VMIP=VM IP shown by run.bat (blank = this machine / localhost):
if "%VMIP%"=="" set VMIP=127.0.0.1

set /p VMPORT=Port (blank = 8000):
if "%VMPORT%"=="" set VMPORT=8000

set VITE_API_BASE=http://%VMIP%:%VMPORT%
echo.
echo Dashboard will connect to:  %VITE_API_BASE%
echo.

REM --- Install dependencies the first time only ---
if not exist "node_modules" (
    echo Installing dependencies ^(first run only, may take a minute^)...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed. Is Node.js 18+ installed and on PATH?
        pause
        exit /b 1
    )
)

echo Starting the dashboard at http://localhost:5173   ^(close this window to stop^)
echo.
call npm run dev
pause
