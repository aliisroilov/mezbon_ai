import { motion } from "framer-motion";
import { LoadingDots } from "./LoadingDots";
import { cn } from "../../lib/cn";

interface LoadingMessageProps {
  message: string;
  className?: string;
}

/**
 * Context-specific loading indicator: 3 pulsing dots + descriptive message.
 * Replaces generic "Loading..." with context like "Bo'limlar yuklanmoqda..."
 */
export function LoadingMessage({ message, className }: LoadingMessageProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className={cn(
        "flex flex-col items-center justify-center gap-4 py-16",
        className,
      )}
    >
      <LoadingDots color="bg-primary" />
      <p className="text-body text-text-muted">{message}</p>
    </motion.div>
  );
}
