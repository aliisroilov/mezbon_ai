import { useEffect, useState } from "react";
import { cn } from "../../lib/cn";

interface CountUpNumberProps {
  target: number;
  duration?: number;
  className?: string;
  prefix?: string;
}

export function CountUpNumber({
  target,
  duration = 800,
  className,
  prefix = "",
}: CountUpNumberProps) {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const start = performance.now();
    const startVal = 0;

    function tick() {
      const elapsed = performance.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOut cubic
      const value = Math.round(startVal + (target - startVal) * eased);
      setCurrent(value);

      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    }

    requestAnimationFrame(tick);
  }, [target, duration]);

  return (
    <span className={cn("tabular-nums", className)}>
      {prefix}{current}
    </span>
  );
}
