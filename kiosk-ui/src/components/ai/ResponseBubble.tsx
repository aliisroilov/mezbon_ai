import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../../lib/cn";
import { TypewriterText } from "../feedback/TypewriterText";

interface ActionSuggestion {
  label: string;
  onClick: () => void;
}

interface ResponseBubbleProps {
  /** The AI's response text */
  message: string;
  /** Unique key to detect new messages (e.g. timestamp or message ID) */
  messageKey?: string | number;
  /** Optional action button below the text */
  action?: ActionSuggestion;
  /** Whether to animate with typewriter effect (true for new messages) */
  animate?: boolean;
  /** Called when typewriter finishes */
  onAnimationComplete?: () => void;
  className?: string;
}

const bubbleVariants = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring" as const,
      stiffness: 300,
      damping: 25,
      mass: 0.8,
    },
  },
  exit: {
    opacity: 0,
    y: -12,
    scale: 0.97,
    transition: { duration: 0.2, ease: "easeIn" as const },
  },
};

export function ResponseBubble({
  message,
  messageKey,
  action,
  animate: shouldAnimate = true,
  onAnimationComplete,
  className,
}: ResponseBubbleProps) {
  const [showAction, setShowAction] = useState(!shouldAnimate);
  const prevKeyRef = useRef(messageKey);

  // Reset action visibility when message changes
  useEffect(() => {
    if (messageKey !== prevKeyRef.current) {
      setShowAction(false);
      prevKeyRef.current = messageKey;
    }
  }, [messageKey]);

  // If not animating, show action immediately
  useEffect(() => {
    if (!shouldAnimate && action) {
      setShowAction(true);
    }
  }, [shouldAnimate, action]);

  function handleTypewriterComplete() {
    if (action) setShowAction(true);
    onAnimationComplete?.();
  }

  if (!message) return null;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={messageKey ?? message}
        variants={bubbleVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        className={cn(
          "mx-auto w-full",
          className,
        )}
      >
        <div
          className={cn(
            "relative rounded-2xl bg-white p-6 shadow-card",
            "border border-border/50",
          )}
        >
          {/* Message text */}
          <div className="pt-1">
            {shouldAnimate ? (
              <TypewriterText
                text={message}
                delayMs={30}
                onComplete={handleTypewriterComplete}
                className="text-[22px] leading-relaxed text-text-primary"
              />
            ) : (
              <p className="text-[22px] leading-relaxed text-text-primary">
                {message}
              </p>
            )}
          </div>

          {/* Action suggestion */}
          <AnimatePresence>
            {action && showAction && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 8 }}
                transition={{ duration: 0.25, delay: 0.1 }}
                className="mt-4"
              >
                <motion.button
                  whileTap={{ scale: 0.96 }}
                  onClick={action.onClick}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full",
                    "bg-primary-50 px-5 py-2.5",
                    "text-[15px] font-semibold text-primary",
                    "border border-primary/15",
                    "transition-colors duration-150 hover:bg-primary-light",
                    "active:bg-primary/10",
                  )}
                >
                  {action.label}
                  <svg
                    viewBox="0 0 16 16"
                    width={14}
                    height={14}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    strokeLinecap="round"
                  >
                    <path d="M3 8h10M9 4l4 4-4 4" />
                  </svg>
                </motion.button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
