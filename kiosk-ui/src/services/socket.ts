import { io, type Socket } from "socket.io-client";
import type { KioskListenEvents } from "../types";

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || "http://localhost:8000";
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

type StatusListener = (status: ConnectionStatus) => void;

let socket: Socket | null = null;
let connectionStatus: ConnectionStatus = "disconnected";
let deviceToken: string | null = null;
const statusListeners = new Set<StatusListener>();

function notifyStatus(status: ConnectionStatus) {
  connectionStatus = status;
  statusListeners.forEach((fn) => fn(status));
}

/**
 * Fetch a device JWT from the backend. The kiosk authenticates by device_id
 * + clinic_id.  The backend issues a short-lived JWT that Socket.IO accepts.
 */
async function fetchDeviceToken(deviceId: string, clinicId: string): Promise<string> {
  // Return cached token if we have one
  if (deviceToken) return deviceToken;

  const res = await fetch(`${API_BASE}/auth/device`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ device_id: deviceId, clinic_id: clinicId }),
  });

  if (!res.ok) {
    throw new Error(`Device auth failed: ${res.status}`);
  }

  const json = await res.json();
  const token: string = json.data?.access_token;
  if (!token) throw new Error("No access_token in device auth response");

  deviceToken = token;
  return token;
}

export function getSocket(): Socket {
  if (socket) return socket;

  socket = io(SOCKET_URL, {
    path: "/ws/socket.io",
    transports: ["websocket", "polling"],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 10000,
    autoConnect: false,
  });

  socket.on("connect", () => {
    if (import.meta.env.DEV) console.log("[socket] connected, id:", socket?.id);
    notifyStatus("connected");
  });
  socket.on("disconnect", (reason) => {
    if (import.meta.env.DEV) console.warn("[socket] disconnected:", reason);
    notifyStatus("disconnected");
    // Clear cached token — it may be expired by the time we reconnect
    deviceToken = null;
  });
  socket.on("reconnect_attempt", () => notifyStatus("reconnecting"));
  socket.on("reconnect_failed", () => notifyStatus("disconnected"));
  socket.on("connect_error", (err) => {
    if (import.meta.env.DEV) console.error("[socket] connect_error:", err.message);
    // Clear token on auth failures so next reconnect fetches a fresh one
    if (err.message.includes("auth") || err.message.includes("401") || err.message.includes("token")) {
      deviceToken = null;
    }
  });

  return socket;
}

/**
 * Connect the socket with proper device authentication.
 * Must be called with the device and clinic IDs so we can fetch a JWT first.
 */
export async function connectSocket(deviceId: string, clinicId: string): Promise<void> {
  const s = getSocket();
  if (s.connected) return;

  try {
    const token = await fetchDeviceToken(deviceId, clinicId);

    // Set auth data that the backend Socket.IO server expects
    s.auth = { token, device_id: deviceId };
    s.connect();
  } catch (err) {
    if (import.meta.env.DEV) console.error("[socket] Device auth failed, connecting without token:", err);
    // Still try to connect — backend may allow it in dev mode
    s.auth = { device_id: deviceId };
    s.connect();
  }
}

export function disconnectSocket(): void {
  socket?.disconnect();
}

export function onConnectionStatus(listener: StatusListener): () => void {
  statusListeners.add(listener);
  listener(connectionStatus);
  return () => {
    statusListeners.delete(listener);
  };
}

export function getConnectionStatus(): ConnectionStatus {
  return connectionStatus;
}

export function getDeviceToken(): string | null {
  return deviceToken;
}

export function onAIResponse(
  handler: (data: KioskListenEvents["ai:response"]) => void,
): () => void {
  const s = getSocket();
  s.on("ai:response", handler);
  return () => {
    s.off("ai:response", handler);
  };
}

export function onAIStateChange(
  handler: (data: KioskListenEvents["ai:state_change"]) => void,
): () => void {
  const s = getSocket();
  s.on("ai:state_change", handler);
  return () => {
    s.off("ai:state_change", handler);
  };
}

export function onAIProcessing(
  handler: (data: { session_id: string }) => void,
): () => void {
  const s = getSocket();
  s.on("ai:processing", handler);
  return () => {
    s.off("ai:processing", handler);
  };
}

export function onAIError(
  handler: (data: KioskListenEvents["ai:error"]) => void,
): () => void {
  const s = getSocket();
  s.on("ai:error", handler);
  return () => {
    s.off("ai:error", handler);
  };
}

export function onSessionTimeout(
  handler: (data: KioskListenEvents["session:timeout"]) => void,
): () => void {
  const s = getSocket();
  s.on("session:timeout", handler);
  return () => {
    s.off("session:timeout", handler);
  };
}

export function emitFaceFrame(deviceId: string, frame: string): void {
  getSocket().emit("kiosk:face_frame", { device_id: deviceId, frame });
}

export async function emitSpeechAudio(
  deviceId: string,
  sessionId: string,
  audio: Blob,
  format: string,
): Promise<void> {
  // Convert Blob to base64 string — Blob is NOT serializable over Socket.IO
  const arrayBuffer = await audio.arrayBuffer();
  const bytes = new Uint8Array(arrayBuffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]!);
  }
  const base64 = btoa(binary);

  const s = getSocket();
  if (!s.connected) {
    if (import.meta.env.DEV) console.error("[socket] Cannot send audio — socket not connected");
    return;
  }

  if (import.meta.env.DEV) console.log(`[socket] Emitting kiosk:speech_audio — ${base64.length} chars base64, session: ${sessionId || "(new)"}`);
  s.emit("kiosk:speech_audio", {
    device_id: deviceId,
    session_id: sessionId,
    audio: base64,
    format,
  });
  window.dispatchEvent(new Event("speech-sent"));
}

/**
 * Send text directly to the AI (bypasses STT).
 * Use when Muxlisa STT is down or when using browser-side speech recognition.
 */
export function emitChatText(
  deviceId: string,
  sessionId: string,
  text: string,
  language: string = "uz",
): void {
  const s = getSocket();
  if (!s.connected) {
    if (import.meta.env.DEV) console.error("[socket] Cannot send text — socket not connected");
    return;
  }
  if (import.meta.env.DEV) console.log(`[socket] Emitting kiosk:chat_text — "${text}", session: ${sessionId || "(new)"}`);
  s.emit("kiosk:chat_text", {
    device_id: deviceId,
    session_id: sessionId,
    text,
    language,
  });
  window.dispatchEvent(new Event("speech-sent"));
}

export function emitTouchAction(
  deviceId: string,
  sessionId: string,
  action: string,
  data: Record<string, unknown> = {},
): void {
  getSocket().emit("kiosk:touch_action", {
    device_id: deviceId,
    session_id: sessionId,
    action,
    data,
  });
}
