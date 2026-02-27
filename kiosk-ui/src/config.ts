/**
 * Runtime configuration for the kiosk application.
 * Detects whether running on actual kiosk hardware vs dev environment.
 */

const hostname = window.location.hostname;
export const IS_KIOSK =
  hostname !== "localhost" &&
  hostname !== "127.0.0.1";

export const KIOSK_ORIENTATION = "portrait" as const; // 1080x1920

/** Printing is always enabled — uses browser print fallback when backend printer is unavailable */
export const PRINTER_ENABLED = true;

export const API_BASE =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export const SOCKET_URL =
  import.meta.env.VITE_SOCKET_URL || "http://localhost:8000";
