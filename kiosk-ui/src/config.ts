/**
 * Runtime configuration for the kiosk application.
 * Detects whether running on actual kiosk hardware vs dev environment.
 */

export const IS_KIOSK =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

export const KIOSK_ORIENTATION = "portrait" as const; // 1080x1920

export const PRINTER_ENABLED = IS_KIOSK;

export const API_BASE =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export const SOCKET_URL =
  import.meta.env.VITE_SOCKET_URL || "http://localhost:8000";
