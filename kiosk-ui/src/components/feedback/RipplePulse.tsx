import { motion } from "framer-motion";
import { cn } from "../../lib/cn";

interface RipplePulseProps {
  active?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function RipplePulse({ active = true, className, children }: RipplePulseProps) {
  return (
    <div className={cn("relative inline-flex items-center justify-center", className)}>
      {active &&
        [0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="absolute inset-0 rounded-full border-2 border-primary/40"
            animate={{ scale: [0.8, 2.5], opacity: [0.6, 0] }}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: i * 0.6,
              ease: "easeOut",
            }}
          />
        ))}
      <div className="relative z-10">{children}</div>
    </div>
  );
}
