"""
Thermal Printer Service - python-escpos 3.x compatible
Handles ESC/POS thermal printer integration for queue tickets, receipts, and confirmations.
Supports USB and Network thermal printers common in Uzbekistan clinics.
"""

import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from escpos.printer import Usb, Network, File, Dummy
from loguru import logger
from PIL import Image


class PrinterType(str, Enum):
    """Supported printer types"""
    USB = "usb"
    NETWORK = "network"
    FILE = "file"  # For testing - prints to file
    DUMMY = "dummy"  # For testing - no output


class ReceiptType(str, Enum):
    """Types of receipts that can be printed"""
    QUEUE_TICKET = "queue_ticket"
    BOOKING_CONFIRMATION = "booking_confirmation"
    PAYMENT_RECEIPT = "payment_receipt"
    CHECK_IN_CONFIRMATION = "check_in_confirmation"


class PrinterService:
    """
    Service for printing receipts on thermal printers.
    Uses ESC/POS protocol compatible with most thermal printers.
    
    Compatible with python-escpos 3.x API
    """

    def __init__(self):
        self.printer_type = os.getenv("PRINTER_TYPE", "file")
        self.printer = self._initialize_printer()
        self.logo_path = os.getenv("RECEIPT_LOGO_PATH")

    def _initialize_printer(self):
        """Initialize printer based on configuration"""
        try:
            if self.printer_type == PrinterType.USB:
                # Common thermal printer vendor IDs (Epson, Star, etc.)
                vendor_id = int(os.getenv("PRINTER_VENDOR_ID", "0x04b8"), 16)
                product_id = int(os.getenv("PRINTER_PRODUCT_ID", "0x0e15"), 16)
                return Usb(vendor_id, product_id)

            elif self.printer_type == PrinterType.NETWORK:
                host = os.getenv("PRINTER_HOST", "192.168.1.100")
                port = int(os.getenv("PRINTER_PORT", "9100"))
                return Network(host, port)

            elif self.printer_type == PrinterType.FILE:
                # For testing - print to file
                output_dir = os.getenv("PRINTER_OUTPUT_DIR", "/tmp/receipts")
                os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = os.path.join(output_dir, f"receipt_{timestamp}.txt")
                return File(filepath)

            else:  # DUMMY
                return Dummy()

        except Exception as e:
            logger.error(f"Failed to initialize printer: {e}")
            # Fallback to dummy printer
            return Dummy()

    def _print_header(self, clinic_name: str, clinic_address: str = ""):
        """Print receipt header with clinic info"""
        try:
            # Logo if available
            if self.logo_path and os.path.exists(self.logo_path):
                try:
                    logo = Image.open(self.logo_path)
                    self.printer.image(logo, center=True)
                except Exception as e:
                    logger.warning(f"Failed to print logo: {e}")

            # Clinic name (big and bold)
            self.printer.set(align="center", bold=True, double_width=True, double_height=True)
            self.printer.text(f"{clinic_name}\n")
            self.printer.set(bold=False, double_width=False, double_height=False)

            # Address
            if clinic_address:
                self.printer.set(align="center")
                self.printer.text(f"{clinic_address}\n")

            # Separator
            self.printer.text("-" * 32 + "\n")

        except Exception as e:
            logger.error(f"Failed to print header: {e}")

    def _print_footer(self):
        """Print receipt footer"""
        try:
            self.printer.text("-" * 32 + "\n")
            self.printer.set(align="center")
            self.printer.text(f"Iltimos, chiptangizni saqlang\n")
            self.printer.text(f"Пожалуйста, сохраните билет\n")
            self.printer.text(f"Please keep your ticket\n\n")
            self.printer.text(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            self.printer.text("Powered by Mezbon AI\n\n")

            # Cut paper
            self.printer.cut()

        except Exception as e:
            logger.error(f"Failed to print footer: {e}")

    def print_queue_ticket(
        self,
        ticket_number: str,
        patient_name: str,
        department_name: str,
        floor: int,
        room: str,
        estimated_wait: int,
        doctor_name: Optional[str] = None,
        clinic_name: str = "NANO MEDICAL CLINIC",
        clinic_address: str = "Toshkent, Chilonzor tumani",
    ) -> bool:
        """Print queue ticket receipt"""
        try:
            logger.info(f"Printing queue ticket: {ticket_number}")

            self._print_header(clinic_name, clinic_address)

            # Title
            self.printer.set(align="center", bold=True)
            self.printer.text("NAVBAT CHIPTASI\n")
            self.printer.text("ОЧЕРЕДЬ / QUEUE\n\n")
            self.printer.set(bold=False)

            # Ticket number (BIG)
            self.printer.set(align="center", bold=True, double_width=True, double_height=True)
            self.printer.text(f"{ticket_number}\n\n")
            self.printer.set(bold=False, double_width=False, double_height=False)

            # Patient info
            self.printer.set(align="left")
            self.printer.text(f"Bemor / Пациент:\n")
            self.printer.set(bold=True)
            self.printer.text(f"  {patient_name}\n\n")
            self.printer.set(bold=False)

            # Department
            self.printer.text(f"Bo'lim / Отделение:\n")
            self.printer.set(bold=True)
            self.printer.text(f"  {department_name}\n\n")
            self.printer.set(bold=False)

            # Doctor if available
            if doctor_name:
                self.printer.text(f"Shifokor / Врач:\n")
                self.printer.set(bold=True)
                self.printer.text(f"  {doctor_name}\n\n")
                self.printer.set(bold=False)

            # Location
            self.printer.text(f"Manzil / Адрес:\n")
            self.printer.set(bold=True)
            self.printer.text(f"  {floor}-qavat, {room}-xona\n")
            self.printer.text(f"  {floor}-этаж, каб. {room}\n\n")
            self.printer.set(bold=False)

            # Wait time
            self.printer.set(align="center")
            self.printer.text(f"Taxminiy kutish vaqti:\n")
            self.printer.text(f"Время ожидания:\n")
            self.printer.set(bold=True, double_width=True, double_height=True)
            self.printer.text(f"~{estimated_wait} min\n\n")
            self.printer.set(bold=False, double_width=False, double_height=False)

            self._print_footer()

            logger.info(f"Queue ticket printed successfully: {ticket_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to print queue ticket: {e}")
            return False

    def print_booking_confirmation(
        self,
        booking_id: uuid.UUID,
        patient_name: str,
        department_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str,
        service_name: str,
        price: float,
        clinic_name: str = "NANO MEDICAL CLINIC",
        clinic_address: str = "Toshkent, Chilonzor tumani",
    ) -> bool:
        """Print booking confirmation receipt"""
        try:
            logger.info(f"Printing booking confirmation: {booking_id}")

            self._print_header(clinic_name, clinic_address)

            # Title
            self.printer.set(align="center", bold=True)
            self.printer.text("TASDIQLASH\n")
            self.printer.text("ПОДТВЕРЖДЕНИЕ\n")
            self.printer.text("CONFIRMATION\n\n")
            self.printer.set(bold=False)

            # Booking ID
            self.printer.set(align="center")
            self.printer.text(f"ID: {str(booking_id)[:8]}\n\n")

            # Patient
            self.printer.set(align="left")
            self.printer.text(f"Bemor / Пациент:\n")
            self.printer.set(bold=True)
            self.printer.text(f"  {patient_name}\n\n")
            self.printer.set(bold=False)

            # Appointment details
            self.printer.text(f"Sana / Дата:\n")
            self.printer.set(bold=True)
            self.printer.text(f"  {appointment_date}\n\n")
            self.printer.set(bold=False)

            self.printer.text(f"Vaqt / Время:\n")
            self.printer.set(bold=True, double_width=True, double_height=True)
            self.printer.text(f"  {appointment_time}\n\n")
            self.printer.set(bold=False, double_width=False, double_height=False)

            # Doctor & Department
            self.printer.text(f"Shifokor / Врач:\n")
            self.printer.set(bold=True)
            self.printer.text(f"  {doctor_name}\n")
            self.printer.set(bold=False)
            self.printer.text(f"  {department_name}\n\n")

            # Service
            self.printer.text(f"Xizmat / Услуга:\n")
            self.printer.set(bold=True)
            self.printer.text(f"  {service_name}\n\n")
            self.printer.set(bold=False)

            # Price
            self.printer.text(f"Narx / Цена:\n")
            self.printer.set(bold=True, double_width=True, double_height=True)
            self.printer.text(f"  {price:,.0f} so'm\n\n")
            self.printer.set(bold=False, double_width=False, double_height=False)

            # Important note
            self.printer.set(align="center")
            self.printer.text("="*32 + "\n")
            self.printer.text("Iltimos, vaqtida keling!\n")
            self.printer.text("Пожалуйста, приходите вовремя!\n")
            self.printer.text("="*32 + "\n\n")

            self._print_footer()

            logger.info(f"Booking confirmation printed: {booking_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to print booking confirmation: {e}")
            return False

    def print_payment_receipt(
        self,
        payment_id: uuid.UUID,
        patient_name: str,
        amount: float,
        payment_method: str,
        service_name: str,
        clinic_name: str = "NANO MEDICAL CLINIC",
        clinic_address: str = "Toshkent, Chilonzor tumani",
    ) -> bool:
        """Print payment receipt"""
        try:
            logger.info(f"Printing payment receipt: {payment_id}")

            self._print_header(clinic_name, clinic_address)

            # Title
            self.printer.set(align="center", bold=True)
            self.printer.text("TO'LOV CHEKI\n")
            self.printer.text("ЧЕК ОПЛАТЫ\n")
            self.printer.text("PAYMENT RECEIPT\n\n")
            self.printer.set(bold=False)

            # Receipt number
            self.printer.set(align="center")
            self.printer.text(f"№ {str(payment_id)[:8]}\n\n")

            # Patient
            self.printer.set(align="left")
            self.printer.text(f"Bemor / Пациент:\n")
            self.printer.set(bold=True)
            self.printer.text(f"  {patient_name}\n\n")
            self.printer.set(bold=False)

            # Service
            self.printer.text(f"Xizmat / Услуга:\n")
            self.printer.set(bold=True)
            self.printer.text(f"  {service_name}\n\n")
            self.printer.set(bold=False)

            # Amount (BIG)
            self.printer.text(f"Summa / Сумма:\n")
            self.printer.set(bold=True, double_width=True, double_height=True, align="center")
            self.printer.text(f"{amount:,.0f}\n")
            self.printer.set(bold=False, double_width=False, double_height=False, align="center")
            self.printer.text(f"so'm / сум\n\n")

            # Payment method
            self.printer.set(align="left")
            self.printer.text(f"To'lov usuli / Способ:\n")
            self.printer.set(bold=True)
            self.printer.text(f"  {payment_method}\n\n")
            self.printer.set(bold=False)

            # Status
            self.printer.set(align="center", bold=True)
            self.printer.text("✓ TO'LANDI / ОПЛАЧЕНО ✓\n\n")
            self.printer.set(bold=False)

            self._print_footer()

            logger.info(f"Payment receipt printed: {payment_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to print payment receipt: {e}")
            return False

    def test_print(self) -> bool:
        """Print test receipt to verify printer connection"""
        try:
            self.printer.set(align="center", bold=True, double_width=True, double_height=True)
            self.printer.text("TEST PRINT\n")
            self.printer.text("PRINTER OK\n\n")
            self.printer.set(bold=False, double_width=False, double_height=False)
            self.printer.text(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            self.printer.cut()
            logger.info("Test print successful")
            return True
        except Exception as e:
            logger.error(f"Test print failed: {e}")
            return False


# Singleton instance
_printer_service: Optional[PrinterService] = None


def get_printer_service() -> PrinterService:
    """Get or create printer service singleton"""
    global _printer_service
    if _printer_service is None:
        _printer_service = PrinterService()
    return _printer_service
