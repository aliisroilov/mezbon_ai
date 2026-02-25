# 🚀 MEZBON AI - CLOUD DEPLOYMENT GUIDE

## Architecture Overview

```
Cloud Server (Public IP)
├── Backend API (FastAPI) - Port 8000
├── Admin Dashboard (React) - Port 3000
├── Doctor Panel (React) - Port 3001
├── PostgreSQL Database - Port 5432
└── Nginx (Reverse Proxy) - Port 80/443

Kiosk Locations (Multiple Clinics)
└── Kiosk UI (React) + Printer
    - Connects to cloud via HTTPS/WSS
    - Local printer via USB
```

---

## PART 1: SERVER SETUP (One-time)

### 1.1 Create Cloud Server

**DigitalOcean (Recommended):**
1. Sign up at https://digitalocean.com
2. Create new Droplet:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic - $12/month (2GB RAM)
   - **Datacenter**: Frankfurt or Amsterdam
   - **Authentication**: SSH key or password
3. Note your server IP: `YOUR_SERVER_IP`

**Alternative - Hetzner (Cheapest):**
1. Sign up at https://hetzner.com
2. Create CX11 server (€4.15/month)
3. Same specs as above

### 1.2 Initial Server Configuration

SSH into your server:
```bash
ssh root@YOUR_SERVER_IP
```

Update system:
```bash
apt update && apt upgrade -y
```

Install required packages:
```bash
apt install -y python3.10 python3-pip python3-venv \
  postgresql postgresql-contrib \
  nginx certbot python3-certbot-nginx \
  git curl build-essential \
  redis-server
```

### 1.3 Setup PostgreSQL

```bash
# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE mezbon_prod;
CREATE USER mezbon WITH PASSWORD 'CHANGE_THIS_PASSWORD';
ALTER ROLE mezbon SET client_encoding TO 'utf8';
ALTER ROLE mezbon SET default_transaction_isolation TO 'read committed';
ALTER ROLE mezbon SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE mezbon_prod TO mezbon;
\q
EOF
```

### 1.4 Setup Redis

```bash
systemctl start redis-server
systemctl enable redis-server
```

---

## PART 2: BACKEND DEPLOYMENT

### 2.1 Create Application User

```bash
adduser --disabled-password --gecos "" mezbon
usermod -aG sudo mezbon
su - mezbon
```

### 2.2 Clone Repository

```bash
cd /home/mezbon
git clone YOUR_REPO_URL mezbon-ai
cd mezbon-ai/backend
```

Or upload via SCP:
```bash
# From your Mac
scp -r /Users/aliisroilov/Desktop/AI\ Reception/backend root@YOUR_SERVER_IP:/home/mezbon/mezbon-ai/
```

### 2.3 Setup Python Environment

```bash
cd /home/mezbon/mezbon-ai/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.4 Configure Environment

Create `/home/mezbon/mezbon-ai/backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://mezbon:CHANGE_THIS_PASSWORD@localhost:5432/mezbon_prod
DATABASE_URL_SYNC=postgresql://mezbon:CHANGE_THIS_PASSWORD@localhost:5432/mezbon_prod

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET=$(openssl rand -hex 32)
JWT_REFRESH_SECRET=$(openssl rand -hex 32)
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# Encryption
ENCRYPTION_KEY=$(openssl rand -hex 32)

# AI
GEMINI_API_KEY=AIzaSyDu9_5VhHNrqy9OQo6EbAQB9_aXcLyagtc
GEMINI_MODEL=gemini-2.0-flash
MUXLISA_API_URL=https://service.muxlisa.uz/api/v2
MUXLISA_API_KEY=5aI_jAk8byCqwU5PI4C_Y-az4pxrPif7ttTcGN8A
MUXLISA_MOCK=false

# Face AI
INSIGHTFACE_MODEL=buffalo_l
INSIGHTFACE_DEVICE=cpu

# Printer - NETWORK MODE for remote kiosks
PRINTER_TYPE=network
PRINTER_HOST=10.99.0.184  # First kiosk IP
PRINTER_PORT=9100

# Payments
PAYMENT_MOCK=false

# App
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=https://kiosk.mezbon.uz,https://admin.mezbon.uz,https://doctor.mezbon.uz
LOG_LEVEL=INFO
```

### 2.5 Run Database Migrations

```bash
source venv/bin/activate
alembic upgrade head
```

### 2.6 Create Systemd Service

Create `/etc/systemd/system/mezbon-backend.service`:

```ini
[Unit]
Description=Mezbon AI Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=mezbon
WorkingDirectory=/home/mezbon/mezbon-ai/backend
Environment="PATH=/home/mezbon/mezbon-ai/backend/venv/bin"
ExecStart=/home/mezbon/mezbon-ai/backend/venv/bin/python -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
systemctl daemon-reload
systemctl enable mezbon-backend
systemctl start mezbon-backend
systemctl status mezbon-backend
```

---

## PART 3: FRONTEND DEPLOYMENT

### 3.1 Install Node.js

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt install -y nodejs
```

### 3.2 Build Kiosk UI

```bash
cd /home/mezbon/mezbon-ai/kiosk-ui

# Create production .env
cat > .env << EOF
VITE_API_URL=https://api.mezbon.uz
VITE_WS_URL=wss://api.mezbon.uz
EOF

npm install
npm run build
```

### 3.3 Build Admin Dashboard

```bash
cd /home/mezbon/mezbon-ai/admin-dashboard

cat > .env << EOF
VITE_API_URL=https://api.mezbon.uz
EOF

npm install
npm run build
```

---

## PART 4: NGINX CONFIGURATION

### 4.1 Setup Domain Names

Point these domains to your server IP:
- `api.mezbon.uz` → YOUR_SERVER_IP
- `kiosk.mezbon.uz` → YOUR_SERVER_IP
- `admin.mezbon.uz` → YOUR_SERVER_IP
- `doctor.mezbon.uz` → YOUR_SERVER_IP

### 4.2 Nginx Config

Create `/etc/nginx/sites-available/mezbon`:

```nginx
# Backend API
server {
    listen 80;
    server_name api.mezbon.uz;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Kiosk UI - RESTRICTED ACCESS
server {
    listen 80;
    server_name kiosk.mezbon.uz;

    # IP whitelist (only your kiosk IPs)
    allow 10.99.0.184;  # Clinic 1
    # allow 10.99.0.185;  # Clinic 2 (add more)
    deny all;

    root /home/mezbon/mezbon-ai/kiosk-ui/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}

# Admin Dashboard - ACCESSIBLE FROM ANYWHERE
server {
    listen 80;
    server_name admin.mezbon.uz;

    root /home/mezbon/mezbon-ai/admin-dashboard/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}

# Doctor Panel - ACCESSIBLE FROM ANYWHERE
server {
    listen 80;
    server_name doctor.mezbon.uz;

    root /home/mezbon/mezbon-ai/admin-dashboard/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Enable site:
```bash
ln -s /etc/nginx/sites-available/mezbon /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 4.3 Setup SSL (HTTPS)

```bash
certbot --nginx -d api.mezbon.uz -d kiosk.mezbon.uz -d admin.mezbon.uz -d doctor.mezbon.uz
```

---

## PART 5: KIOSK SETUP (Each Clinic Location)

### 5.1 Install Print Server on Kiosk

On each kiosk Windows machine, copy and run `kiosk_print_server.py`:

```cmd
pip install python-escpos
python kiosk_print_server.py
```

Server will listen on port 9100.

### 5.2 Configure Kiosk Browser

1. Install Chrome on kiosk
2. Create shortcut with:
   ```
   chrome.exe --kiosk --app=https://kiosk.mezbon.uz
   ```
3. Add to Windows startup

### 5.3 Network Configuration

**Important:** Your kiosk must be accessible from cloud server for printing.

**Option A: Static Public IP** (if kiosk has one)
- Configure firewall to allow port 9100 from server IP

**Option B: VPN** (recommended)
- Setup WireGuard VPN between server and kiosks
- Secure tunnel for print commands

**Option C: Reverse Tunnel** (easiest)
- Use ngrok or similar to expose kiosk:9100
- Update PRINTER_HOST in backend .env

---

## PART 6: MULTI-KIOSK PRINTER SETUP

Since you'll have multiple clinics, you need smart printer routing:

### 6.1 Update Backend for Multiple Printers

Edit `backend/app/services/printer_service.py`:

```python
# Support multiple printers per clinic
PRINTER_CONFIGS = {
    "clinic_1": {
        "host": "10.99.0.184",
        "port": 9100,
    },
    "clinic_2": {
        "host": "10.99.0.185",
        "port": 9100,
    },
}

def get_printer_for_clinic(clinic_id: str):
    config = PRINTER_CONFIGS.get(clinic_id)
    return Network(config["host"], config["port"])
```

---

## PART 7: TESTING DEPLOYMENT

### 7.1 Test Backend

```bash
curl https://api.mezbon.uz/health
# Expected: {"status": "healthy"}
```

### 7.2 Test Kiosk UI

From kiosk browser:
```
https://kiosk.mezbon.uz
```

### 7.3 Test Admin Dashboard

From anywhere:
```
https://admin.mezbon.uz
```

### 7.4 Test Printer

From server, test print to kiosk:
```bash
cd /home/mezbon/mezbon-ai/backend
source venv/bin/activate
python3 test_network_printer.py 10.99.0.184
```

---

## PART 8: SECURITY HARDENING

### 8.1 Firewall

```bash
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

### 8.2 Fail2Ban

```bash
apt install fail2ban
systemctl enable fail2ban
```

### 8.3 Auto-Updates

```bash
apt install unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades
```

---

## PART 9: MONITORING

### 9.1 Setup Logging

```bash
# View backend logs
journalctl -u mezbon-backend -f

# View nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 9.2 Health Checks

Add to cron for daily checks:
```bash
0 */6 * * * curl -s https://api.mezbon.uz/health || echo "Backend down!" | mail -s "Alert" admin@mezbon.uz
```

---

## DEPLOYMENT CHECKLIST

- [ ] Server created and configured
- [ ] PostgreSQL database setup
- [ ] Backend deployed and running
- [ ] Frontend built and served
- [ ] Nginx configured with SSL
- [ ] DNS records pointing to server
- [ ] Kiosk print server running
- [ ] Kiosk browser in kiosk mode
- [ ] Admin dashboard accessible
- [ ] Test booking creates queue ticket
- [ ] Printer auto-prints from cloud

---

## UPDATING CODE

### Backend Update

```bash
cd /home/mezbon/mezbon-ai/backend
git pull
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
systemctl restart mezbon-backend
```

### Frontend Update

```bash
cd /home/mezbon/mezbon-ai/kiosk-ui
git pull
npm install
npm run build
# Nginx serves new build automatically
```

---

## ESTIMATED COSTS

| Service | Cost/Month |
|---------|------------|
| Cloud Server (Hetzner CX11) | $5 |
| Domain (mezbon.uz) | $12/year ≈ $1/month |
| SSL Certificates (Let's Encrypt) | FREE |
| **TOTAL** | **~$6/month** |

---

## NEXT STEPS

1. **Choose hosting provider** (Hetzner recommended)
2. **Register domain** (mezbon.uz or similar)
3. **Deploy following this guide**
4. **Test with one kiosk first**
5. **Scale to multiple clinics**

---

**Status:** Ready for deployment 🚀  
**Support:** See troubleshooting section for common issues
