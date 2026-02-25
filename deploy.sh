#!/bin/bash
################################################################################
# MEZBON AI - AUTOMATED CLOUD DEPLOYMENT SCRIPT
# Run this on your fresh Ubuntu 22.04 server
################################################################################

set -e  # Exit on error

echo "🚀 Starting Mezbon AI Deployment..."
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
read -p "Enter your server domain (e.g., mezbon.uz): " DOMAIN
read -p "Enter PostgreSQL password: " -s DB_PASSWORD
echo ""
read -p "Enter your kiosk IP address (e.g., 10.99.0.184): " KIOSK_IP

API_DOMAIN="api.${DOMAIN}"
KIOSK_DOMAIN="kiosk.${DOMAIN}"
ADMIN_DOMAIN="admin.${DOMAIN}"
DOCTOR_DOMAIN="doctor.${DOMAIN}"

echo ""
echo -e "${GREEN}✓${NC} Configuration:"
echo "  Domain: $DOMAIN"
echo "  API: https://$API_DOMAIN"
echo "  Kiosk: https://$KIOSK_DOMAIN"
echo "  Admin: https://$ADMIN_DOMAIN"
echo "  Kiosk IP: $KIOSK_IP"
echo ""

read -p "Continue with deployment? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

################################################################################
# STEP 1: System Update
################################################################################

echo ""
echo -e "${YELLOW}[1/10]${NC} Updating system..."
apt update -y && apt upgrade -y

################################################################################
# STEP 2: Install Dependencies
################################################################################

echo ""
echo -e "${YELLOW}[2/10]${NC} Installing dependencies..."
apt install -y \
    python3.10 python3-pip python3-venv \
    postgresql postgresql-contrib \
    nginx certbot python3-certbot-nginx \
    git curl build-essential \
    redis-server \
    ufw fail2ban

################################################################################
# STEP 3: Setup PostgreSQL
################################################################################

echo ""
echo -e "${YELLOW}[3/10]${NC} Setting up PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

sudo -u postgres psql << EOF
CREATE DATABASE mezbon_prod;
CREATE USER mezbon WITH PASSWORD '$DB_PASSWORD';
ALTER ROLE mezbon SET client_encoding TO 'utf8';
ALTER ROLE mezbon SET default_transaction_isolation TO 'read committed';
ALTER ROLE mezbon SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE mezbon_prod TO mezbon;
EOF

################################################################################
# STEP 4: Setup Redis
################################################################################

echo ""
echo -e "${YELLOW}[4/10]${NC} Setting up Redis..."
systemctl start redis-server
systemctl enable redis-server

################################################################################
# STEP 5: Create Application User
################################################################################

echo ""
echo -e "${YELLOW}[5/10]${NC} Creating application user..."
if ! id "mezbon" &>/dev/null; then
    adduser --disabled-password --gecos "" mezbon
fi

################################################################################
# STEP 6: Deploy Backend
################################################################################

echo ""
echo -e "${YELLOW}[6/10]${NC} Deploying backend..."

# Create directory
mkdir -p /home/mezbon/mezbon-ai
chown mezbon:mezbon /home/mezbon/mezbon-ai

# Copy backend files (assumes you've uploaded them)
echo "Please upload your backend code to /home/mezbon/mezbon-ai/backend"
echo "Press enter when ready..."
read

# Setup Python environment
cd /home/mezbon/mezbon-ai/backend
sudo -u mezbon python3 -m venv venv
sudo -u mezbon venv/bin/pip install --upgrade pip
sudo -u mezbon venv/bin/pip install -r requirements.txt

# Generate secrets
JWT_SECRET=$(openssl rand -hex 32)
JWT_REFRESH_SECRET=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)

# Create .env file
cat > /home/mezbon/mezbon-ai/backend/.env << EOF
DATABASE_URL=postgresql+asyncpg://mezbon:$DB_PASSWORD@localhost:5432/mezbon_prod
DATABASE_URL_SYNC=postgresql://mezbon:$DB_PASSWORD@localhost:5432/mezbon_prod
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=$JWT_SECRET
JWT_REFRESH_SECRET=$JWT_REFRESH_SECRET
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7
ENCRYPTION_KEY=$ENCRYPTION_KEY
GEMINI_API_KEY=AIzaSyDu9_5VhHNrqy9OQo6EbAQB9_aXcLyagtc
GEMINI_MODEL=gemini-2.0-flash
MUXLISA_API_URL=https://service.muxlisa.uz/api/v2
MUXLISA_API_KEY=5aI_jAk8byCqwU5PI4C_Y-az4pxrPif7ttTcGN8A
MUXLISA_MOCK=false
INSIGHTFACE_MODEL=buffalo_l
INSIGHTFACE_DEVICE=cpu
PRINTER_TYPE=network
PRINTER_HOST=$KIOSK_IP
PRINTER_PORT=9100
PAYMENT_MOCK=false
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=https://$KIOSK_DOMAIN,https://$ADMIN_DOMAIN,https://$DOCTOR_DOMAIN
LOG_LEVEL=INFO
EOF

chown mezbon:mezbon /home/mezbon/mezbon-ai/backend/.env

# Run migrations
sudo -u mezbon /home/mezbon/mezbon-ai/backend/venv/bin/alembic upgrade head

################################################################################
# STEP 7: Create Systemd Service
################################################################################

echo ""
echo -e "${YELLOW}[7/10]${NC} Creating systemd service..."

cat > /etc/systemd/system/mezbon-backend.service << EOF
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
EOF

systemctl daemon-reload
systemctl enable mezbon-backend
systemctl start mezbon-backend

################################################################################
# STEP 8: Install Node.js and Build Frontend
################################################################################

echo ""
echo -e "${YELLOW}[8/10]${NC} Installing Node.js and building frontend..."

curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# Build Kiosk UI
cd /home/mezbon/mezbon-ai/kiosk-ui
cat > .env << EOF
VITE_API_URL=https://$API_DOMAIN
VITE_WS_URL=wss://$API_DOMAIN
EOF
sudo -u mezbon npm install
sudo -u mezbon npm run build

# Build Admin Dashboard (if exists)
if [ -d "/home/mezbon/mezbon-ai/admin-dashboard" ]; then
    cd /home/mezbon/mezbon-ai/admin-dashboard
    cat > .env << EOF
VITE_API_URL=https://$API_DOMAIN
EOF
    sudo -u mezbon npm install
    sudo -u mezbon npm run build
fi

################################################################################
# STEP 9: Configure Nginx
################################################################################

echo ""
echo -e "${YELLOW}[9/10]${NC} Configuring Nginx..."

cat > /etc/nginx/sites-available/mezbon << 'EOF'
# Backend API
server {
    listen 80;
    server_name API_DOMAIN;

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

# Kiosk UI - IP restricted
server {
    listen 80;
    server_name KIOSK_DOMAIN;

    allow KIOSK_IP;
    deny all;

    root /home/mezbon/mezbon-ai/kiosk-ui/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}

# Admin Dashboard
server {
    listen 80;
    server_name ADMIN_DOMAIN;

    root /home/mezbon/mezbon-ai/admin-dashboard/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

# Replace placeholders
sed -i "s/API_DOMAIN/$API_DOMAIN/g" /etc/nginx/sites-available/mezbon
sed -i "s/KIOSK_DOMAIN/$KIOSK_DOMAIN/g" /etc/nginx/sites-available/mezbon
sed -i "s/ADMIN_DOMAIN/$ADMIN_DOMAIN/g" /etc/nginx/sites-available/mezbon
sed -i "s/KIOSK_IP/$KIOSK_IP/g" /etc/nginx/sites-available/mezbon

ln -sf /etc/nginx/sites-available/mezbon /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl restart nginx

################################################################################
# STEP 10: Setup SSL with Let's Encrypt
################################################################################

echo ""
echo -e "${YELLOW}[10/10]${NC} Setting up SSL certificates..."
echo "Make sure DNS records are pointing to this server!"
read -p "Press enter to continue with SSL setup..."

certbot --nginx \
    -d $API_DOMAIN \
    -d $KIOSK_DOMAIN \
    -d $ADMIN_DOMAIN \
    --non-interactive \
    --agree-tos \
    --email admin@$DOMAIN

################################################################################
# Security Hardening
################################################################################

echo ""
echo -e "${YELLOW}[BONUS]${NC} Hardening security..."

# Firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Fail2Ban
systemctl enable fail2ban
systemctl start fail2ban

################################################################################
# COMPLETE
################################################################################

echo ""
echo "=================================="
echo -e "${GREEN}✓ DEPLOYMENT COMPLETE!${NC}"
echo "=================================="
echo ""
echo "Your Mezbon AI installation is ready:"
echo ""
echo "  📡 API:    https://$API_DOMAIN"
echo "  🖥️  Kiosk: https://$KIOSK_DOMAIN (IP restricted)"
echo "  👨‍💼 Admin:  https://$ADMIN_DOMAIN"
echo ""
echo "Backend status:"
systemctl status mezbon-backend --no-pager
echo ""
echo "Next steps:"
echo "  1. Configure printer server on kiosk ($KIOSK_IP)"
echo "  2. Test kiosk access from clinic"
echo "  3. Complete booking to test printer"
echo ""
echo "Logs:"
echo "  journalctl -u mezbon-backend -f"
echo ""
echo "Update code:"
echo "  cd /home/mezbon/mezbon-ai && git pull"
echo "  systemctl restart mezbon-backend"
echo ""
