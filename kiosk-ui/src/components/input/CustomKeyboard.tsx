import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Delete, ArrowBigUp, X } from "lucide-react";
import { cn } from "../../lib/cn";

interface CustomKeyboardProps {
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
  label?: string;
}

// Row 1: q w e r t y u i o p oʻ
// Row 2: a s d f g gʻ h j k l
// Row 3: ⇧ z x c v b n m sh ch ⌫
// Row 4: LAT/КИР [SPACE] ✕
const LATIN_ROWS = [
  ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "oʻ"],
  ["a", "s", "d", "f", "g", "gʻ", "h", "j", "k", "l"],
  ["z", "x", "c", "v", "b", "n", "m", "sh", "ch"],
];

// Row 1: й ц у к е н г ш щ з х ъ
// Row 2: ф ы в а п р о л д ж э
// Row 3: ⇧ я ч с м и т ь б ю ў ⌫
// Row 4: LAT/КИР [SPACE] ✕
const CYRILLIC_ROWS = [
  ["й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х", "ъ"],
  ["ф", "ы", "в", "а", "п", "р", "о", "л", "д", "ж", "э"],
  ["я", "ч", "с", "м", "и", "т", "ь", "б", "ю", "ў"],
];

type KeyboardMode = "latin" | "cyrillic";

export function CustomKeyboard({
  value,
  onChange,
  placeholder,
  label,
}: CustomKeyboardProps) {
  const [mode, setMode] = useState<KeyboardMode>("latin");
  const [shifted, setShifted] = useState(true); // Start with caps for name

  const rows = mode === "latin" ? LATIN_ROWS : CYRILLIC_ROWS;

  const handleKey = useCallback(
    (key: string) => {
      const char = shifted ? key.toUpperCase() : key;
      onChange(value + char);
      // Auto-unshift after typing (single-press shift)
      if (shifted && value.length > 0) {
        setShifted(false);
      }
    },
    [value, onChange, shifted],
  );

  const handleBackspace = useCallback(() => {
    onChange(value.slice(0, -1));
  }, [value, onChange]);

  const handleClearAll = useCallback(() => {
    onChange("");
    setShifted(true);
  }, [onChange]);

  const handleSpace = useCallback(() => {
    if (value.length > 0 && !value.endsWith(" ")) {
      onChange(value + " ");
      // Auto-capitalize after space (for names like "Ism Familiya")
      setShifted(true);
    }
  }, [value, onChange]);

  const toggleMode = useCallback(() => {
    setMode((m) => (m === "latin" ? "cyrillic" : "latin"));
  }, []);

  const toggleShift = useCallback(() => {
    setShifted((s) => !s);
  }, []);

  return (
    <div className="flex flex-col gap-2">
      {label && (
        <label className="text-caption font-semibold text-text-body">
          {label}
        </label>
      )}

      {/* Display field — inputMode="none" prevents system keyboard */}
      <div className="flex h-touch-md items-center rounded-input border border-border bg-white px-4">
        <input
          type="text"
          inputMode="none"
          readOnly
          value={value}
          placeholder={placeholder ?? ""}
          className="w-full bg-transparent text-[22px] font-semibold text-text-primary outline-none placeholder:text-text-muted"
        />
      </div>

      {/* Keyboard */}
      <div className="flex flex-col gap-1.5 pt-2">
        {rows.map((row, rowIdx) => (
          <div key={rowIdx} className="flex justify-center gap-1">
            {/* Shift on last row start */}
            {rowIdx === 2 && (
              <motion.button
                whileTap={{ scale: 0.9 }}
                onClick={toggleShift}
                className={cn(
                  "flex h-[48px] w-[48px] shrink-0 items-center justify-center rounded-xl transition-all duration-150",
                  shifted
                    ? "bg-primary text-white"
                    : "bg-slate-100 text-text-body",
                )}
              >
                <ArrowBigUp className="h-5 w-5" />
              </motion.button>
            )}

            {row.map((key) => (
              <motion.button
                key={key}
                whileTap={{ scale: 0.92 }}
                onClick={() => handleKey(key)}
                className="flex h-[48px] min-w-[40px] flex-1 items-center justify-center rounded-xl bg-white text-[18px] font-medium text-text-primary shadow-sm transition-all duration-100 active:bg-primary-50"
              >
                {shifted ? key.toUpperCase() : key}
              </motion.button>
            ))}

            {/* Backspace on last row end */}
            {rowIdx === 2 && (
              <motion.button
                whileTap={{ scale: 0.9 }}
                onClick={handleBackspace}
                className="flex h-[48px] w-[48px] shrink-0 items-center justify-center rounded-xl bg-slate-100 text-text-body transition-all duration-150"
              >
                <Delete className="h-5 w-5" />
              </motion.button>
            )}
          </div>
        ))}

        {/* Bottom row: mode toggle, space, clear all */}
        <div className="flex justify-center gap-1.5">
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={toggleMode}
            className="flex h-[48px] w-[72px] shrink-0 items-center justify-center rounded-xl bg-slate-100 text-caption font-semibold text-text-body transition-all duration-150"
          >
            {mode === "latin" ? "КИР" : "LAT"}
          </motion.button>

          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={handleSpace}
            className="flex h-[48px] flex-1 items-center justify-center rounded-xl bg-white text-[16px] text-text-muted shadow-sm transition-all duration-100 active:bg-primary-50"
          >
            ␣
          </motion.button>

          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={handleClearAll}
            className="flex h-[48px] w-[48px] shrink-0 items-center justify-center rounded-xl bg-red-50 text-danger transition-all duration-150"
          >
            <X className="h-5 w-5" />
          </motion.button>
        </div>
      </div>
    </div>
  );
}
