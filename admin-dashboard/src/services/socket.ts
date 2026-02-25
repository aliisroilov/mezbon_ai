import { io, Socket } from "socket.io-client";
import type { AdminListenEvents } from "../types";

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || "http://localhost:8000";

let socket: Socket | null = null;

export function getSocket(): Socket {
  if (!socket) {
    socket = io(SOCKET_URL, {
      path: "/socket.io",
      transports: ["websocket", "polling"],
      autoConnect: false,
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 10000,
    });
  }
  return socket;
}

export function connectSocket() {
  const s = getSocket();
  if (!s.connected) {
    s.connect();
  }
}

export function disconnectSocket() {
  if (socket?.connected) {
    socket.disconnect();
  }
}

export function onQueueUpdate(
  cb: (data: AdminListenEvents["queue:update"]) => void,
) {
  getSocket().on("queue:update", cb);
  return () => {
    getSocket().off("queue:update", cb);
  };
}

export function onDeviceHeartbeat(
  cb: (data: AdminListenEvents["device:heartbeat"]) => void,
) {
  getSocket().on("device:heartbeat", cb);
  return () => {
    getSocket().off("device:heartbeat", cb);
  };
}

export function onDeviceStatusChange(
  cb: (data: AdminListenEvents["device:status_change"]) => void,
) {
  getSocket().on("device:status_change", cb);
  return () => {
    getSocket().off("device:status_change", cb);
  };
}

export function onPaymentConfirmed(
  cb: (data: AdminListenEvents["payment:confirmed"]) => void,
) {
  getSocket().on("payment:confirmed", cb);
  return () => {
    getSocket().off("payment:confirmed", cb);
  };
}

export function onActivityNew(
  cb: (data: AdminListenEvents["activity:new"]) => void,
) {
  getSocket().on("activity:new", cb);
  return () => {
    getSocket().off("activity:new", cb);
  };
}
