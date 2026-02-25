import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-caption font-semibold text-text-body"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            "h-touch-md rounded-input border border-border bg-white px-4 text-body text-text-primary",
            "transition-all duration-200 placeholder:text-text-muted",
            "focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none",
            error && "border-red-400 focus:border-red-400 focus:ring-red-400/20",
            className,
          )}
          {...props}
        />
        {error && (
          <p className="text-caption text-danger">{error}</p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
