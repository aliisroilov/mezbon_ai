@echo off
REM ================================================================
REM  Mezbon AI Kiosk — Startup Script
REM  Runs on every boot via Task Scheduler
REM ================================================================

set INSTALL_DIR=C:\mezbon
set BACKEND_DIR=%INSTALL_DIR%\backend
set KIOSK_DIR=%INSTALL_DIR%\kiosk-ui

echo [Mezbon] Starting kiosk services...

REM ── Start PostgreSQL service ──
echo [Mezbon] Starting PostgreSQL...
net start postgresql-x64-16 2>nul
if %errorlevel% neq 0 (
    echo [Mezbon] PostgreSQL may already be running or not installed as service
)

REM ── Start Redis ──
echo [Mezbon] Starting Redis...
start /min "Redis" redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

REM ── Wait for database to be ready ──
echo [Mezbon] Waiting for services to initialize...
timeout /t 5 /nobreak >nul

REM ── Start backend ──
echo [Mezbon] Starting backend server...
cd /d %BACKEND_DIR%
start /min "MezbonBackend" cmd /c ".venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"

REM ── Wait for backend to be ready ──
echo [Mezbon] Waiting for backend to start...
:wait_backend
timeout /t 2 /nobreak >nul
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health' -TimeoutSec 2 -UseBasicParsing; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if %errorlevel% neq 0 (
    echo [Mezbon] Backend not ready yet, retrying...
    goto wait_backend
)
echo [Mezbon] Backend is ready!

REM ── Start frontend static server ──
echo [Mezbon] Starting frontend server...
start /min "MezbonFrontend" cmd /c "serve -s %KIOSK_DIR%\dist -l 5173 --no-clipboard"

REM ── Wait for frontend ──
timeout /t 3 /nobreak >nul

REM ── Launch Chrome in kiosk mode ──
echo [Mezbon] Launching kiosk browser...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
    --kiosk ^
    --start-fullscreen ^
    --disable-session-crashed-bubble ^
    --noerrdialogs ^
    --disable-translate ^
    --no-first-run ^
    --fast ^
    --fast-start ^
    --disable-features=TranslateUI ^
    --disable-infobars ^
    --disable-pinch ^
    --overscroll-history-navigation=0 ^
    --autoplay-policy=no-user-gesture-required ^
    http://localhost:5173

echo [Mezbon] Kiosk started successfully!
