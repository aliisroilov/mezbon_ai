import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import { RefreshCw } from "lucide-react";
import { AIPromptBar } from "../components/ai/AIPromptBar";
import { LoadingMessage } from "../components/feedback/LoadingMessage";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";
import { Button } from "../components/ui/Button";
import { getMedicalIcon } from "../components/icons/MedicalIcons";
import { useSessionStore } from "../store/sessionStore";
import { useVoiceChat } from "../hooks/useVoiceChat";
import { cn } from "../lib/cn";
import type { Department } from "../types";
import { sounds } from "../utils/sounds";

// ── Department card ─────────────────────────────────────────

interface DepartmentCardProps {
  department: Department;
  index: number;
  selected: boolean;
  onSelect: () => void;
}

function DepartmentCard({ department, index, selected, onSelect }: DepartmentCardProps) {
  const { t } = useTranslation();

  const detailParts: string[] = [];
  if (department.floor != null) {
    detailParts.push(t("department.floor", { floor: department.floor }));
  }
  if (department.room_number) {
    detailParts.push(t("department.room", { room: department.room_number }));
  }
  const detailLine = detailParts.join(" • ");

  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        delay: 0.15 + index * 0.06,
        duration: 0.4,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.97 }}
      onClick={onSelect}
      aria-label={t("accessibility.selectDepartment", { name: department.name })}
      className={cn(
        "group relative flex w-full items-start gap-5 rounded-card bg-white p-6 text-left shadow-card",
        "transition-shadow duration-200 hover:shadow-card-hover",
        "focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-primary/40 focus-visible:ring-offset-4",
        selected && "border-l-4 border-l-primary bg-primary-50",
      )}
    >
      {/* Teal left border — slides in on hover/select */}
      {!selected && (
        <motion.div
          className="absolute left-0 top-4 bottom-4 w-1 rounded-full bg-primary"
          initial={{ scaleY: 0 }}
          whileHover={{ scaleY: 1 }}
          transition={{ duration: 0.2 }}
          style={{ originY: 0.5 }}
        />
      )}

      {/* Icon */}
      {(() => {
        const Icon = getMedicalIcon(department.name);
        return (
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary-50 text-primary">
            <Icon className="h-7 w-7" />
          </div>
        );
      })()}

      {/* Text */}
      <div className="min-w-0 flex-1">
        <p className="text-h3 tracking-heading text-text-primary">{department.name}</p>
        {detailLine && (
          <p className="mt-1 text-caption text-text-muted">{detailLine}</p>
        )}
        {department.doctor_count > 0 && (
          <div className="mt-2 flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-success" />
            <span className="text-caption text-text-muted">
              {t("department.doctors", { count: department.doctor_count })}
            </span>
          </div>
        )}
      </div>

      {/* Arrow hint */}
      <motion.div
        className="shrink-0 self-center text-text-muted"
        initial={{ x: 0, opacity: 0.4 }}
        whileHover={{ x: 4, opacity: 1 }}
        transition={{ duration: 0.15 }}
      >
        <svg
          viewBox="0 0 20 20"
          width={20}
          height={20}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
        >
          <path d="M7 4l6 6-6 6" />
        </svg>
      </motion.div>
    </motion.button>
  );
}

// ── Main screen ─────────────────────────────────────────────

interface DepartmentSelectScreenProps {
  onSelectDepartment: (department: Department) => void;
  onBack: () => void;
}

export function DepartmentSelectScreen({
  onSelectDepartment,
  onBack,
}: DepartmentSelectScreenProps) {
  const { t } = useTranslation();
  const departments = useSessionStore((s) => s.departments);
  const aiMessage = useSessionStore((s) => s.aiMessage);

  const voice = useVoiceChat({ autoStartDelay: 800 });

  // 5s loading timeout — show empty state instead of infinite spinner
  const [loadingTimedOut, setLoadingTimedOut] = useState(false);
  useEffect(() => {
    if (departments.length > 0) { setLoadingTimedOut(false); return; }
    const timer = setTimeout(() => setLoadingTimedOut(true), 5000);
    return () => clearTimeout(timer);
  }, [departments.length]);

  const responseText = aiMessage || t("department.subtitle");

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* ── Header ── */}
      <HeaderBar title={t("department.title")} />

      {/* ── AI prompt bar ── */}
      <div className="px-8 pb-4">
        <AIPromptBar
          message={responseText}
          avatarState={voice.avatarState}
          voiceState={voice.voiceState}
          onVoiceClick={voice.toggleMic}
        />
      </div>

      {/* ── Department cards ── */}
      <div className="flex-1 overflow-y-auto px-8 pb-6 scrollbar-hide">
        <AnimatePresence mode="wait">
          {departments.length > 0 ? (
            <div className="grid grid-cols-2 gap-4">
              {departments.map((dept, i) => {
                const isLastOdd =
                  i === departments.length - 1 && departments.length % 2 !== 0;
                return (
                  <div
                    key={dept.id}
                    className={cn(isLastOdd && "col-span-2 mx-auto w-1/2")}
                  >
                    <DepartmentCard
                      department={dept}
                      index={i}
                      selected={false}
                      onSelect={() => { sounds.tap(); onSelectDepartment(dept); }}
                    />
                  </div>
                );
              })}
            </div>
          ) : loadingTimedOut ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center gap-4 py-16"
            >
              <p className="text-body text-text-muted">{t("loading.notFound", { defaultValue: "Ma'lumot topilmadi" })}</p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => { setLoadingTimedOut(false); onBack(); }}
                iconLeft={<RefreshCw className="h-4 w-4" />}
              >
                {t("common.retry", { defaultValue: "Qayta urinish" })}
              </Button>
            </motion.div>
          ) : (
            <LoadingMessage message={t("loading.departments")} />
          )}
        </AnimatePresence>
      </div>

      {/* ── Bottom nav ── */}
      <BottomNav onBack={onBack} />
    </motion.div>
  );
}
