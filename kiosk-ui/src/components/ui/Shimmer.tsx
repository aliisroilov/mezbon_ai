import { cn } from "../../lib/cn";

interface ShimmerProps {
  className?: string;
  rounded?: "sm" | "md" | "lg" | "full" | "card";
}

const roundedStyles: Record<string, string> = {
  sm: "rounded-md",
  md: "rounded-xl",
  lg: "rounded-2xl",
  full: "rounded-full",
  card: "rounded-card",
};

export function Shimmer({ className, rounded = "md" }: ShimmerProps) {
  return (
    <div
      className={cn(
        "animate-shimmer bg-gradient-to-r from-slate-100 via-slate-200 to-slate-100",
        "bg-[length:200%_100%]",
        roundedStyles[rounded],
        className,
      )}
    />
  );
}
