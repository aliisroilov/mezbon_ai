@echo off
title Mezbon Kiosk Print Proxy
echo.
echo Starting Mezbon Print Proxy...
echo Printer: 10.99.0.184:9100
echo.

set PRINTER_HOST=10.99.0.184
set PRINTER_PORT=9100
set PROXY_PORT=9111

python mezbon_print_proxy.py

pause
