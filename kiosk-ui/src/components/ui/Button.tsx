import { forwardRef, type ReactNode } from "react";
import { motion, type HTMLMotionProps } from "framer-motion";
import { cn } from "../../lib/cn";
import { LoadingDots } from "../feedback/LoadingDots";
import { sounds } from "../../utils/sounds";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps
  extends Omit<HTMLMotionProps<"button">, "children" | "size"> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  disabled?: boolean;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
  children: ReactNode;
}

const variantStyles: Record<Variant, string> = {
  primary:
    "bg-primary text-white shadow-button hover:bg-primary-dark hover:-translate-y-0.5 active:translate-y-0",
  secondary:
    "bg-white text-primary border-2 border-primary hover:bg-primary-50",
  ghost: "text-primary hover:bg-primary-50",
  danger: "bg-danger text-white hover:bg-red-600",
};

const sizeStyles: Record<Size, string> = {
  sm: "min-h-[44px] px-5 text-[16px]",
  md: "min-h-[56px] px-8 text-button",
  lg: "min-h-[72px] px-10 text-[20px]",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled = false,
      iconLeft,
      iconRight,
      children,
      className,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <motion.button
        ref={ref}
        whileTap={isDisabled ? undefined : { scale: 0.96 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
        disabled={isDisabled}
        onPointerDown={() => { if (!isDisabled) sounds.tap(); }}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-button font-semibold",
          "transition-all duration-200 select-none",
          "focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-primary/40 focus-visible:ring-offset-4",
          variantStyles[variant],
          sizeStyles[size],
          isDisabled && "pointer-events-none opacity-50",
          className,
        )}
        {...props}
      >
        {loading ? (
          <LoadingDots />
        ) : (
          <>
            {iconLeft && <span className="shrink-0">{iconLeft}</span>}
            {children}
            {iconRight && <span className="shrink-0">{iconRight}</span>}
          </>
        )}
      </motion.button>
    );
  },
);

Button.displayName = "Button";
