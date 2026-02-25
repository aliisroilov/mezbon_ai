import { cn } from "../../lib/cn";

interface DividerProps {
  text?: string;
  className?: string;
}

export function Divider({ text, className }: DividerProps) {
  if (text) {
    return (
      <div className={cn("flex items-center gap-4", className)}>
        <div className="h-px flex-1 bg-border" />
        <span className="text-caption text-text-muted">{text}</span>
        <div className="h-px flex-1 bg-border" />
      </div>
    );
  }

  return <div className={cn("h-px w-full bg-border", className)} />;
}
