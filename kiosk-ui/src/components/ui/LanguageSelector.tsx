import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { cn } from "../../lib/cn";
import type { Language } from "../../types";

const LANGUAGES: { code: Language; label: string; flag: string }[] = [
  { code: "uz", label: "O'zbek", flag: "🇺🇿" },
  { code: "ru", label: "Русский", flag: "🇷🇺" },
  { code: "en", label: "English", flag: "🇬🇧" },
];

interface LanguageSelectorProps {
  className?: string;
}

export function LanguageSelector({ className }: LanguageSelectorProps) {
  const { i18n } = useTranslation();
  const currentLang = i18n.language as Language;

  function handleChange(code: Language) {
    i18n.changeLanguage(code);
  }

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {LANGUAGES.map(({ code, label }) => (
        <motion.button
          key={code}
          whileTap={{ scale: 0.93 }}
          onClick={() => handleChange(code)}
          aria-label={`Switch to ${label}`}
          className={cn(
            "flex h-11 min-w-[52px] items-center justify-center rounded-full px-3 text-[15px] font-semibold",
            "transition-all duration-200",
            currentLang === code
              ? "bg-primary text-white shadow-button"
              : "bg-white/80 text-text-body hover:bg-white shadow-sm",
          )}
        >
          {code.toUpperCase()}
        </motion.button>
      ))}
    </div>
  );
}
