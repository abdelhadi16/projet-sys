@echo off
REM ===========================================================================
REM  build.bat - one-click build of kbmonitor.exe (backend + keyboard hook).
REM  Double-click this file on a Windows machine that has Python 3.11+ installed.
REM  The finished exe needs no Python on the machine you run it on.
REM ===========================================================================

echo ============================================
echo   Building kbmonitor.exe
echo ============================================
echo.

REM Move to this script's own folder so it works from anywhere.
cd /d "%~dp0"

echo [1/2] Installing build + runtime dependencies...
python -m pip install --upgrade pip
python -m pip install pyinstaller fastapi uvicorn pydantic
if errorlevel 1 (
    echo.
    echo [ERROR] Could not install dependencies.
    echo         Make sure Python 3.11+ is installed and on your PATH.
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] Freezing the backend into one file...
python -m PyInstaller --onefile --name kbmonitor --collect-all uvicorn run_server.py
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed - see the messages above.
    echo         If it says a module is missing, add it, e.g.:
    echo         python -m PyInstaller --onefile --name kbmonitor --collect-all uvicorn --collect-all fastapi run_server.py
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Done!  Your exe is here:  dist\kbmonitor.exe
echo ============================================
echo.
echo   Next: copy dist\kbmonitor.exe into the VM and
echo   run it AS ADMINISTRATOR. See BUILD_EXE.md.
echo.
pause
