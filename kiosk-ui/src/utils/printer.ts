/**
 * Thermal printer integration for queue tickets.
 *
 * Strategy (in order):
 * 1. Local print proxy at http://localhost:9111/print — runs on the kiosk
 *    machine and sends ESC/POS commands directly to the thermal printer.
 *    This prints SILENTLY with no dialog.
 * 2. Browser iframe print fallback — opens print dialog (requires user confirm)
 */

import { PRINTER_ENABLED } from "../config";

/** URL of the local print proxy running on the kiosk machine */
const LOCAL_PRINT_PROXY = "http://localhost:9111";

interface TicketData {
  ticketNumber: string;
  departmentName: string;
  doctorName?: string;
  date: string;
  time?: string;
  roomNumber?: string;
  floor?: number;
  estimatedWait?: number;
}

/**
 * Print a queue ticket on the thermal printer.
 * Tries local print proxy first (silent), falls back to browser print dialog.
 */
export async function printTicket(ticket: TicketData): Promise<boolean> {
  if (!PRINTER_ENABLED) {
    if (import.meta.env.DEV) console.log("[printer] Printing disabled");
    return false;
  }

  if (import.meta.env.DEV) console.log("[printer] Printing ticket:", ticket.ticketNumber);

  // Try local print proxy first (silent, no dialog)
  try {
    const res = await fetch(`${LOCAL_PRINT_PROXY}/print`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type: "queue_ticket",
        ...ticket,
      }),
      signal: AbortSignal.timeout(3000), // 3s timeout
    });

    if (res.ok) {
      if (import.meta.env.DEV) console.log("[printer] Ticket printed silently via local proxy");
      return true;
    }
    if (import.meta.env.DEV) console.warn("[printer] Local proxy returned", res.status);
  } catch {
    if (import.meta.env.DEV) console.log("[printer] Local print proxy not available, using browser print");
  }

  // Fallback: browser print with iframe (shows dialog)
  return printViaBrowser(ticket);
}

/**
 * Sanitize text for safe insertion into DOM
 */
function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Fallback: create a hidden iframe with ticket content and trigger print
 */
function printViaBrowser(ticket: TicketData): boolean {
  try {
    const iframe = document.createElement("iframe");
    iframe.style.position = "fixed";
    iframe.style.left = "-9999px";
    iframe.style.top = "-9999px";
    iframe.style.width = "300px";
    iframe.style.height = "500px";
    document.body.appendChild(iframe);

    const doc = iframe.contentDocument;
    if (!doc) {
      document.body.removeChild(iframe);
      return false;
    }

    // Build the ticket content safely using DOM methods
    const style = doc.createElement("style");
    style.textContent = `
      @page { size: 80mm auto; margin: 2mm; }
      body { font-family: 'Courier New', monospace; width: 76mm; margin: 0; padding: 2mm; font-size: 12px; line-height: 1.4; }
      .center { text-align: center; }
      .bold { font-weight: bold; }
      .xlarge { font-size: 36px; font-weight: bold; }
      .divider { border-top: 1px dashed #000; margin: 4mm 0; }
      .row { display: flex; justify-content: space-between; margin: 1mm 0; }
      .label { color: #666; }
      .footer { font-size: 10px; color: #666; }
      .timestamp { font-size: 9px; color: #999; }
    `;
    doc.head.appendChild(style);

    const body = doc.body;

    // Clinic name
    const header = doc.createElement("div");
    header.className = "center bold";
    header.textContent = "NANO MEDICAL CLINIC";
    body.appendChild(header);

    body.appendChild(createDivider(doc));

    // Ticket number
    const ticketLabel = doc.createElement("div");
    ticketLabel.className = "center";
    ticketLabel.style.margin = "3mm 0";
    ticketLabel.textContent = "NAVBAT RAQAMI";
    body.appendChild(ticketLabel);

    const ticketNum = doc.createElement("div");
    ticketNum.className = "center xlarge";
    ticketNum.textContent = escapeHtml(ticket.ticketNumber);
    body.appendChild(ticketNum);

    body.appendChild(createDivider(doc));

    // Department
    addRow(doc, body, "Bo'lim:", ticket.departmentName, true);

    // Doctor
    if (ticket.doctorName) {
      addRow(doc, body, "Shifokor:", ticket.doctorName);
    }

    // Date
    addRow(doc, body, "Sana:", ticket.date);

    // Time
    if (ticket.time) {
      addRow(doc, body, "Vaqt:", ticket.time, true);
    }

    // Room
    if (ticket.roomNumber) {
      const roomText = (ticket.floor ? `${ticket.floor}-qavat, ` : "") + `${ticket.roomNumber}-xona`;
      addRow(doc, body, "Xona:", roomText, true);
    }

    // Wait time
    if (ticket.estimatedWait) {
      addRow(doc, body, "Kutish:", `~${ticket.estimatedWait} daqiqa`);
    }

    body.appendChild(createDivider(doc));

    // Footer
    const footer = doc.createElement("div");
    footer.className = "center footer";
    footer.textContent = "Navbatingiz ekranda e'lon qilinadi. Iltimos, kutish zonasida kuting.";
    body.appendChild(footer);

    body.appendChild(createDivider(doc));

    // Timestamp
    const timestamp = doc.createElement("div");
    timestamp.className = "center timestamp";
    timestamp.textContent = new Date().toLocaleString("uz-UZ");
    body.appendChild(timestamp);

    // Print and cleanup
    setTimeout(() => {
      iframe.contentWindow?.print();
      setTimeout(() => {
        document.body.removeChild(iframe);
      }, 1000);
    }, 200);

    return true;
  } catch {
    if (import.meta.env.DEV) console.error("[printer] Browser print failed");
    return false;
  }
}

function createDivider(doc: Document): HTMLDivElement {
  const div = doc.createElement("div");
  div.className = "divider";
  return div;
}

function addRow(doc: Document, parent: HTMLElement, label: string, value: string, bold = false): void {
  const row = doc.createElement("div");
  row.className = "row";

  const labelEl = doc.createElement("span");
  labelEl.className = "label";
  labelEl.textContent = label;
  row.appendChild(labelEl);

  const valueEl = doc.createElement("span");
  if (bold) valueEl.className = "bold";
  valueEl.textContent = escapeHtml(value);
  row.appendChild(valueEl);

  parent.appendChild(row);
}
