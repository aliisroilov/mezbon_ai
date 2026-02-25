# 🚀 MEZBON AI - CONTABO DEPLOYMENT GUIDE

## Server Details

**Recommended:** Cloud VPS S  
**Cost:** €4.50/month (~$5)  
**Specs:**
- 4GB RAM
- 100GB NVMe SSD  
- 4 vCPU cores
- Unlimited traffic
- Ubuntu 22.04 LTS

**Location:** EU West (Germany) - Best latency to Uzbekistan

---

## STEP-BY-STEP DEPLOYMENT

### 1. Order Contabo Server (5 min)

1. Go to https://contabo.com/en/vps/
2. Select **Cloud VPS S** - €4.50/month
3. Choose:
   - **Region**: EU West (Germany)
   - **Operating System**: Ubuntu 22.04
   - **Storage**: NVMe SSD (default)
4. Add your SSH public key (recommended)
5. Complete payment

### 2. Receive Server Credentials (5 min)

Check your email for:
```
Server IP: X.X.X.X
Username: root
Password: YourPassword
```

**Save these!** You'll need them.

### 3. First Login

From your Mac terminal:

```bash
ssh root@YOUR_SERVER_IP
# Enter password when prompted
```

**On first login:**
```bash
# Update password (optional but recommended)
passwd

# Update system
apt update && apt upgrade -y
```

### 4. Upload Your Code to Contabo

**Option A: Using Git (Recommended)**

On server:
```bash
cd /root
git clone YOUR_GITHUB_REPO_URL mezbon-ai
```

**Option B: Using SCP from Mac**

From your Mac:
```bash
# Compress your project
cd /Users/aliisroilov/Desktop/AI\ Reception
tar -czf mezbon-ai.tar.gz backend kiosk-ui admin-dashboard

# Upload to Contabo
scp mezbon-ai.tar.gz root@YOUR_SERVER_IP:/root/

# On server, extract
ssh root@YOUR_SERVER_IP
cd /root
tar -xzf mezbon-ai.tar.gz
```

### 5. Run Automated Deployment

**Copy the deployment script to server:**

From Mac:
```bash
scp deploy.sh root@YOUR_SERVER_IP:/root/mezbon-ai/
```

**On server, run deployment:**
```bash
ssh root@YOUR_SERVER_IP
cd /root/mezbon-ai
chmod +x deploy.sh
./deploy.sh
```

**The script will ask you:**
1. Domain name (e.g., mezbon.uz)
2. Database password (create a strong one)
3. Kiosk IP (10.99.0.184)

Then it automatically:
- ✅ Installs all dependencies
- ✅ Configures PostgreSQL
- ✅ Sets up backend service
- ✅ Builds frontend
- ✅ Configures Nginx
- ✅ Installs SSL certificates
- ✅ Hardens security

**Duration:** ~30 minutes

### 6. Configure DNS

While deployment runs, point your domain to Contabo:

**DNS Records (at your domain registrar):**
```
Type  Name     Value              TTL
A     api      YOUR_SERVER_IP     300
A     kiosk    YOUR_SERVER_IP     300
A     admin    YOUR_SERVER_IP     300
A     doctor   YOUR_SERVER_IP     300
```

**Example with Contabo IP:**
```
A     api      203.0.113.45       300
A     kiosk    203.0.113.45       300
A     admin    203.0.113.45       300
A     doctor   203.0.113.45       300
```

**Wait 5-10 minutes for DNS propagation.**

### 7. Verify Deployment

**Test backend:**
```bash
curl https://api.mezbon.uz/health
# Expected: {"status": "healthy"}
```

**Test frontend:**
```bash
curl -I https://kiosk.mezbon.uz
# Expected: HTTP/2 200
```

**Check backend logs:**
```bash
journalctl -u mezbon-backend -f
```

### 8. Setup Kiosk Print Server

On your kiosk (10.99.0.184):

```cmd
# Install Python if not already
# Download from python.org

# Install dependency
pip install python-escpos

# Copy kiosk_print_server.py to desktop

# Run it
python kiosk_print_server.py

# Should show:
# ✅ USB Printer connected
# Listening on 0.0.0.0:9100
```

**Add to Windows startup:**
1. Press `Win + R`
2. Type `shell:startup`
3. Create shortcut to `python kiosk_print_server.py`

### 9. Test End-to-End

**From server, test printer:**
```bash
cd /root/mezbon-ai/backend
source venv/bin/activate
python3 test_network_printer.py 10.99.0.184
```

**Physical receipt should print on kiosk!** 🎉

**Test from kiosk browser:**
1. Open Chrome on kiosk
2. Go to: `https://kiosk.mezbon.uz`
3. Complete a booking
4. Receipt should auto-print!

---

## 🔧 CONTABO-SPECIFIC CONFIGURATION

### Firewall (UFW)

Already configured by deployment script:
```bash
ufw status
# Should show:
# 22/tcp  ALLOW  # SSH
# 80/tcp  ALLOW  # HTTP
# 443/tcp ALLOW  # HTTPS
```

### Backups

Contabo offers backup add-on:
- **€2/month** - Daily backups
- **Recommended** for production

Enable in Contabo Control Panel → Your VPS → Backups

### Monitoring

View server resources:
```bash
# CPU & Memory
htop

# Disk usage
df -h

# Backend logs
journalctl -u mezbon-backend -f
```

### Updates

**Code updates:**
```bash
cd /root/mezbon-ai
git pull
systemctl restart mezbon-backend
```

**System updates:**
```bash
apt update && apt upgrade -y
```

---

## 💡 CONTABO TIPS

### Performance Optimization

Contabo NVMe is very fast, but optimize PostgreSQL:

Edit `/etc/postgresql/14/main/postgresql.conf`:
```ini
shared_buffers = 1GB          # 25% of RAM
effective_cache_size = 3GB    # 75% of RAM
work_mem = 16MB
maintenance_work_mem = 256MB
```

Restart PostgreSQL:
```bash
systemctl restart postgresql
```

### Security Best Practices

1. **Change default SSH port** (optional):
   ```bash
   # Edit /etc/ssh/sshd_config
   Port 2222  # Instead of 22
   
   # Update firewall
   ufw allow 2222/tcp
   ufw delete allow 22/tcp
   
   systemctl restart sshd
   ```

2. **Disable root SSH login:**
   ```bash
   # Create admin user first
   adduser admin
   usermod -aG sudo admin
   
   # Edit /etc/ssh/sshd_config
   PermitRootLogin no
   
   systemctl restart sshd
   ```

3. **Setup Fail2Ban:**
   Already installed by deploy.sh
   ```bash
   systemctl status fail2ban
   ```

### Monitoring & Alerts

**Install monitoring:**
```bash
apt install -y netdata
systemctl enable netdata
systemctl start netdata
```

Access at: `http://YOUR_SERVER_IP:19999`

---

## 📊 COST BREAKDOWN (Contabo)

| Item | Cost/Month |
|------|------------|
| Contabo Cloud VPS S | €4.50 |
| Domain (.uz or .com) | ~$1 |
| SSL Certificates | FREE |
| Backups (optional) | €2 |
| **TOTAL** | **~€6.50 (~$7)** |

**Per clinic:** €0 extra (one server serves unlimited kiosks!)

---

## 🐛 TROUBLESHOOTING

### Issue: Can't SSH to Contabo

**Check:**
1. IP address correct?
2. Firewall allows SSH (port 22)?
3. Server status in Contabo panel?

**Solution:**
- Use Contabo VNC console (in control panel)
- Check firewall: `ufw status`

### Issue: Slow performance

**Check:**
```bash
# CPU usage
top

# Memory
free -h

# Disk I/O
iostat
```

**Solution:**
- Upgrade to Cloud VPS M (6GB RAM) if needed
- Optimize database queries
- Enable caching

### Issue: Can't connect to printer

**Check from server:**
```bash
nc -zv 10.99.0.184 9100
```

**If fails:**
1. Print server running on kiosk?
2. Firewall on kiosk allows port 9100?
3. Network connection stable?

---

## 🎯 POST-DEPLOYMENT CHECKLIST

- [ ] Server accessible via SSH
- [ ] DNS records pointing to server
- [ ] Backend running: `systemctl status mezbon-backend`
- [ ] SSL certificates installed
- [ ] Kiosk UI accessible from kiosk only
- [ ] Admin dashboard accessible from anywhere
- [ ] Print server running on kiosk
- [ ] Test print successful
- [ ] End-to-end booking test completed
- [ ] Backups configured
- [ ] Monitoring setup

---

## 📞 CONTABO SUPPORT

**If you need help:**
- Contabo Support: support@contabo.com
- Control Panel: https://my.contabo.com
- Documentation: https://docs.contabo.com

**For Mezbon AI issues:**
- Backend logs: `journalctl -u mezbon-backend -f`
- Nginx logs: `/var/log/nginx/error.log`

---

## 🚀 QUICK START COMMANDS

**After Contabo server is ready:**

```bash
# 1. SSH to server
ssh root@YOUR_SERVER_IP

# 2. Upload code (via git or scp)
git clone YOUR_REPO mezbon-ai

# 3. Run deployment
cd mezbon-ai
chmod +x deploy.sh
./deploy.sh

# 4. Monitor deployment
journalctl -u mezbon-backend -f

# 5. Test
curl https://api.mezbon.uz/health
```

**That's it!** 🎉

---

## ✅ READY TO DEPLOY

1. **Order Contabo Cloud VPS S** → 5 min
2. **Get server IP from email** → 5 min
3. **Run deployment script** → 30 min
4. **Setup kiosk printer** → 10 min
5. **Test & launch!** → 10 min

**Total: ~1 hour** ⚡

---

**Questions?** Everything is automated. Just run `deploy.sh` and you're good! 🚀
