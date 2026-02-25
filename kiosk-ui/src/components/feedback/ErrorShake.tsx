import { motion, useAnimation } from "framer-motion";
import { useEffect, type ReactNode } from "react";

interface ErrorShakeProps {
  trigger: boolean;
  children: ReactNode;
  className?: string;
}

export function ErrorShake({ trigger, children, className }: ErrorShakeProps) {
  const controls = useAnimation();

  useEffect(() => {
    if (trigger) {
      controls.start({
        x: [-4, 4, -4, 4, 0],
        transition: { duration: 0.4, ease: "easeInOut" },
      });
    }
  }, [trigger, controls]);

  return (
    <motion.div animate={controls} className={className}>
      {children}
    </motion.div>
  );
}
