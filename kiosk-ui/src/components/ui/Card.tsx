import { type ReactNode } from "react";
import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { cn } from "../../lib/cn";

interface CardProps {
  icon?: ReactNode;
  title?: string;
  subtitle?: string;
  badge?: ReactNode;
  selected?: boolean;
  onClick?: () => void;
  children?: ReactNode;
  className?: string;
}

export function Card({
  icon,
  title,
  subtitle,
  badge,
  selected = false,
  onClick,
  children,
  className,
}: CardProps) {
  return (
    <motion.div
      whileHover={{ y: -2 }}
      whileTap={onClick ? { scale: 0.98 } : undefined}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={cn(
        "relative rounded-card bg-surface-card p-7 shadow-card transition-shadow duration-200",
        onClick && "cursor-pointer hover:shadow-card-hover",
        selected && "border-l-4 border-l-primary bg-primary-50",
        className,
      )}
    >
      {selected && (
        <div className="absolute top-4 right-4 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-white">
          <Check size={14} strokeWidth={3} />
        </div>
      )}

      {badge && !selected && (
        <div className="absolute top-4 right-4">{badge}</div>
      )}

      {(icon || title || subtitle) && (
        <div className="flex items-start gap-4">
          {icon && (
            <div className="flex h-12 w-12 shrink-0 items-center justify-center text-[32px]">
              {icon}
            </div>
          )}
          <div className="min-w-0 flex-1">
            {title && (
              <h3 className="truncate text-h3 tracking-heading text-text-primary">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="mt-1 line-clamp-2 text-body text-text-muted">
                {subtitle}
              </p>
            )}
          </div>
        </div>
      )}

      {children}
    </motion.div>
  );
}
