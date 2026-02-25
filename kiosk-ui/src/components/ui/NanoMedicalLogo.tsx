import { cn } from "../../lib/cn";

interface LogoProps {
  className?: string;
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: { height: 32, fontSize: 14, iconSize: 20 },
  md: { height: 48, fontSize: 18, iconSize: 28 },
  lg: { height: 220, fontSize: 32, iconSize: 64 },
};

export function NanoMedicalLogo({ className, size = "md" }: LogoProps) {
  const s = sizes[size];

  return (
    <div className={cn("flex items-center gap-2.5", className)} style={{ height: s.height }}>
      {/* Icon — stylized "N" with medical cross */}
      <svg width={s.iconSize} height={s.iconSize} viewBox="0 0 40 40" fill="none">
        <rect width="40" height="40" rx="10" fill="#1E2A6E" />
        <path d="M12 28V12h3l10 12V12h3v16h-3L15 16v12h-3z" fill="white" />
        <rect x="18" y="8" width="4" height="10" rx="1" fill="#3B82F6" opacity="0.9" />
        <rect x="15" y="11" width="10" height="4" rx="1" fill="#3B82F6" opacity="0.9" />
      </svg>
      {/* Text */}
      <div className="flex flex-col leading-none">
        <span
          className="font-bold tracking-tight text-primary"
          style={{ fontSize: s.fontSize }}
        >
          NANO MEDICAL
        </span>
        {size !== "sm" && (
          <span
            className="font-medium tracking-wider text-text-muted"
            style={{ fontSize: s.fontSize * 0.5 }}
          >
            CLINIC
          </span>
        )}
      </div>
    </div>
  );
}
