import clsx from "clsx";
import type { ReactNode } from "react";

type Variant = "default" | "success" | "warning" | "danger" | "info";

interface Props {
  variant?: Variant;
  children: ReactNode;
  className?: string;
  dot?: boolean;
}

const variantStyles: Record<Variant, string> = {
  default: "bg-slate-100 text-slate-700",
  success: "bg-emerald-50 text-emerald-700",
  warning: "bg-amber-50 text-amber-700",
  danger: "bg-red-50 text-red-700",
  info: "bg-blue-50 text-blue-700",
};

const dotStyles: Record<Variant, string> = {
  default: "bg-slate-400",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  danger: "bg-red-500",
  info: "bg-blue-500",
};

export function Badge({ variant = "default", children, className, dot }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className,
      )}
    >
      {dot && (
        <span
          className={clsx("h-1.5 w-1.5 rounded-full", dotStyles[variant])}
        />
      )}
      {children}
    </span>
  );
}
