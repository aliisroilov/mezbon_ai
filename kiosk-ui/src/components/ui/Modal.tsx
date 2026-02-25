import { type ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../../lib/cn";

interface ModalProps {
  open: boolean;
  onClose?: () => void;
  mode?: "center" | "bottom";
  children: ReactNode;
  className?: string;
}

const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

const centerVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: "spring" as const, stiffness: 300, damping: 25 },
  },
  exit: { opacity: 0, scale: 0.95, y: 20, transition: { duration: 0.2 } },
};

const bottomVariants = {
  hidden: { opacity: 0, y: "100%" },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring" as const, stiffness: 300, damping: 30 },
  },
  exit: { opacity: 0, y: "100%", transition: { duration: 0.25 } },
};

export function Modal({
  open,
  onClose,
  mode = "center",
  children,
  className,
}: ModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center"
          initial="hidden"
          animate="visible"
          exit="hidden"
        >
          <motion.div
            className="absolute inset-0 bg-black/30 backdrop-blur-sm"
            variants={overlayVariants}
            onClick={onClose}
          />
          <motion.div
            variants={mode === "center" ? centerVariants : bottomVariants}
            className={cn(
              "relative z-10 w-full bg-white shadow-modal",
              mode === "center" && "max-w-lg rounded-modal p-8",
              mode === "bottom" && "fixed bottom-0 left-0 right-0 rounded-t-modal p-8",
              className,
            )}
          >
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
