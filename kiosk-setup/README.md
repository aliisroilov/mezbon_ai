# Mezbon AI Kiosk — Deployment Guide

## Hardware Requirements

- **Display:** 32" vertical touchscreen (1080x1920 portrait, FullHD)
- **CPU:** Intel i5-12450H or better
- **RAM:** 8GB minimum
- **Storage:** 256GB SSD M2
- **Camera:** Built-in 1080p webcam
- **Printer:** Built-in 80mm thermal receipt printer
- **OS:** Windows 11

## Prerequisites

Install these manually before running the installer:

1. **PostgreSQL 16** — https://www.postgresql.org/download/windows/
   - Install as Windows service
   - Create database: `mezbon_clinic`
   - Default port: 5432

2. **Redis 7** — https://github.com/microsoftarchive/redis/releases
   - Or use Memurai (Redis-compatible for Windows): https://www.memurai.com/

3. **Google Chrome** — https://www.google.com/chrome/

4. **Google Gemini API Key** — https://aistudio.google.com/

## Installation

### Step 1: Copy Project Files

Copy the entire project to the kiosk machine (USB drive or network).

### Step 2: Configure Environment

Create `C:\mezbon\backend\.env` with the following:

```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/mezbon_clinic
DATABASE_URL_SYNC=postgresql://postgres:your_password@localhost:5432/mezbon_clinic
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=<generate with: openssl rand -hex 32>
JWT_REFRESH_SECRET=<generate with: openssl rand -hex 32>
ENCRYPTION_KEY=<generate with: openssl rand -hex 32>
GEMINI_API_KEY=<your-google-ai-key>
GEMINI_MODEL=gemini-2.0-flash
MUXLISA_API_URL=https://api.muxlisa.uz
MUXLISA_API_KEY=<your-key>
MUXLISA_MOCK=false
INSIGHTFACE_MODEL=buffalo_l
INSIGHTFACE_DEVICE=cpu
PAYMENT_MOCK=true
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

### Step 3: Run Installer

1. Right-click `install.bat` and select **Run as administrator**
2. Wait for all components to install (~10-15 minutes)
3. Follow any on-screen prompts

### Step 4: Initialize Database

```batch
cd C:\mezbon\backend
.venv\Scripts\activate
alembic upgrade head
python scripts/seed.py
python scripts/create_admin.py
```

### Step 5: Configure Auto-Login

1. Press `Win+R`, type `netplwiz`, press Enter
2. Uncheck "Users must enter a user name and password"
3. Click Apply, enter the kiosk user credentials

### Step 6: Restart

Restart the computer. The kiosk should:
1. Auto-login
2. Start PostgreSQL and Redis
3. Start the backend server
4. Launch Chrome in fullscreen kiosk mode
5. Display the Mezbon reception screen

## Troubleshooting

### Backend won't start
- Check `.env` file exists and has correct values
- Verify PostgreSQL is running: `net start postgresql-x64-16`
- Verify Redis is running: `redis-cli ping`
- Check logs: `C:\mezbon\backend\logs\`

### Display not in portrait mode
- Run: `powershell -ExecutionPolicy Bypass -File C:\mezbon\set-portrait.ps1`
- Or manually: Settings > System > Display > Orientation > Portrait

### Chrome crashes or shows error
- Clear Chrome cache: delete `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache`
- Check backend is running: open `http://localhost:8000/api/docs` in another browser

### Thermal printer not working
- Verify printer is connected via USB
- Check Device Manager for the printer
- Install printer drivers if needed
- Test with: `echo test > \\.\COM3` (adjust COM port)

### Reverting kiosk restrictions
```powershell
powershell -ExecutionPolicy Bypass -File C:\mezbon\disable-peripherals.ps1 -Revert
```

## Maintenance

### Update the application
1. Stop Chrome (Alt+F4 if keyboard is accessible, or kill from Task Manager)
2. Copy new files to `C:\mezbon\`
3. Run migrations: `cd C:\mezbon\backend && .venv\Scripts\activate && alembic upgrade head`
4. Rebuild frontend: `cd C:\mezbon\kiosk-ui && npm run build`
5. Restart the kiosk

### Database backup
```batch
pg_dump -U postgres mezbon_clinic > C:\mezbon\backups\backup_%date:~-4%-%date:~4,2%-%date:~7,2%.sql
```

### View logs
- Backend logs: `C:\mezbon\backend\logs\`
- Chrome logs: `%LOCALAPPDATA%\Google\Chrome\User Data\chrome_debug.log`
