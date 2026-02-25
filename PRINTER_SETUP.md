# 🖨️ PRINTER SETUP & TESTING GUIDE

## Your Printer Configuration

**Printer Model:** USB Thermal Printer  
**Vendor ID:** `0x4B43`  
**Product ID:** `0x3830`  
**Connection Type:** USB  

---

## ✅ COMPLETED SETUP

1. ✅ Created `printer_service.py` - ESC/POS thermal printer support
2. ✅ Updated `.env` with correct USB VID/PID  
3. ✅ Added `python-escpos` to `requirements.txt`
4. ✅ Created test script `test_printer.py`

---

## 📦 STEP 1: Install Dependencies

```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
pip3 install python-escpos Pillow --break-system-packages
```

This installs:
- `python-escpos` - Thermal printer library
- `Pillow` - Image processing (for logos)

---

## 🧪 STEP 2: Test Printer Connection

### Quick Test (Recommended First)

```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
sudo python3 test_printer.py
```

**Why sudo?** USB device access on macOS requires elevated permissions.

### Expected Output

If successful, you'll see:
```
🖨️  Testing USB Thermal Printer...
==================================================
Vendor ID:  0x4b43
Product ID: 0x3830

Connecting to printer...
✅ Connected successfully!

Printing test receipt...
✅ Test receipt printed successfully!

Check your printer - you should see:
  • Clinic name and address
  • Ticket number K-001 (large)
  • Patient and department info
  • Wait time estimate
  • Footer with timestamp

==================================================

🎉 Printer is ready for use!
```

A physical receipt should print with:
- **NANO MEDICAL** header
- **K-001** ticket number (big)
- Patient info: "Test Patient"
- Department: "Kardiologiya"
- Location: "2-qavat, 201-xona"
- Wait time: "~15 min"
- Timestamp footer

---

## ⚠️ TROUBLESHOOTING

### Problem: "Permission denied" or "Access denied"

**Solution:** Run with sudo
```bash
sudo python3 test_printer.py
```

### Problem: "Device not found"

**Solutions:**
1. Check printer is powered on
2. Check USB cable is connected
3. Verify VID/PID using system tools:
   ```bash
   system_profiler SPUSBDataType
   ```
4. Look for your printer and verify the IDs match:
   - Vendor ID: `0x4B43`
   - Product ID: `0x3830`

### Problem: Printer prints but text is garbled

**Solutions:**
1. Verify printer supports ESC/POS protocol
2. Check printer model documentation
3. Try different character encoding in printer_service.py

### Problem: Paper doesn't cut

Some printers don't support auto-cut. This is normal. Just tear manually.

---

## 🔧 STEP 3: Configure for Production

Your `.env` is already configured for USB mode:

```env
PRINTER_TYPE=usb
PRINTER_VENDOR_ID=0x4B43
PRINTER_PRODUCT_ID=0x3830
```

### Alternative: Network Printer

If you later switch to network printer:
```env
PRINTER_TYPE=network
PRINTER_HOST=192.168.1.100
PRINTER_PORT=9100
```

### Alternative: Testing Mode (No Hardware)

For development without printer:
```env
PRINTER_TYPE=file
PRINTER_OUTPUT_DIR=/tmp/receipts
```

Then check prints:
```bash
cat /tmp/receipts/receipt_*.txt
```

---

## 🚀 STEP 4: Start Backend with Printer

```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
python3 -m app.main
```

The printer service will initialize automatically on startup.

---

## 📝 STEP 5: Test from Kiosk

### Automatic Printing

Queue tickets will **auto-print** when:
1. Patient checks in → Prints queue ticket
2. Booking confirmed → Prints confirmation receipt
3. Payment completed → Prints payment receipt

### Manual Test via API

```bash
# Test printer status
curl http://localhost:8000/api/printer/status

# Expected: {"type": "usb", "status": "configured"}

# Test print
curl -X POST http://localhost:8000/api/printer/test

# Expected: {"success": true}
```

---

## 📄 What Gets Printed

### Queue Ticket Receipt
```
================================
     NANO MEDICAL
  Toshkent, Chilonzor
--------------------------------

    NAVBAT CHIPTASI
    ОЧЕРЕДЬ / QUEUE

         K-001

Bemor / Пациент:
  Alisher Karimov

Bo'lim / Отделение:
  Kardiologiya

Manzil / Адрес:
  2-qavat, 201-xona
  2-этаж, каб. 201

Taxminiy kutish vaqti:
Время ожидания:
      ~15 min

--------------------------------
Iltimos, chiptangizni saqlang
Пожалуйста, сохраните билет
Please keep your ticket

2026-02-24 18:45
Powered by Mezbon AI

[Paper cut]
```

### Booking Confirmation
- Appointment date & time (big)
- Doctor name
- Department
- Service name
- Price

### Payment Receipt
- Payment amount (big)
- Service name
- Payment method
- Confirmation number

---

## 🔍 Monitoring Prints

### Check Print Logs

```bash
cd /Users/aliisroilov/Desktop/AI\ Reception/backend
tail -f logs/mezbon.log | grep -i print
```

You'll see:
```
INFO Printing queue ticket: K-001
INFO Queue ticket printed successfully: K-001
```

### Frontend Status

On the kiosk screen, you'll see toast notifications:
- **Blue:** "Chek chop etilmoqda..." (Printing...)
- **Green:** "Chek chop etildi" (Printed successfully)
- **Red:** "Chop etishda xato" (Print error)

---

## 🎨 Customization

### Add Clinic Logo

1. Prepare logo image:
   - Format: PNG, JPG, or GIF
   - Size: 384 pixels wide (printer width)
   - Monochrome recommended for best results

2. Save to backend:
   ```bash
   cp /path/to/logo.png /Users/aliisroilov/Desktop/AI\ Reception/backend/assets/clinic_logo.png
   ```

3. Update `.env`:
   ```env
   RECEIPT_LOGO_PATH=/Users/aliisroilov/Desktop/AI Reception/backend/assets/clinic_logo.png
   ```

4. Logo will appear at top of all receipts

### Change Clinic Info

Edit `printer_service.py`, update default values:
```python
clinic_name="NANO MEDICAL CLINIC"  # Your clinic name
clinic_address="Toshkent, Chilonzor tumani"  # Your address
```

Or pass dynamically from database when printing.

---

## 🐛 Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Nothing prints | Wrong VID/PID | Verify with `system_profiler SPUSBDataType` |
| Garbled text | Wrong encoding | Printer may not support UTF-8 fully |
| Paper jam | Low paper | Refill thermal paper roll |
| Slow printing | Large logo | Compress logo image |
| Connection lost | USB unplugged | Reconnect and restart backend |

---

## ✅ Success Checklist

- [ ] Dependencies installed (`python-escpos`, `Pillow`)
- [ ] `.env` configured with correct VID/PID
- [ ] Test script prints successfully
- [ ] Backend starts without printer errors
- [ ] API test endpoint returns success
- [ ] Kiosk auto-prints queue tickets
- [ ] Receipts have correct Uzbek/Russian text
- [ ] Print status shows on kiosk UI
- [ ] Paper cuts cleanly (if supported)

---

## 🎯 Next Steps

1. Run the test: `sudo python3 test_printer.py`
2. If successful, start backend: `python3 -m app.main`
3. Test from kiosk by completing booking flow
4. Monitor logs for print confirmations

---

## 📞 Support

**Printer Issues:**
- Check printer manual for ESC/POS compatibility
- Verify USB connection
- Try different USB port
- Update printer firmware

**Code Issues:**
- Check logs: `tail -f logs/mezbon.log`
- Test printer service directly in Python shell
- Verify Socket.IO events are firing

---

**Status:** ✅ Ready to test  
**Last Updated:** 2026-02-24  
**Configuration:** USB Thermal Printer (VID: 0x4B43, PID: 0x3830)
