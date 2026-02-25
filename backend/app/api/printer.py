"""Printer management API endpoints.

Provides test and status endpoints for the thermal printer.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from app.services.printer_service import get_printer_service

router = APIRouter(prefix="/printer", tags=["printer"])


class TicketPrintRequest(BaseModel):
    ticketNumber: str
    departmentName: str
    doctorName: str | None = None
    date: str
    time: str | None = None
    roomNumber: str | None = None
    floor: int | None = None
    estimatedWait: int | None = None


@router.post("/test")
async def test_printer() -> dict[str, bool]:
    """Test printer connection by printing a test receipt."""
    try:
        printer = get_printer_service()
        success = printer.test_print()
        return {"success": success}
    except Exception as e:
        logger.error(f"Printer test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_printer_status() -> dict[str, str]:
    """Get printer configuration status."""
    try:
        printer = get_printer_service()
        return {
            "type": printer.printer_type,
            "status": "configured",
        }
    except Exception as e:
        logger.error(f"Failed to get printer status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ticket")
async def print_ticket(data: TicketPrintRequest) -> dict[str, bool | str]:
    """Print a queue ticket on the thermal printer."""
    try:
        printer = get_printer_service()
        success = printer.print_queue_ticket(
            ticket_number=data.ticketNumber,
            patient_name="",
            department_name=data.departmentName,
            floor=data.floor or 1,
            room=data.roomNumber or "101",
            estimated_wait=data.estimatedWait or 15,
            doctor_name=data.doctorName,
        )
        if success:
            return {"success": True, "message": "Ticket printed"}
        return {"success": False, "message": "Print failed"}
    except Exception as e:
        logger.opt(exception=True).warning("Ticket printing failed")
        return {"success": False, "message": f"Printer not available: {e}"}
