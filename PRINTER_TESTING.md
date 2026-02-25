# Printer Testing Guide

## Setup for Testing (File Mode)

1. Ensure `.env` has:
```
PRINTER_TYPE=file
PRINTER_OUTPUT_DIR=/tmp/receipts
```

2. Start backend:
```bash
cd backend
uvicorn app.main:application --reload --port 8000
```

3. Check prints in:
```bash
ls -la /tmp/receipts/
cat /tmp/receipts/receipt_*.txt
```

## Setup for Production (USB Printer)

1. Connect USB thermal printer
2. Find vendor/product ID:
```bash
lsusb
```
3. Update `.env`:
```
PRINTER_TYPE=usb
PRINTER_VENDOR_ID=0x04b8
PRINTER_PRODUCT_ID=0x0e15
```

## Setup for Network Printer

1. Get printer IP address
2. Update `.env`:
```
PRINTER_TYPE=network
PRINTER_HOST=192.168.1.100
PRINTER_PORT=9100
```

## Test API Endpoints

```bash
# Test printer connection
curl -X POST http://localhost:8000/api/v1/printer/test

# Get printer status
curl http://localhost:8000/api/v1/printer/status

# Print a test ticket
curl -X POST http://localhost:8000/api/v1/printer/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticketNumber": "K-001",
    "departmentName": "Kardiologiya",
    "doctorName": "Dr. Malikov",
    "date": "2026-02-25",
    "time": "10:30",
    "roomNumber": "205",
    "floor": 2,
    "estimatedWait": 15
  }'
```

## Troubleshooting

**Printer not found:**
- Check USB connection
- Verify vendor/product IDs with `lsusb`
- Check permissions: `sudo usermod -a -G lp $USER`

**Network printer timeout:**
- Ping printer IP: `ping 192.168.1.100`
- Check firewall rules
- Verify port 9100 is open: `nc -zv 192.168.1.100 9100`

**Print garbled:**
- Verify printer supports ESC/POS
- Check character encoding (UTF-8 required for Cyrillic/Latin)
- Update printer firmware

**File mode not writing:**
- Check output directory exists and is writable
- Verify `PRINTER_OUTPUT_DIR` path in `.env`
