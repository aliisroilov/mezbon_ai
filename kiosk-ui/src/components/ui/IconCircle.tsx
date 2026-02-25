import { type ReactNode } from "react";
import { cn } from "../../lib/cn";

type Size = "sm" | "md" | "lg";

interface IconCircleProps {
  size?: Size;
  gradient?: boolean;
  children: ReactNode;
  className?: string;
}

const sizeStyles: Record<Size, string> = {
  sm: "h-10 w-10",
  md: "h-14 w-14",
  lg: "h-[72px] w-[72px]",
};

const iconSizes: Record<Size, number> = {
  sm: 18,
  md: 24,
  lg: 32,
};

export function IconCircle({
  size = "md",
  gradient = false,
  children,
  className,
}: IconCircleProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center justify-center rounded-full",
        "text-primary [&_svg]:h-auto",
        sizeStyles[size],
        gradient
          ? "bg-gradient-to-br from-primary-light to-primary-50 ring-2 ring-primary/10"
          : "bg-primary-50",
        className,
      )}
      style={{ fontSize: iconSizes[size] }}
    >
      {children}
    </div>
  );
}
