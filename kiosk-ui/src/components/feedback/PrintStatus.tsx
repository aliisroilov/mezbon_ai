import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Printer, CheckCircle, AlertCircle } from "lucide-react";
import { getSocket } from "../../services/socket";

type Status = "printing" | "success" | "error";

interface PrintState {
  show: boolean;
  status: Status;
  message: string;
}

export function PrintStatus() {
  const [printState, setPrintState] = useState<PrintState>({
    show: false,
    status: "printing",
    message: "",
  });

  useEffect(() => {
    const socket = getSocket();

    const handleStatus = (data: { success: boolean; receipt_type: string }) => {
      setPrintState({
        show: true,
        status: data.success ? "success" : "error",
        message: data.success
          ? "Chek chop etildi / Чек распечатан"
          : "Chop etishda xato / Ошибка печати",
      });

      setTimeout(() => {
        setPrintState((prev) => ({ ...prev, show: false }));
      }, 3000);
    };

    const handleError = (data: { error: string }) => {
      setPrintState({
        show: true,
        status: "error",
        message: `Xato / Ошибка: ${data.error}`,
      });

      setTimeout(() => {
        setPrintState((prev) => ({ ...prev, show: false }));
      }, 5000);
    };

    socket.on("printer:status", handleStatus);
    socket.on("printer:error", handleError);

    return () => {
      socket.off("printer:status", handleStatus);
      socket.off("printer:error", handleError);
    };
  }, []);

  return (
    <AnimatePresence>
      {printState.show && (
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 40 }}
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
          className="fixed bottom-32 left-1/2 z-50 -translate-x-1/2"
        >
          <div
            className={`flex items-center gap-3 rounded-2xl px-6 py-4 shadow-lg ${
              printState.status === "success"
                ? "bg-emerald-500 text-white"
                : printState.status === "error"
                  ? "bg-red-500 text-white"
                  : "bg-primary text-white"
            }`}
          >
            {printState.status === "printing" && (
              <Printer className="h-5 w-5 animate-pulse" />
            )}
            {printState.status === "success" && (
              <CheckCircle className="h-5 w-5" />
            )}
            {printState.status === "error" && (
              <AlertCircle className="h-5 w-5" />
            )}
            <span className="text-body font-medium">{printState.message}</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
