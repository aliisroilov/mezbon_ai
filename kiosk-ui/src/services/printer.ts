import { getSocket } from "./socket";

export interface QueueTicketData {
  ticket_number: string;
  patient_name: string;
  department_name: string;
  floor: number;
  room: string;
  estimated_wait: number;
  doctor_name?: string;
  clinic_name?: string;
  clinic_address?: string;
}

export interface BookingConfirmationData {
  booking_id: string;
  patient_name: string;
  department_name: string;
  doctor_name: string;
  appointment_date: string;
  appointment_time: string;
  service_name: string;
  price: number;
  clinic_name?: string;
  clinic_address?: string;
}

export interface PaymentReceiptData {
  payment_id: string;
  patient_name: string;
  amount: number;
  payment_method: string;
  service_name: string;
  clinic_name?: string;
  clinic_address?: string;
}

export type ReceiptType = "queue_ticket" | "booking_confirmation" | "payment_receipt";

/**
 * Request receipt printing via Socket.IO
 */
export function printReceipt(
  deviceId: string,
  receiptType: ReceiptType,
  data: QueueTicketData | BookingConfirmationData | PaymentReceiptData,
): void {
  getSocket().emit("kiosk:print_receipt", {
    device_id: deviceId,
    receipt_type: receiptType,
    data,
  });
}

/**
 * Print queue ticket
 */
export function printQueueTicket(
  deviceId: string,
  data: QueueTicketData,
): void {
  printReceipt(deviceId, "queue_ticket", data);
}

/**
 * Print booking confirmation
 */
export function printBookingConfirmation(
  deviceId: string,
  data: BookingConfirmationData,
): void {
  printReceipt(deviceId, "booking_confirmation", data);
}

/**
 * Print payment receipt
 */
export function printPaymentReceipt(
  deviceId: string,
  data: PaymentReceiptData,
): void {
  printReceipt(deviceId, "payment_receipt", data);
}
