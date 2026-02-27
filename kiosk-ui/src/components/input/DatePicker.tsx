import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { Calendar } from "lucide-react";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { cn } from "../../lib/cn";

interface DatePickerProps {
  value: string; // YYYY-MM-DD or ""
  onChange: (val: string) => void;
  label?: string;
}

const ITEM_HEIGHT = 56;
const VISIBLE_ITEMS = 5;
const CENTER_OFFSET = Math.floor(VISIBLE_ITEMS / 2);
const MAX_YEAR = 2024;
const MIN_YEAR = 1940;

const MONTH_KEYS = [
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

// ── Scroll column ──────────────────────────────────────────

interface ScrollColumnProps {
  items: { value: number; label: string }[];
  selected: number;
  onSelect: (val: number) => void;
}

function ScrollColumn({ items, selected, onSelect }: ScrollColumnProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isScrolling = useRef(false);
  const scrollTimeout = useRef<ReturnType<typeof setTimeout>>();

  const selectedIndex = items.findIndex((item) => item.value === selected);

  // Scroll to selected item on mount and when selected changes externally
  useEffect(() => {
    const el = containerRef.current;
    if (!el || isScrolling.current) return;
    const targetScroll = selectedIndex * ITEM_HEIGHT;
    el.scrollTo({ top: targetScroll, behavior: "smooth" });
  }, [selectedIndex]);

  const handleScroll = useCallback(() => {
    isScrolling.current = true;
    clearTimeout(scrollTimeout.current);
    scrollTimeout.current = setTimeout(() => {
      const el = containerRef.current;
      if (!el) return;
      const index = Math.round(el.scrollTop / ITEM_HEIGHT);
      const clamped = Math.max(0, Math.min(index, items.length - 1));
      // Snap to nearest item
      el.scrollTo({ top: clamped * ITEM_HEIGHT, behavior: "smooth" });
      if (items[clamped] && items[clamped].value !== selected) {
        onSelect(items[clamped].value);
      }
      isScrolling.current = false;
    }, 100);
  }, [items, selected, onSelect]);

  return (
    <div className="relative flex-1">
      {/* Highlight band for center item */}
      <div
        className="pointer-events-none absolute left-0 right-0 z-10 rounded-xl bg-primary-50 border border-primary/20"
        style={{
          top: CENTER_OFFSET * ITEM_HEIGHT,
          height: ITEM_HEIGHT,
        }}
      />

      {/* Fade edges */}
      <div className="pointer-events-none absolute left-0 right-0 top-0 z-20 h-16 bg-gradient-to-b from-white to-transparent" />
      <div className="pointer-events-none absolute bottom-0 left-0 right-0 z-20 h-16 bg-gradient-to-t from-white to-transparent" />

      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="scrollbar-hide overflow-y-auto"
        style={{
          height: VISIBLE_ITEMS * ITEM_HEIGHT,
          scrollSnapType: "y mandatory",
        }}
      >
        {/* Top padding */}
        <div style={{ height: CENTER_OFFSET * ITEM_HEIGHT }} />

        {items.map((item) => {
          const isSelected = item.value === selected;
          return (
            <div
              key={item.value}
              onClick={() => onSelect(item.value)}
              className={cn(
                "flex cursor-pointer items-center justify-center transition-all duration-150",
                isSelected
                  ? "text-[20px] font-bold text-primary"
                  : "text-[17px] font-medium text-text-muted",
              )}
              style={{
                height: ITEM_HEIGHT,
                scrollSnapAlign: "start",
              }}
            >
              {item.label}
            </div>
          );
        })}

        {/* Bottom padding */}
        <div style={{ height: CENTER_OFFSET * ITEM_HEIGHT }} />
      </div>
    </div>
  );
}

// ── DatePicker ─────────────────────────────────────────────

export function DatePicker({ value, onChange, label }: DatePickerProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  // Parse initial value or use defaults
  const parsed = useMemo(() => {
    if (value) {
      const [y, m, d] = value.split("-").map(Number);
      return { day: d || 1, month: (m || 1) - 1, year: y || 1990 };
    }
    return { day: 1, month: 0, year: 1990 };
  }, [value]);

  const [day, setDay] = useState(parsed.day);
  const [month, setMonth] = useState(parsed.month);
  const [year, setYear] = useState(parsed.year);

  // Sync when value prop changes
  useEffect(() => {
    setDay(parsed.day);
    setMonth(parsed.month);
    setYear(parsed.year);
  }, [parsed]);

  // Generate items
  const days = useMemo(() => {
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    return Array.from({ length: daysInMonth }, (_, i) => ({
      value: i + 1,
      label: String(i + 1),
    }));
  }, [year, month]);

  const months = useMemo(
    () =>
      MONTH_KEYS.map((key, i) => ({
        value: i,
        label: t(key),
      })),
    [t],
  );

  const years = useMemo(
    () =>
      Array.from({ length: MAX_YEAR - MIN_YEAR + 1 }, (_, i) => {
        const y = MAX_YEAR - i;
        return { value: y, label: String(y) };
      }),
    [],
  );

  // Clamp day if month/year changes reduce max days
  useEffect(() => {
    const maxDay = new Date(year, month + 1, 0).getDate();
    if (day > maxDay) setDay(maxDay);
  }, [month, year, day]);

  const handleConfirm = useCallback(() => {
    const m = String(month + 1).padStart(2, "0");
    const d = String(day).padStart(2, "0");
    onChange(`${year}-${m}-${d}`);
    setOpen(false);
  }, [day, month, year, onChange]);

  // Display value
  const displayText = useMemo(() => {
    if (!value) return "";
    return `${day} ${t(MONTH_KEYS[month] ?? "months.january")} ${year}`;
  }, [value, day, month, year, t]);

  return (
    <>
      {label && (
        <label className="text-caption font-semibold text-text-body">
          {label}
        </label>
      )}

      {/* Trigger */}
      <motion.button
        whileTap={{ scale: 0.98 }}
        onClick={() => setOpen(true)}
        className="flex h-touch-md w-full items-center gap-3 rounded-input border border-border bg-white px-4 text-left transition-all duration-150 hover:border-primary/40"
      >
        <Calendar className="h-5 w-5 text-text-muted" />
        <span
          className={cn(
            "text-body",
            displayText ? "text-text-primary font-medium" : "text-text-muted",
          )}
        >
          {displayText || t("booking.dateOfBirth")}
        </span>
      </motion.button>

      {/* Bottom sheet modal */}
      <Modal open={open} onClose={() => setOpen(false)} mode="bottom">
        <div className="flex flex-col gap-6">
          {/* Title */}
          <h3 className="text-center text-h3 font-semibold text-text-primary">
            {t("booking.dateOfBirth")}
          </h3>

          {/* 3-column picker */}
          <div className="flex gap-2">
            <ScrollColumn items={days} selected={day} onSelect={setDay} />
            <ScrollColumn
              items={months}
              selected={month}
              onSelect={setMonth}
            />
            <ScrollColumn items={years} selected={year} onSelect={setYear} />
          </div>

          {/* Confirm button */}
          <Button
            variant="primary"
            size="lg"
            className="w-full"
            onClick={handleConfirm}
          >
            {t("common.confirm")}
          </Button>
        </div>
      </Modal>
    </>
  );
}
