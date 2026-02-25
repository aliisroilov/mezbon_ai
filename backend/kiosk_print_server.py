#!/usr/bin/env python3
"""
Simple Print Server for Windows Kiosk
Receives print jobs over network (port 9100) and forwards to USB printer
Run this on the kiosk machine where printer is connected
"""

import socket
import threading
from escpos.printer import Usb

# Your printer's USB IDs
VENDOR_ID = 0x4B43
PRODUCT_ID = 0x3830

# Network settings
HOST = '0.0.0.0'  # Listen on all network interfaces
PORT = 9100

class PrintServer:
    def __init__(self):
        self.printer = None
        self.init_printer()
        
    def init_printer(self):
        """Initialize USB printer connection"""
        try:
            self.printer = Usb(VENDOR_ID, PRODUCT_ID)
            print(f"✅ USB Printer connected (VID:{hex(VENDOR_ID)}, PID:{hex(PRODUCT_ID)})")
        except Exception as e:
            print(f"❌ Failed to connect to printer: {e}")
            print("Make sure printer is connected via USB")
            exit(1)
    
    def handle_client(self, client_socket, address):
        """Handle incoming print job"""
        print(f"📥 Connection from {address}")
        
        try:
            # Receive print data
            data = b''
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
            
            if data:
                # Send to USB printer
                print(f"🖨️  Printing {len(data)} bytes...")
                self.printer._raw(data)
                print(f"✅ Print job completed from {address}")
            
        except Exception as e:
            print(f"❌ Error handling client {address}: {e}")
        
        finally:
            client_socket.close()
    
    def start(self):
        """Start print server"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(5)
        
        print("=" * 60)
        print("🖨️  THERMAL PRINTER SERVER")
        print("=" * 60)
        print(f"Listening on {HOST}:{PORT}")
        print(f"USB Printer: VID:{hex(VENDOR_ID)}, PID:{hex(PRODUCT_ID)}")
        print("\n✅ Server ready! Send print jobs to this machine's IP on port 9100")
        print(f"Example: echo 'TEST' | nc {self.get_local_ip()} {PORT}")
        print("\nPress Ctrl+C to stop server")
        print("=" * 60)
        print()
        
        try:
            while True:
                client, address = server.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client, address)
                )
                client_thread.daemon = True
                client_thread.start()
        
        except KeyboardInterrupt:
            print("\n\n🛑 Server stopped")
            server.close()
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"

if __name__ == "__main__":
    print("\n🚀 Starting Thermal Printer Server...\n")
    server = PrintServer()
    server.start()
