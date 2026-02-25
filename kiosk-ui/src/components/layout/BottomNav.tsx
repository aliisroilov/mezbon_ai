import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { ArrowLeft, Home } from "lucide-react";
import { Button } from "../ui/Button";
import { useSessionStore } from "../../store/sessionStore";
import { cn } from "../../lib/cn";

interface BottomNavProps {
  onBack?: () => void;
  onHome?: () => void;
  backLabel?: string;
  backDisabled?: boolean;
  showHome?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function BottomNav({
  onBack,
  onHome,
  backLabel,
  backDisabled,
  showHome = true,
  className,
  children,
}: BottomNavProps) {
  const { t } = useTranslation();
  const resetSession = useSessionStore((s) => s.resetSession);

  const handleHome = useCallback(() => {
    if (onHome) {
      onHome();
    } else {
      resetSession();
    }
  }, [onHome, resetSession]);

  return (
    <div
      className={cn(
        "flex h-[100px] shrink-0 items-center justify-between border-t border-slate-200/60 bg-white/80 px-8 backdrop-blur-sm",
        className,
      )}
    >
      {/* Back button */}
      {onBack ? (
        <Button
          variant="secondary"
          size="md"
          onClick={onBack}
          disabled={backDisabled}
          iconLeft={<ArrowLeft className="h-5 w-5" />}
        >
          {backLabel || t("common.back")}
        </Button>
      ) : (
        <div className="w-[140px]" />
      )}

      {/* Center content (optional progress indicator) */}
      {children && <div className="flex-1 flex items-center justify-center">{children}</div>}

      {/* Home button */}
      {showHome ? (
        <Button
          variant="ghost"
          size="md"
          onClick={handleHome}
          iconLeft={<Home className="h-5 w-5" />}
        >
          {t("common.home", { defaultValue: "Asosiy" })}
        </Button>
      ) : (
        <div className="w-[140px]" />
      )}
    </div>
  );
}
