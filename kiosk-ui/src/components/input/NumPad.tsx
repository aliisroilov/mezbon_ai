import { motion } from "framer-motion";
import { Delete } from "lucide-react";
import { cn } from "../../lib/cn";

interface NumPadProps {
  onDigit: (digit: string) => void;
  onBackspace: () => void;
  onClear: () => void;
}

const keys = [
  ["1", "2", "3"],
  ["4", "5", "6"],
  ["7", "8", "9"],
  ["C", "0", "⌫"],
];

export function NumPad({ onDigit, onBackspace, onClear }: NumPadProps) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {keys.flat().map((key) => {
        const isAction = key === "C" || key === "⌫";
        return (
          <motion.button
            key={key}
            whileTap={{ scale: 0.93, backgroundColor: "rgba(30,42,110,0.08)" }}
            onClick={() => {
              if (key === "⌫") onBackspace();
              else if (key === "C") onClear();
              else onDigit(key);
            }}
            className={cn(
              "flex h-[64px] w-[64px] mx-auto items-center justify-center rounded-2xl text-[28px] font-semibold transition-all duration-150",
              isAction
                ? key === "C"
                  ? "bg-red-50 text-danger"
                  : "bg-slate-100 text-text-body"
                : "bg-white text-text-primary shadow-card hover:shadow-card-hover active:bg-primary-50",
            )}
          >
            {key === "⌫" ? <Delete className="h-6 w-6" /> : key}
          </motion.button>
        );
      })}
    </div>
  );
}
