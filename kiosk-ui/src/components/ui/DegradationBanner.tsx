import { motion, AnimatePresence } from "framer-motion";
import { useSessionStore } from "../../store/sessionStore";

/**
 * Shows a non-intrusive pill indicator when voice or AI services are unavailable.
 * Positioned below the header bar as a subtle top-right pill — does NOT overlap content.
 */
export function DegradationBanner() {
  const voiceAvailable = useSessionStore((s) => s.voiceAvailable);
  const aiAvailable = useSessionStore((s) => s.aiAvailable);

  const showVoiceBanner = !voiceAvailable;
  const showAiBanner = !aiAvailable;

  if (!showVoiceBanner && !showAiBanner) return null;

  const message = showVoiceBanner
    ? "Ovozli rejim vaqtincha ishlamayapti"
    : "AI yordamchi vaqtincha ishlamayapti";

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className="fixed top-2 right-2 z-50 flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1.5 text-xs text-amber-700 shadow-sm"
      >
        <div className="h-2 w-2 animate-pulse rounded-full bg-amber-500" />
        {message}
      </motion.div>
    </AnimatePresence>
  );
}
