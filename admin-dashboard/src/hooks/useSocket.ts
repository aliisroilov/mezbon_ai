import { useEffect } from "react";
import { connectSocket, disconnectSocket } from "../services/socket";

export function useSocket() {
  useEffect(() => {
    connectSocket();
    return () => {
      disconnectSocket();
    };
  }, []);
}
