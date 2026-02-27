import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";
import { NumPad } from "./NumPad";

interface PhoneInputProps {
  value: string;
  onChange: (val: string) => void;
  onDone?: () => void;
}

export function PhoneInput({ value, onChange, onDone }: PhoneInputProps) {
  const { t } = useTranslation();

  const formatted = useMemo(() => {
    // Format: +998 (XX) XXX-XX-XX
    const digits = value.replace(/\D/g, "");
    if (digits.length === 0) return "";
    const parts: string[] = [];
    if (digits.length > 0) parts.push("(" + digits.slice(0, 2));
    if (digits.length >= 2) parts[0] += ")";
    if (digits.length > 2) parts.push(digits.slice(2, 5));
    if (digits.length > 5) parts.push(digits.slice(5, 7));
    if (digits.length > 7) parts.push(digits.slice(7, 9));
    return parts.join("-");
  }, [value]);

  const isComplete = value.length === 9;

  return (
    <div className="flex flex-col gap-3">
      <label className="text-caption font-semibold text-text-body">
        {t("common.phone")}
      </label>

      {/* Display: +998 prefix + formatted number */}
      <div className="flex h-touch-lg items-center justify-center rounded-card border border-border bg-white px-6">
        <span className="mr-2 text-h2 text-text-muted">+998</span>
        <span className="text-[32px] font-bold tracking-wider text-text-primary">
          {formatted || (
            <span className="text-text-muted">(__)___-__-__</span>
          )}
        </span>
      </div>

      <NumPad
        onDigit={(d) => {
          if (value.length < 9) onChange(value + d);
        }}
        onBackspace={() => onChange(value.slice(0, -1))}
        onClear={() => onChange("")}
      />

      {/* "Tayyor" (Done) button — visible when 9 digits entered */}
      {onDone && isComplete && (
        <Button
          variant="primary"
          size="lg"
          className="mt-2 w-full"
          onClick={onDone}
        >
          {t("common.confirm")}
        </Button>
      )}
    </div>
  );
}
