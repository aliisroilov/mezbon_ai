import { motion } from "framer-motion";
import { cn } from "../../lib/cn";

interface LoadingDotsProps {
  className?: string;
  color?: string;
}

export function LoadingDots({ className, color }: LoadingDotsProps) {
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className={cn("block h-2 w-2 rounded-full", color ?? "bg-current")}
          animate={{ scale: [1, 1.4, 1], opacity: [0.5, 1, 0.5] }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            delay: i * 0.15,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}
