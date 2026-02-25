import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { Phone } from "lucide-react";
import { RipplePulse } from "../components/feedback/RipplePulse";
import { IconCircle } from "../components/ui/IconCircle";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";

// ── Main screen ─────────────────────────────────────────────

interface HandOffScreenProps {
  onCancel: () => void;
}

export function HandOffScreen({ onCancel }: HandOffScreenProps) {
  const { t } = useTranslation();

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <HeaderBar title="" />

      {/* ── Center content ── */}
      <div className="flex flex-1 flex-col items-center justify-center px-12">
        {/* Animated phone icon with ripple */}
        <RipplePulse active className="mb-8">
          <IconCircle size="lg" className="bg-amber-50">
            <Phone className="h-8 w-8 text-amber-500" />
          </IconCircle>
        </RipplePulse>

        {/* Calling text with animated dots */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="text-h1 tracking-heading text-text-primary"
        >
          <CallingText />
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.4 }}
          className="mt-3 text-body-lg text-text-muted"
        >
          {t("common.loading")}
        </motion.p>
      </div>

      <BottomNav onBack={onCancel} showHome={false} />
    </motion.div>
  );
}

// Animated "Calling..." text
function CallingText() {
  const { t } = useTranslation();
  // Use a generic "calling" message — the loading key works well here
  const baseText = t("loading.checkIn").replace("...", "");

  return (
    <span>
      {baseText}
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          animate={{ opacity: [0, 1, 0] }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            delay: i * 0.3,
            ease: "easeInOut",
          }}
        >
          .
        </motion.span>
      ))}
    </span>
  );
}
