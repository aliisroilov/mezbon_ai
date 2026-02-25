import { motion } from "framer-motion";

interface SuccessAnimationProps {
  size?: number;
  className?: string;
}

export function SuccessAnimation({ size = 120, className }: SuccessAnimationProps) {
  const circleR = size / 2 - 4;
  const checkPath = `M${size * 0.28} ${size * 0.5} L${size * 0.44} ${size * 0.65} L${size * 0.72} ${size * 0.38}`;

  return (
    <div className={className} style={{ width: size, height: size, position: "relative" }}>
      {/* Particle burst */}
      {Array.from({ length: 8 }).map((_, i) => {
        const angle = (i / 8) * Math.PI * 2;
        const x = Math.cos(angle) * size * 0.7;
        const y = Math.sin(angle) * size * 0.7;
        return (
          <motion.div
            key={i}
            className="absolute left-1/2 top-1/2 h-2 w-2 rounded-full bg-success"
            initial={{ x: 0, y: 0, scale: 0, opacity: 1 }}
            animate={{
              x,
              y,
              scale: [0, 1.2, 0],
              opacity: [1, 1, 0],
            }}
            transition={{ duration: 0.7, delay: 0.3, ease: "easeOut" }}
          />
        );
      })}

      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
        {/* Circle background */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={circleR}
          fill="#10B981"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 15, duration: 0.3 }}
          style={{ transformOrigin: "center" }}
        />

        {/* Checkmark */}
        <motion.path
          d={checkPath}
          fill="none"
          stroke="white"
          strokeWidth={size * 0.06}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.3, delay: 0.3, ease: "easeOut" }}
        />
      </svg>
    </div>
  );
}
