# 🌐 NETWORK PRINTER SETUP GUIDE

## Architecture Overview

```
┌─────────────────┐         Network          ┌──────────────────┐
│  Your Mac       │ ◄─────────────────────► │  Kiosk Machine   │
│  (Backend)      │    Print commands        │  (Printer Host)  │
└─────────────────┘                          └────────┬─────────┘
                                                      │ USB
                                                      ▼
                                              ┌───────────────┐
                                              │ Thermal       │
                                              │ Printer       │
                                              │ VID: 0x4B43   │
                                              │ PID: 0x3830   │
                                              └───────────────┘
```

**You discovered:** The printer is physically connected to the kiosk via USB  
**You need:** Share it over network so your Mac can send print jobs

---

## Option A: Use Print Server Software (RECOMMENDED)

### Step 1: Install Print Server on Kiosk

**Windows (Kiosk) - Using Free Print Server:**

1. **Download Print Server Software**
   - **PrintNode** (Free trial): https://www.printnode.com/
   - **PaperCut Mobility Print** (Free): https://www.papercut.com/
   - **Share-a-Print** (Paid): Alternative option

2. **Install on Kiosk**
   - Run installer on Windows kiosk
   - Configure to start on boot
   - Enable network access

3. **Configure Printer**
   - Add your USB thermal printer
   - Note the network port (usually 9100, 9101)
   - Enable TCP/IP printing

### Step 2: Find Kiosk IP Address

On the kiosk Windows machine:
```cmd
ipconfig
```

Look for: `IPv4 Address: 192.168.x.x`  
Example: `192.168.1.100`

### Step 3: Test Connection from Mac

```bash
# Test if port is open
nc -zv 192.168.1.100 9100

# Expected output:
# Connection to 192.168.1.100 port 9100 [tcp/jetdirect] succeeded!
```

### Step 4: Test Printing from Mac

```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
python3 test_network_printer.py 192.168.1.100
```

### Step 5: Update .env on Mac

```env
PRINTER_TYPE=network
PRINTER_HOST=192.168.1.100  # Your kiosk IP
PRINTER_PORT=9100
```

---

## Option B: Windows Printer Sharing (Built-in)

### On Kiosk (Windows):

1. **Open Control Panel**
   - Search: "Devices and Printers"

2. **Right-click your thermal printer**
   - Select "Printer properties"
   - Go to "Sharing" tab
   - ✅ Check "Share this printer"
   - Share name: "ThermalPrinter"

3. **Enable Network Discovery**
   - Control Panel → Network and Sharing Center
   - Change advanced sharing settings
   - ✅ Turn on network discovery
   - ✅ Turn on file and printer sharing

4. **Configure Firewall**
   - Allow "File and Printer Sharing" through firewall
   - Windows Defender Firewall → Allow an app
   - ✅ Check "File and Printer Sharing"

5. **Get Computer Name**
   ```cmd
   hostname
   ```
   Example: `KIOSK-PC`

### On Mac (Your Development Machine):

1. **Add Network Printer**
   - System Settings → Printers & Scanners
   - Click "+" to add printer
   - Find shared printer from Windows: `\\KIOSK-PC\ThermalPrinter`

2. **Or use IP directly**
   - Protocol: Line Printer Daemon (LPD)
   - Address: `192.168.1.100`
   - Queue: `ThermalPrinter`

---

## Option C: Use Dedicated Print Server Hardware (Production)

For production deployment, consider:

**Network Print Server Device:**
- TP-Link TL-PS110U (~$30)
- Connects USB printer → Ethernet
- Printer becomes network device at fixed IP
- Most reliable for 24/7 operation

**Setup:**
1. Connect printer USB → Print server
2. Connect print server → Network (Ethernet)
3. Configure print server web interface
4. Set static IP (e.g., 192.168.1.50)
5. Enable RAW printing on port 9100

---

## Testing & Troubleshooting

### Test 1: Network Connectivity

```bash
# From Mac, ping kiosk
ping 192.168.1.100

# Expected: Reply from 192.168.1.100: bytes=32 time<10ms
```

### Test 2: Port Accessibility

```bash
# Check if port 9100 is open
nc -zv 192.168.1.100 9100

# OR try telnet
telnet 192.168.1.100 9100
```

If connection succeeds, port is open!

### Test 3: Raw Print Test

```bash
# Send raw data to printer (from Mac)
echo "TEST PRINT" | nc 192.168.1.100 9100
```

If printer prints "TEST PRINT", networking is working!

### Test 4: Python Network Printer

```bash
python3 test_network_printer.py 192.168.1.100
```

Should print formatted queue ticket.

---

## Common Issues

### Issue: "Connection refused"

**Solutions:**
- Firewall blocking port 9100
- Print server not running on kiosk
- Wrong IP address

**Fix:**
```bash
# On kiosk (Windows), check if port is listening:
netstat -an | findstr :9100
```

### Issue: "No route to host"

**Solutions:**
- Mac and kiosk on different networks
- VPN interfering
- WiFi vs Ethernet subnet mismatch

**Fix:**
Ensure both devices on same network segment (e.g., 192.168.1.x)

### Issue: Prints but garbled text

**Solutions:**
- Wrong printer protocol
- Character encoding issue
- Printer doesn't support ESC/POS

**Fix:**
1. Verify printer supports ESC/POS (check manual)
2. Try different character encoding in code
3. Update printer firmware

---

## Production Deployment

### Recommended Setup:

```
┌──────────────┐
│  Backend     │
│  (on Mac or  │
│   Linux VM)  │
└──────┬───────┘
       │
       │ Network
       │
┌──────▼─────────────────────────────┐
│  Kiosk Machine (Windows/Linux)     │
│  ┌──────────────────────────────┐  │
│  │ Print Server Software        │  │
│  │ - Listens on port 9100       │  │
│  │ - Forwards to USB printer    │  │
│  └──────────────────────────────┘  │
│              │ USB                  │
│              ▼                      │
│     ┌────────────────┐              │
│     │ Thermal Printer│              │
│     └────────────────┘              │
└───────────────────────────────────┘
```

### .env Configuration (Mac/Backend):

```env
# Network printer on kiosk
PRINTER_TYPE=network
PRINTER_HOST=192.168.1.100  # Kiosk IP (static recommended)
PRINTER_PORT=9100

# Fallback for testing
# PRINTER_TYPE=file
# PRINTER_OUTPUT_DIR=/tmp/receipts
```

---

## Security Considerations

1. **Firewall Rules**
   - Only allow port 9100 from backend IP
   - Block external access to printer port

2. **Network Segmentation**
   - Put kiosk and backend on private VLAN
   - Isolate from public WiFi

3. **Authentication** (if using PrintNode)
   - Use API keys
   - Rotate keys regularly

---

## Quick Start Checklist

- [ ] Identify kiosk IP address
- [ ] Install print server software on kiosk
- [ ] Configure printer sharing
- [ ] Open firewall port 9100
- [ ] Test with `nc` or `telnet`
- [ ] Test with `test_network_printer.py`
- [ ] Update `.env` with correct IP
- [ ] Restart backend
- [ ] Complete booking flow to test auto-print

---

## Next Steps

1. **Setup printer sharing on kiosk** (Option A recommended)
2. **Find kiosk IP** using `ipconfig`
3. **Test from Mac:**
   ```bash
   python3 test_network_printer.py YOUR_KIOSK_IP
   ```
4. **Update .env:**
   ```env
   PRINTER_HOST=YOUR_KIOSK_IP
   ```
5. **Start backend and test queue ticket printing**

---

**Status:** Waiting for kiosk IP and network configuration  
**Next:** Run `test_network_printer.py` once kiosk is configured
