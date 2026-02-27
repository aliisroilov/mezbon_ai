#!/usr/bin/env python3
"""
Mezbon Kiosk Print Proxy
=========================
A lightweight HTTP server that runs on the KIOSK MACHINE (not the cloud server).
Receives print requests from the browser frontend and sends ESC/POS commands
directly to the thermal printer.

Usage:
  python mezbon_print_proxy.py

The proxy listens on http://localhost:9111 and accepts POST /print requests.
It connects to the thermal printer at PRINTER_HOST:PRINTER_PORT via TCP.

Requirements:
  pip install python-escpos

Configuration (environment variables):
  PRINTER_HOST  - Thermal printer IP (default: 10.99.0.184)
  PRINTER_PORT  - Thermal printer port (default: 9100)
  PROXY_PORT    - HTTP server port (default: 9111)
"""

import json
import os
import socket
import struct
import sys
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Configuration ────────────────────────────────────────
PRINTER_HOST = os.environ.get("PRINTER_HOST", "10.99.0.184")
PRINTER_PORT = int(os.environ.get("PRINTER_PORT", "9100"))
PROXY_PORT = int(os.environ.get("PROXY_PORT", "9111"))

# ── ESC/POS Commands ────────────────────────────────────
ESC = b'\x1b'
GS = b'\x1d'
INIT = ESC + b'\x40'           # Initialize printer
CUT = GS + b'\x56\x00'        # Full cut
ALIGN_CENTER = ESC + b'\x61\x01'
ALIGN_LEFT = ESC + b'\x61\x00'
BOLD_ON = ESC + b'\x45\x01'
BOLD_OFF = ESC + b'\x45\x00'
DOUBLE_ON = GS + b'\x21\x11'  # Double width + double height
DOUBLE_OFF = GS + b'\x21\x00'
FEED = ESC + b'\x64\x03'      # Feed 3 lines
UNDERLINE_ON = ESC + b'\x2d\x01'
UNDERLINE_OFF = ESC + b'\x2d\x00'
FONT_B = ESC + b'\x4d\x01'    # Small font
FONT_A = ESC + b'\x4d\x00'    # Normal font


def encode_text(text: str) -> bytes:
    """Encode text for thermal printer (UTF-8 with fallback to latin-1)."""
    try:
        return text.encode('cp866')  # Cyrillic support
    except UnicodeEncodeError:
        try:
            return text.encode('utf-8')
        except:
            return text.encode('latin-1', errors='replace')


def build_queue_ticket(data: dict) -> bytes:
    """Build ESC/POS binary data for a queue ticket."""
    buf = bytearray()
    buf += INIT

    # ── Header ──
    buf += ALIGN_CENTER
    buf += BOLD_ON
    buf += encode_text("MEZBON CLINIC\n")
    buf += BOLD_OFF
    buf += encode_text("─" * 32 + "\n")

    # ── Ticket Number (large) ──
    buf += ALIGN_CENTER
    buf += encode_text("NAVBAT RAQAMI\n\n")
    buf += DOUBLE_ON
    buf += BOLD_ON
    ticket_number = data.get("ticketNumber", "---")
    buf += encode_text(f"  {ticket_number}  \n")
    buf += BOLD_OFF
    buf += DOUBLE_OFF
    buf += encode_text("\n")
    buf += encode_text("─" * 32 + "\n")

    # ── Details ──
    buf += ALIGN_LEFT

    dept = data.get("departmentName", "")
    if dept:
        buf += BOLD_ON
        buf += encode_text(f"Bo'lim:   {dept}\n")
        buf += BOLD_OFF

    doctor = data.get("doctorName", "")
    if doctor:
        buf += encode_text(f"Shifokor: {doctor}\n")

    date_str = data.get("date", "")
    if date_str:
        buf += encode_text(f"Sana:     {date_str}\n")

    time_str = data.get("time", "")
    if time_str:
        buf += BOLD_ON
        buf += encode_text(f"Vaqt:     {time_str}\n")
        buf += BOLD_OFF

    room = data.get("roomNumber", "")
    floor = data.get("floor", "")
    if room:
        room_text = ""
        if floor:
            room_text = f"{floor}-qavat, "
        room_text += f"{room}-xona"
        buf += BOLD_ON
        buf += encode_text(f"Xona:     {room_text}\n")
        buf += BOLD_OFF

    wait = data.get("estimatedWait", 0)
    if wait:
        buf += encode_text(f"Kutish:   ~{wait} daqiqa\n")

    buf += encode_text("─" * 32 + "\n")

    # ── Footer ──
    buf += ALIGN_CENTER
    buf += FONT_B
    buf += encode_text("Navbatingiz ekranda e'lon\n")
    buf += encode_text("qilinadi. Iltimos, kutish\n")
    buf += encode_text("zonasida kuting.\n")
    buf += FONT_A
    buf += encode_text("─" * 32 + "\n")

    # ── Timestamp ──
    buf += FONT_B
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    buf += encode_text(f"{now}\n")
    buf += FONT_A

    # ── Feed & Cut ──
    buf += FEED
    buf += CUT

    return bytes(buf)


def send_to_printer(data: bytes) -> bool:
    """Send raw ESC/POS data to the thermal printer via TCP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((PRINTER_HOST, PRINTER_PORT))
        sock.sendall(data)
        sock.close()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send to printer {PRINTER_HOST}:{PRINTER_PORT}: {e}")
        return False


class PrintHandler(BaseHTTPRequestHandler):
    """HTTP request handler for print requests."""

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Health check endpoint."""
        if self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "printer": f"{PRINTER_HOST}:{PRINTER_PORT}",
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle print request."""
        if self.path != "/print":
            self.send_response(404)
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)

            print(f"[PRINT] Received: type={data.get('type', '?')}, ticket={data.get('ticketNumber', '?')}")

            # Build ESC/POS data
            receipt_type = data.get("type", "queue_ticket")
            if receipt_type == "queue_ticket":
                escpos_data = build_queue_ticket(data)
            else:
                # Default to queue ticket format
                escpos_data = build_queue_ticket(data)

            # Send to printer
            success = send_to_printer(escpos_data)

            # Respond
            self.send_response(200 if success else 502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": success,
                "message": "Printed" if success else "Failed to reach printer",
            }).encode())

            if success:
                print(f"[PRINT] ✅ Ticket {data.get('ticketNumber', '?')} printed successfully")
            else:
                print(f"[PRINT] ❌ Failed to print ticket {data.get('ticketNumber', '?')}")

        except Exception as e:
            print(f"[ERROR] {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "message": str(e),
            }).encode())

    def log_message(self, format, *args):
        """Suppress default HTTP logging (we have custom logging)."""
        pass


def main():
    print("=" * 50)
    print("  MEZBON KIOSK PRINT PROXY")
    print("=" * 50)
    print(f"  Proxy:   http://localhost:{PROXY_PORT}")
    print(f"  Printer: {PRINTER_HOST}:{PRINTER_PORT}")
    print("=" * 50)
    print()
    print("  Endpoints:")
    print(f"    POST http://localhost:{PROXY_PORT}/print  — Print a ticket")
    print(f"    GET  http://localhost:{PROXY_PORT}/health  — Health check")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    print()

    server = HTTPServer(("127.0.0.1", PROXY_PORT), PrintHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] Print proxy stopped")
        server.server_close()


if __name__ == "__main__":
    main()
