import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { cn } from "../../lib/cn";

interface TypewriterTextProps {
  text: string;
  delayMs?: number;
  onComplete?: () => void;
  className?: string;
}

export function TypewriterText({
  text,
  delayMs = 40,
  onComplete,
  className,
}: TypewriterTextProps) {
  const words = text.split(" ");
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    setVisibleCount(0);
  }, [text]);

  useEffect(() => {
    if (visibleCount >= words.length) {
      onComplete?.();
      return;
    }

    const timer = setTimeout(() => {
      setVisibleCount((c) => c + 1);
    }, delayMs);

    return () => clearTimeout(timer);
  }, [visibleCount, words.length, delayMs, onComplete]);

  return (
    <span className={className}>
      {words.slice(0, visibleCount).map((word, i) => (
        <motion.span
          key={`${i}-${word}`}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.15 }}
          className="inline"
        >
          {word}{" "}
        </motion.span>
      ))}
      {visibleCount < words.length && (
        <motion.span
          animate={{ opacity: [0, 1, 0] }}
          transition={{ duration: 0.8, repeat: Infinity }}
          className={cn("inline-block h-[1em] w-[2px] translate-y-0.5 bg-current")}
        />
      )}
    </span>
  );
}
