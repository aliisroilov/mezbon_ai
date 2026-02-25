import { motion } from "framer-motion";
import { LanguageSelector } from "../ui/LanguageSelector";
import { NanoMedicalLogo } from "../ui/NanoMedicalLogo";
import { cn } from "../../lib/cn";

interface HeaderBarProps {
  title: string;
  className?: string;
}

export function HeaderBar({ title, className }: HeaderBarProps) {
  return (
    <div
      className={cn(
        "flex h-[80px] shrink-0 items-center justify-between border-b border-slate-200/60 bg-white/80 px-8 backdrop-blur-sm",
        className,
      )}
    >
      {/* Logo */}
      <NanoMedicalLogo size="sm" />

      {/* Title */}
      {title && (
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.3 }}
          className="text-h2 tracking-heading text-text-primary"
        >
          {title}
        </motion.h1>
      )}

      {/* Language selector */}
      <LanguageSelector />
    </div>
  );
}
