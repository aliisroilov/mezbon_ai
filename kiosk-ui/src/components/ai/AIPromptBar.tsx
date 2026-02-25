import { motion } from "framer-motion";
import { AIAvatar, type AvatarState } from "./AIAvatar";
import { VoiceIndicator, type VoiceState } from "./VoiceIndicator";
import { cn } from "../../lib/cn";

interface AIPromptBarProps {
  /** The AI message text to display */
  message: string;
  /** Avatar animation state */
  avatarState?: AvatarState;
  /** Voice indicator state */
  voiceState?: VoiceState;
  /** Voice toggle callback */
  onVoiceClick?: () => void;
  className?: string;
}

/**
 * Compact AI prompt bar for inner screens.
 * Shows: [Avatar 48px] [Message text] [Voice indicator]
 *
 * Replaces the broken pattern of scale(0.3) AIAvatar
 * + separate ResponseBubble + separate VoiceIndicator that caused
 * overlap issues on every screen.
 */
export function AIPromptBar({
  message,
  avatarState = "idle",
  voiceState = "inactive",
  onVoiceClick,
  className,
}: AIPromptBarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className={cn(
        "flex items-center gap-4 rounded-2xl bg-white/80 backdrop-blur-sm",
        "border border-border/50 px-5 py-3.5 shadow-card",
        className,
      )}
    >
      {/* Small avatar — uses overflow:hidden to properly clip */}
      <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-full">
        <div
          style={{
            transform: "scale(0.24)",
            transformOrigin: "top left",
            width: 200,
            height: 200,
            position: "absolute",
            top: 0,
            left: 0,
          }}
        >
          <AIAvatar state={avatarState} />
        </div>
      </div>

      {/* Message text — takes remaining space, NO truncation */}
      <p className="min-w-0 flex-1 text-[17px] leading-snug text-text-primary">
        {message}
      </p>

      {/* Voice indicator — compact */}
      <div className="shrink-0">
        <VoiceIndicator state={voiceState} onClick={onVoiceClick} />
      </div>
    </motion.div>
  );
}
