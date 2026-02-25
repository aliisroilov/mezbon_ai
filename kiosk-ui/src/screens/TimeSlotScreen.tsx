import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import { ArrowLeft, ArrowRight, RefreshCw } from "lucide-react";
import { AIPromptBar } from "../components/ai/AIPromptBar";
import { Button } from "../components/ui/Button";
import { HeaderBar } from "../components/layout/HeaderBar";
import { useSessionStore } from "../store/sessionStore";
import { useVoiceChat } from "../hooks/useVoiceChat";
import { LoadingMessage } from "../components/feedback/LoadingMessage";
import { cn } from "../lib/cn";
import { sounds } from "../utils/sounds";
import type { TimeSlot } from "../types";

// ── Day name helpers ────────────────────────────────────────

const DAY_KEYS_SHORT: Record<number, string> = {
  0: "Ya",
  1: "Du",
  2: "Se",
  3: "Ch",
  4: "Pa",
  5: "Ju",
  6: "Sh",
};

const MONTH_KEYS: string[] = [
  "months.january",
  "months.february",
  "months.march",
  "months.april",
  "months.may",
  "months.june",
  "months.july",
  "months.august",
  "months.september",
  "months.october",
  "months.november",
  "months.december",
];

function getNext7Days(): Date[] {
  const days: Date[] = [];
  const now = new Date();
  for (let i = 0; i < 7; i++) {
    const d = new Date(now);
    d.setDate(now.getDate() + i);
    d.setHours(0, 0, 0, 0);
    days.push(d);
  }
  return days;
}

function formatDateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

// ── Date pill ───────────────────────────────────────────────

interface DatePillProps {
  date: Date;
  isToday: boolean;
  isSelected: boolean;
  hasSlots: boolean;
  onSelect: () => void;
}

function DatePill({ date, isToday, isSelected, hasSlots, onSelect }: DatePillProps) {
  const { t } = useTranslation();
  const dayLabel = isToday ? t("days.today") : DAY_KEYS_SHORT[date.getDay()];
  const monthKey = MONTH_KEYS[date.getMonth()] ?? "months.january";
  const monthShort = t(monthKey).slice(0, 3).toLowerCase();

  return (
    <motion.button
      whileTap={hasSlots ? { scale: 0.95 } : undefined}
      onClick={hasSlots ? onSelect : undefined}
      disabled={!hasSlots}
      className={cn(
        "flex w-20 shrink-0 snap-center flex-col items-center gap-1 rounded-xl py-3 transition-all duration-200",
        isSelected
          ? "bg-primary text-white shadow-button"
          : hasSlots
            ? "bg-white text-text-primary border border-border hover:border-primary/30"
            : "bg-slate-50 text-text-muted",
        !hasSlots && "opacity-60",
      )}
    >
      <span className={cn("text-caption font-medium", isSelected && "text-white/80")}>
        {dayLabel}
      </span>
      <span className={cn("text-h2 font-bold", !hasSlots && "line-through")}>
        {date.getDate()}
      </span>
      <span className={cn("text-caption", isSelected ? "text-white/70" : "text-text-muted")}>
        {monthShort}
      </span>
    </motion.button>
  );
}

// ── Time slot pill ──────────────────────────────────────────

interface SlotPillProps {
  slot: TimeSlot;
  isSelected: boolean;
  isPast: boolean;
  onSelect: () => void;
}

function SlotPill({ slot, isSelected, isPast, onSelect }: SlotPillProps) {
  const time = slot.start_time.slice(0, 5); // "HH:MM"
  const isDisabled = !slot.is_available || isPast;

  return (
    <motion.button
      whileTap={!isDisabled ? { scale: 0.95 } : undefined}
      onClick={!isDisabled ? onSelect : undefined}
      disabled={isDisabled}
      aria-label={time}
      className={cn(
        "flex h-12 items-center justify-center rounded-full text-body font-medium transition-all duration-200",
        isSelected
          ? "bg-primary text-white shadow-button scale-105"
          : slot.is_available && !isPast
            ? "bg-white border border-primary-100 text-primary hover:border-primary hover:bg-primary-50"
            : "bg-slate-100 text-text-muted",
        !slot.is_available && "line-through",
        isPast && "opacity-50",
        isDisabled && "pointer-events-none",
      )}
    >
      {time}
      {isSelected && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="ml-1.5"
        >
          ✓
        </motion.span>
      )}
    </motion.button>
  );
}

// ── Main screen ─────────────────────────────────────────────

interface TimeSlotScreenProps {
  onSelectSlot: (slot: TimeSlot, date: string) => void;
  onBack: () => void;
}

export function TimeSlotScreen({ onSelectSlot, onBack }: TimeSlotScreenProps) {
  const { t } = useTranslation();
  const currentDoctor = useSessionStore((s) => s.currentDoctor);
  const currentService = useSessionStore((s) => s.currentService);
  const availableSlots = useSessionStore((s) => s.availableSlots);
  const aiMessage = useSessionStore((s) => s.aiMessage);

  const voice = useVoiceChat({ autoStartDelay: 800 });

  const dates = useMemo(() => getNext7Days(), []);
  const today = useMemo(() => formatDateKey(new Date()), []);

  const [activeDateIdx, setActiveDateIdx] = useState(0);
  const [selectedSlotState, setSelectedSlotState] = useState<TimeSlot | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const activeDate = dates[activeDateIdx] ?? dates[0]!;
  const activeDateKey = formatDateKey(activeDate);
  const isActiveToday = activeDateKey === today;

  // 3s loading timeout — show empty state instead of infinite spinner
  const [loadingTimedOut, setLoadingTimedOut] = useState(false);
  useEffect(() => {
    if (availableSlots.length > 0) { setLoadingTimedOut(false); return; }
    const timer = setTimeout(() => setLoadingTimedOut(true), 5000);
    return () => clearTimeout(timer);
  }, [availableSlots.length]);

  // Filter slots to only show available ones
  const filteredSlots = useMemo(() => {
    return availableSlots.filter((slot) => slot.is_available !== false);
  }, [availableSlots]);

  const isPastSlot = useCallback(
    (slot: TimeSlot) => {
      if (!isActiveToday) return false;
      const now = new Date();
      const parts = slot.start_time.split(":").map(Number);
      const h = parts[0] ?? 0;
      const m = parts[1] ?? 0;
      return h < now.getHours() || (h === now.getHours() && m <= now.getMinutes());
    },
    [isActiveToday],
  );

  const handleDateSelect = useCallback(
    (idx: number) => {
      setActiveDateIdx(idx);
      setSelectedSlotState(null);
    },
    [],
  );

  const handleSlotSelect = useCallback(
    (slot: TimeSlot) => {
      sounds.tap();
      setSelectedSlotState(slot);
    },
    [],
  );

  const handleContinue = useCallback(() => {
    if (selectedSlotState) {
      onSelectSlot(selectedSlotState, activeDateKey);
    }
  }, [selectedSlotState, activeDateKey, onSelectSlot]);

  // Scroll selected date into view
  useEffect(() => {
    if (scrollRef.current) {
      const el = scrollRef.current.children[activeDateIdx] as HTMLElement | undefined;
      el?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
    }
  }, [activeDateIdx]);

  const priceFormatted = currentService
    ? new Intl.NumberFormat("uz-UZ").format(currentService.price_uzs)
    : "";

  const summaryText = selectedSlotState
    ? `${activeDate.getDate()}-${t(MONTH_KEYS[activeDate.getMonth()] ?? "months.january").toLowerCase()}, ${selectedSlotState.start_time.slice(0, 5)} — ${currentService?.name ?? ""} (${priceFormatted} ${t("common.somCurrency")})`
    : "";

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* Header */}
      <HeaderBar title={t("slot.title")} />

      {/* ── Selected info strip ── */}
      {currentDoctor && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.3 }}
          className="mx-8 mb-5 flex items-center gap-4 rounded-xl bg-primary-50 p-4"
        >
          {/* Doctor mini avatar */}
          {currentDoctor.photo_url ? (
            <img
              src={currentDoctor.photo_url}
              alt={currentDoctor.full_name}
              className="h-10 w-10 rounded-full object-cover"
            />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-caption font-bold text-white">
              {currentDoctor.full_name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-body font-semibold text-text-primary">
              {currentDoctor.full_name}
            </p>
            {currentService && (
              <p className="truncate text-caption text-text-muted">
                {currentService.name} • {priceFormatted} {t("common.somCurrency")}
              </p>
            )}
          </div>
        </motion.div>
      )}

      {/* ── AI prompt bar ── */}
      <div className="px-8 pb-4">
        <AIPromptBar
          message={aiMessage || t("slot.title")}
          avatarState={voice.avatarState}
          voiceState={voice.voiceState}
          onVoiceClick={voice.toggleMic}
        />
      </div>

      {/* ── Date selector (horizontal scroll) ── */}
      <div className="px-8 pb-6">
        <p className="mb-3 text-caption font-semibold text-text-muted">
          {t("slot.selectDate")}
        </p>
        <div
          ref={scrollRef}
          className="flex gap-3 overflow-x-auto pb-2 scroll-smooth snap-x snap-mandatory scrollbar-hide"
        >
          {dates.map((date, i) => (
            <DatePill
              key={i}
              date={date}
              isToday={formatDateKey(date) === today}
              isSelected={i === activeDateIdx}
              hasSlots={true}
              onSelect={() => handleDateSelect(i)}
            />
          ))}
        </div>
      </div>

      {/* ── Time slots grid ── */}
      <div className="flex-1 overflow-y-auto px-8 pb-4 scrollbar-hide">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeDateKey}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.25 }}
          >
            {filteredSlots.length > 0 ? (
              <div className="grid grid-cols-3 gap-3">
                {filteredSlots.map((slot, i) => (
                  <SlotPill
                    key={`${activeDateKey}-${slot.start_time}-${i}`}
                    slot={slot}
                    isSelected={
                      selectedSlotState?.start_time === slot.start_time &&
                      selectedSlotState?.end_time === slot.end_time
                    }
                    isPast={isPastSlot(slot)}
                    onSelect={() => handleSlotSelect(slot)}
                  />
                ))}
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
              <LoadingMessage message={t("loading.slots")} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* ── Bottom sticky area ── */}
      <AnimatePresence>
        {selectedSlotState && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.3 }}
            className="border-t border-border/50 bg-white/80 px-8 py-6 backdrop-blur-sm"
          >
            <p className="mb-3 text-center text-body text-text-body">
              {summaryText}
            </p>
            <div className="flex items-center justify-between gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={onBack}
                iconLeft={<ArrowLeft className="h-4 w-4" />}
              >
                {t("common.back")}
              </Button>
              <Button
                variant="primary"
                size="lg"
                className="flex-1"
                onClick={handleContinue}
                iconRight={<ArrowRight className="h-5 w-5" />}
              >
                {t("common.next")}
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Placeholder bottom when no slot selected */}
      {!selectedSlotState && (
        <div className="flex items-center justify-between px-8 pb-8">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            iconLeft={<ArrowLeft className="h-4 w-4" />}
          >
            {t("common.back")}
          </Button>
          <Button
            variant="primary"
            size="lg"
            disabled
          >
            {t("common.next")}
          </Button>
        </div>
      )}
    </motion.div>
  );
}
