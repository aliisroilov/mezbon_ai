import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const COLORS = ["#1B3A6B", "#F59E0B", "#3B82F6", "#10B981", "#8B5CF6"];
const PARTICLE_COUNT = 35;

interface Particle {
  id: number;
  x: number;
  y: number;
  color: string;
  size: number;
  shape: "circle" | "square";
}

function randomBetween(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

export function ConfettiEffect({ active }: { active: boolean }) {
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    if (!active) {
      setParticles([]);
      return;
    }

    const items: Particle[] = Array.from({ length: PARTICLE_COUNT }, (_, i) => ({
      id: i,
      x: randomBetween(-200, 200),
      y: randomBetween(-400, -100),
      color: COLORS[i % COLORS.length]!,
      size: randomBetween(6, 12),
      shape: Math.random() > 0.5 ? "circle" : "square",
    }));
    setParticles(items);

    const timer = setTimeout(() => setParticles([]), 2000);
    return () => clearTimeout(timer);
  }, [active]);

  return (
    <div className="pointer-events-none fixed inset-0 z-50 overflow-hidden">
      <AnimatePresence>
        {particles.map((p) => (
          <motion.div
            key={p.id}
            className="absolute left-1/2 top-1/2"
            initial={{ x: 0, y: 0, opacity: 1, scale: 1, rotate: 0 }}
            animate={{
              x: p.x,
              y: p.y + 600,
              opacity: [1, 1, 0],
              scale: [1, 1.2, 0.6],
              rotate: randomBetween(-360, 360),
            }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2, ease: [0.25, 0.46, 0.45, 0.94] }}
            style={{
              width: p.size,
              height: p.size,
              backgroundColor: p.color,
              borderRadius: p.shape === "circle" ? "50%" : "2px",
            }}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
