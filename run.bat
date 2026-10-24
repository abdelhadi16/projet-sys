@echo off
REM ===========================================================================
REM  run.bat - launch kbmonitor.exe as Administrator and open the firewall.
REM  Put this next to kbmonitor.exe (or in the dist\ folder) and double-click it.
REM ===========================================================================

REM --- Config: change this if you built/launch on a different port ---
set PORT=8000

REM --- Self-elevate to Administrator (shows a UAC prompt the first time) ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator rights...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

REM Now running elevated. Work from this script's own folder.
cd /d "%~dp0"

REM --- Find the exe: same folder, or a dist\ subfolder ---
set EXE=kbmonitor.exe
if not exist "%EXE%" if exist "dist\kbmonitor.exe" set EXE=dist\kbmonitor.exe
if not exist "%EXE%" (
    echo [ERROR] kbmonitor.exe not found next to this script or in dist\.
    echo         Build it first with build.bat.
    pause
    exit /b 1
)

REM --- Open the firewall for the dashboard port (idempotent) ---
echo Opening firewall for TCP %PORT% ...
netsh advfirewall firewall delete rule name="kbmonitor" >nul 2>&1
netsh advfirewall firewall add rule name="kbmonitor" dir=in action=allow protocol=TCP localport=%PORT% >nul 2>&1

REM --- Show this machine's IP so you know what to point the dashboard at ---
echo.
echo This machine's IPv4 address(es) - use one of these on your server:
powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' } | Select-Object -ExpandProperty IPAddress"
echo.
echo Point the dashboard at:  http://^<this-ip^>:%PORT%
echo Starting kbmonitor on port %PORT% ...  (close this window to stop)
echo.

"%EXE%" %PORT%
pause
