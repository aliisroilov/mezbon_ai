@echo off
REM ================================================================
REM  Mezbon AI Kiosk — Full Installation Script for Windows 11
REM  Run as Administrator!
REM ================================================================

echo ============================================
echo   Mezbon AI Kiosk Installer
echo ============================================
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

set INSTALL_DIR=C:\mezbon
set BACKEND_DIR=%INSTALL_DIR%\backend
set KIOSK_DIR=%INSTALL_DIR%\kiosk-ui

echo [1/10] Creating installation directory...
if not exist %INSTALL_DIR% mkdir %INSTALL_DIR%

REM ── Copy project files ──
echo [2/10] Copying project files...
xcopy /E /I /Y "%~dp0..\backend" "%BACKEND_DIR%"
xcopy /E /I /Y "%~dp0..\kiosk-ui" "%KIOSK_DIR%"
copy /Y "%~dp0startup.bat" "%INSTALL_DIR%\startup.bat"
copy /Y "%~dp0set-portrait.ps1" "%INSTALL_DIR%\set-portrait.ps1"
copy /Y "%~dp0disable-peripherals.ps1" "%INSTALL_DIR%\disable-peripherals.ps1"

REM ── Install Node.js ──
echo [3/10] Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Node.js LTS...
    powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi' -OutFile '%TEMP%\nodejs.msi'"
    msiexec /i "%TEMP%\nodejs.msi" /qn /norestart
    set "PATH=%PATH%;C:\Program Files\nodejs"
    echo Node.js installed.
) else (
    echo Node.js already installed.
)

REM ── Install Python 3.11 ──
echo [4/10] Checking Python 3.11...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Python 3.11...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe' -OutFile '%TEMP%\python311.exe'"
    "%TEMP%\python311.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    set "PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts"
    echo Python 3.11 installed.
) else (
    echo Python already installed.
)

REM ── Setup backend ──
echo [5/10] Setting up backend...
cd /d %BACKEND_DIR%
python -m venv .venv
call .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
echo Backend dependencies installed.

REM ── Build kiosk UI ──
echo [6/10] Building kiosk UI...
cd /d %KIOSK_DIR%
call npm install
call npm run build
echo Kiosk UI built successfully.

REM ── Install serve (static file server) ──
echo [7/10] Installing static file server...
call npm install -g serve
echo Static server installed.

REM ── Configure Windows firewall ──
echo [8/10] Configuring firewall...
netsh advfirewall firewall add rule name="Mezbon Backend" dir=in action=allow protocol=tcp localport=8000
netsh advfirewall firewall add rule name="Mezbon Frontend" dir=in action=allow protocol=tcp localport=5173
echo Firewall configured.

REM ── Disable sleep and screen timeout ──
echo [9/10] Disabling sleep and screen timeout...
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
echo Power settings configured.

REM ── Create startup task ──
echo [10/10] Creating startup task...
schtasks /create /tn "MezbonKiosk" /tr "%INSTALL_DIR%\startup.bat" /sc onlogon /rl highest /f
echo Startup task created.

REM ── Set portrait mode ──
echo Setting display to portrait mode...
powershell -ExecutionPolicy Bypass -File "%INSTALL_DIR%\set-portrait.ps1"

REM ── Apply kiosk restrictions ──
echo Applying kiosk security restrictions...
powershell -ExecutionPolicy Bypass -File "%INSTALL_DIR%\disable-peripherals.ps1"

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo   Install directory: %INSTALL_DIR%
echo   Backend: %BACKEND_DIR%
echo   Frontend: %KIOSK_DIR%
echo.
echo   Next steps:
echo   1. Copy .env file to %BACKEND_DIR%\.env
echo   2. Install PostgreSQL 16 and Redis 7
echo   3. Run database migrations: alembic upgrade head
echo   4. Seed demo data: python scripts/seed.py
echo   5. Restart the computer to launch kiosk
echo.
pause
