import { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import {
  ChevronDown,
  ChevronUp,
  Search,
  Clock,
} from "lucide-react";
import { AIPromptBar } from "../components/ai/AIPromptBar";
import { getMedicalIcon } from "../components/icons/MedicalIcons";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";
import { useSessionStore } from "../store/sessionStore";
import { useVoiceChat } from "../hooks/useVoiceChat";
import { MOCK_FAQS } from "../utils/mockData";
import { cn } from "../lib/cn";

// ── Tab types ───────────────────────────────────────────────

type TabId = "faq" | "departments" | "doctors" | "hours";

interface TabConfig {
  id: TabId;
  labelKey: string;
}

const TABS: TabConfig[] = [
  { id: "faq", labelKey: "intent.faq" },
  { id: "departments", labelKey: "info.departments" },
  { id: "doctors", labelKey: "info.doctors" },
  { id: "hours", labelKey: "info.workingHours" },
];

// ── FAQ Accordion ───────────────────────────────────────────

interface FAQItemProps {
  question: string;
  answer: string;
  isOpen: boolean;
  onToggle: () => void;
  index: number;
}

function FAQItem({ question, answer, isOpen, onToggle, index }: FAQItemProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      className="overflow-hidden rounded-card bg-white shadow-card"
    >
      <motion.button
        whileTap={{ scale: 0.99 }}
        onClick={onToggle}
        className="flex w-full items-center justify-between p-5 text-left"
      >
        <span className="pr-4 text-h3 tracking-heading text-text-primary">
          {question}
        </span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="shrink-0"
        >
          {isOpen ? (
            <ChevronUp className="h-5 w-5 text-primary" />
          ) : (
            <ChevronDown className="h-5 w-5 text-text-muted" />
          )}
        </motion.div>
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
          >
            <div className="border-t border-border/50 px-5 pb-5 pt-4">
              <p className="text-body leading-relaxed text-text-body">
                {answer}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Department info card ────────────────────────────────────

function DepartmentInfoCard({
  department,
  index,
}: {
  department: { name: string; floor: number | null; room_number: string | null; doctor_count: number };
  index: number;
}) {
  const { t } = useTranslation();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      className="flex items-center gap-4 rounded-card bg-white p-5 shadow-card"
    >
      {(() => {
        const Icon = getMedicalIcon(department.name);
        return (
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary">
            <Icon className="h-6 w-6" />
          </div>
        );
      })()}
      <div className="min-w-0 flex-1">
        <p className="text-h3 tracking-heading text-text-primary">
          {department.name}
        </p>
        <p className="text-caption text-text-muted">
          {department.floor !== null && t("department.floor", { floor: department.floor })}
          {department.room_number && ` • ${t("department.room", { room: department.room_number })}`}
          {` • ${t("department.doctors", { count: department.doctor_count })}`}
        </p>
      </div>
    </motion.div>
  );
}

// ── Doctor info card ────────────────────────────────────────

function DoctorInfoCard({
  doctor,
  index,
}: {
  doctor: { full_name: string; specialty: string; photo_url: string | null; department_name: string };
  index: number;
}) {
  const initials = doctor.full_name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      className="flex items-center gap-4 rounded-card bg-white p-5 shadow-card"
    >
      {doctor.photo_url ? (
        <img
          src={doctor.photo_url}
          alt={doctor.full_name}
          className="h-14 w-14 shrink-0 rounded-full object-cover"
        />
      ) : (
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-dark">
          <span className="text-body font-bold text-white">{initials}</span>
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-h3 tracking-heading text-text-primary">
          {doctor.full_name}
        </p>
        <p className="text-caption text-text-muted">
          {doctor.specialty} • {doctor.department_name}
        </p>
      </div>
    </motion.div>
  );
}

// ── Working hours table ─────────────────────────────────────

function WorkingHoursTable() {
  const { t } = useTranslation();

  const dayKeys = [
    "days.monday",
    "days.tuesday",
    "days.wednesday",
    "days.thursday",
    "days.friday",
    "days.saturday",
    "days.sunday",
  ];

  const hours = [
    { hours: "08:00 — 18:00", break: "12:00 — 13:00" },
    { hours: "08:00 — 18:00", break: "12:00 — 13:00" },
    { hours: "08:00 — 18:00", break: "12:00 — 13:00" },
    { hours: "08:00 — 18:00", break: "12:00 — 13:00" },
    { hours: "08:00 — 18:00", break: "12:00 — 13:00" },
    { hours: "08:00 — 14:00", break: "—" },
    { hours: null, break: null },
  ];

  const today = new Date().getDay();
  // JS getDay: 0=Sun, adjust so Mon=0
  const todayIndex = today === 0 ? 6 : today - 1;

  return (
    <div className="overflow-hidden rounded-card bg-white shadow-card">
      {dayKeys.map((dayKey, i) => {
        const isToday = i === todayIndex;
        const isSunday = i === 6;
        const hourData = hours[i];

        return (
          <motion.div
            key={dayKey}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.05 }}
            className={cn(
              "flex items-center justify-between px-5 py-4",
              i < dayKeys.length - 1 && "border-b border-border/50",
              isToday && "bg-primary-50",
            )}
          >
            <div className="flex items-center gap-3">
              {isToday && (
                <div className="h-2 w-2 rounded-full bg-primary" />
              )}
              <span
                className={cn(
                  "text-body font-medium",
                  isToday ? "text-primary" : "text-text-primary",
                )}
              >
                {t(dayKey)}
              </span>
            </div>
            <div className="flex items-center gap-6">
              <span
                className={cn(
                  "text-body",
                  isSunday ? "text-text-muted" : "text-text-body",
                )}
              >
                {hourData?.hours ?? t("info.dayOff")}
              </span>
              {hourData?.break && hourData.break !== "—" && (
                <span className="flex items-center gap-1 text-caption text-text-muted">
                  <Clock className="h-3.5 w-3.5" />
                  {hourData.break}
                </span>
              )}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

// ── Main screen ─────────────────────────────────────────────

interface InfoScreenProps {
  onBack: () => void;
}

export function InfoScreen({ onBack }: InfoScreenProps) {
  const { t } = useTranslation();
  const departments = useSessionStore((s) => s.departments);
  const doctors = useSessionStore((s) => s.doctors);
  const aiMessage = useSessionStore((s) => s.aiMessage);

  const voice = useVoiceChat({ autoStartDelay: 1000 });

  const [activeTab, setActiveTab] = useState<TabId>("faq");
  const [searchQuery, setSearchQuery] = useState("");
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(null);

  // FAQ data from mock
  const faqItems = useMemo(
    () =>
      MOCK_FAQS.map((faq) => ({
        question: faq.question,
        answer: faq.answer,
      })),
    [],
  );

  const filteredFaqs = useMemo(() => {
    if (!searchQuery) return faqItems;
    const q = searchQuery.toLowerCase();
    return faqItems.filter(
      (faq) =>
        faq.question.toLowerCase().includes(q) ||
        faq.answer.toLowerCase().includes(q),
    );
  }, [faqItems, searchQuery]);

  const handleTabChange = useCallback((tab: TabId) => {
    setActiveTab(tab);
    setSearchQuery("");
    setOpenFaqIndex(null);
  }, []);

  const responseText =
    aiMessage || t("info.title");

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* ── Header ── */}
      <HeaderBar title={t("info.title")} />

      {/* ── AI prompt ── */}
      <div className="px-8 pb-4">
        <AIPromptBar
          message={responseText}
          avatarState={voice.avatarState}
          voiceState={voice.voiceState}
          onVoiceClick={voice.toggleMic}
        />
      </div>

      {/* ── Tab bar ── */}
      <div className="relative px-8 pb-4">
        <div className="flex gap-1 overflow-x-auto scrollbar-hide">
          {TABS.map((tab) => (
            <motion.button
              key={tab.id}
              whileTap={{ scale: 0.97 }}
              onClick={() => handleTabChange(tab.id)}
              className={cn(
                "relative shrink-0 px-5 py-3 text-body font-medium transition-colors duration-200",
                activeTab === tab.id
                  ? "text-primary"
                  : "text-text-muted hover:text-text-body",
              )}
            >
              {t(tab.labelKey)}
              {activeTab === tab.id && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-primary"
                  transition={{
                    type: "spring" as const,
                    stiffness: 500,
                    damping: 30,
                  }}
                />
              )}
            </motion.button>
          ))}
        </div>
        <div className="h-px bg-border/50" />
      </div>

      {/* ── Tab content ── */}
      <div className="flex-1 overflow-y-auto px-8 pb-6 scrollbar-hide">
        <AnimatePresence mode="wait">
          {/* FAQ Tab */}
          {activeTab === "faq" && (
            <motion.div
              key="faq"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
              className="flex flex-col gap-4"
            >
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={`${t("common.search")}...`}
                  className="h-touch-md w-full rounded-input border border-border bg-white pl-12 pr-4 text-body text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none focus:ring-[3px] focus:ring-primary/20"
                />
              </div>

              {filteredFaqs.map((faq, i) => (
                <FAQItem
                  key={i}
                  question={faq.question}
                  answer={faq.answer}
                  isOpen={openFaqIndex === i}
                  onToggle={() =>
                    setOpenFaqIndex(openFaqIndex === i ? null : i)
                  }
                  index={i}
                />
              ))}

              {filteredFaqs.length === 0 && (
                <p className="py-8 text-center text-body text-text-muted">
                  {t("common.noResults")}
                </p>
              )}
            </motion.div>
          )}

          {/* Departments Tab */}
          {activeTab === "departments" && (
            <motion.div
              key="departments"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
              className="flex flex-col gap-3"
            >
              {departments.map((dept, i) => (
                <DepartmentInfoCard key={dept.id} department={dept} index={i} />
              ))}
              {departments.length === 0 && (
                <p className="py-8 text-center text-body text-text-muted">
                  {t("common.noResults")}
                </p>
              )}
            </motion.div>
          )}

          {/* Doctors Tab */}
          {activeTab === "doctors" && (
            <motion.div
              key="doctors"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
              className="flex flex-col gap-3"
            >
              {doctors.map((doc, i) => (
                <DoctorInfoCard key={doc.id} doctor={doc} index={i} />
              ))}
              {doctors.length === 0 && (
                <p className="py-8 text-center text-body text-text-muted">
                  {t("common.noResults")}
                </p>
              )}
            </motion.div>
          )}

          {/* Working Hours Tab */}
          {activeTab === "hours" && (
            <motion.div
              key="hours"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
            >
              <WorkingHoursTable />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Bottom nav ── */}
      <BottomNav onBack={onBack} />
    </motion.div>
  );
}
