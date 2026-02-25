import { Loader2 } from "lucide-react";
import clsx from "clsx";

interface Props {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function LoadingSpinner({ size = "md", className }: Props) {
  return (
    <Loader2
      className={clsx(
        "animate-spin text-primary-600",
        size === "sm" && "h-4 w-4",
        size === "md" && "h-6 w-6",
        size === "lg" && "h-10 w-10",
        className,
      )}
    />
  );
}
