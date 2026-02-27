import { useRef, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useSessionStore } from "../store/sessionStore";
import { IdleScreen } from "../screens/IdleScreen";
import { GreetingScreen } from "../screens/GreetingScreen";
import { DepartmentSelectScreen } from "../screens/DepartmentSelectScreen";
import { DoctorSelectScreen } from "../screens/DoctorSelectScreen";
import { TimeSlotScreen } from "../screens/TimeSlotScreen";
import { BookingConfirmScreen } from "../screens/BookingConfirmScreen";
import { CheckInScreen } from "../screens/CheckInScreen";
import { QueueTicketScreen } from "../screens/QueueTicketScreen";
import { CashierPaymentScreen } from "../screens/CashierPaymentScreen";
import { InfoScreen } from "../screens/InfoScreen";
import { FarewellScreen } from "../screens/FarewellScreen";
import { HandOffScreen } from "../screens/HandOffScreen";
import { useScreenHandlers } from "./useScreenHandlers";
import type { VisitorState } from "../types";

// ── Screen key mapping ──────────────────────────────────────

type ScreenKey =
  | "idle"
  | "greeting"
  | "intent"
  | "department"
  | "doctor"
  | "timeslot"
  | "confirm"
  | "checkin"
  | "queue"
  | "cashier-payment"
  | "info"
  | "farewell"
  | "handoff";

const SCREEN_ORDER: ScreenKey[] = [
  "idle",
  "greeting",
  "intent",
  "department",
  "doctor",
  "timeslot",
  "confirm",
  "cashier-payment",
  "queue",
  "checkin",
  "info",
  "farewell",
  "handoff",
];

function getScreenKey(state: VisitorState): ScreenKey {
  switch (state) {
    case "IDLE":
      return "idle";
    case "DETECTED":
    case "GREETING":
      return "greeting";
    case "INTENT_DISCOVERY":
      return "greeting";  // merged into GreetingScreen with embedded intents
    case "SELECT_DEPARTMENT":
    case "APPOINTMENT_BOOKING":
      return "department";
    case "SELECT_DOCTOR":
      return "doctor";
    case "SELECT_TIMESLOT":
      return "timeslot";
    case "CONFIRM_BOOKING":
      return "confirm";
    case "BOOKING_PAYMENT":
    case "PAYMENT":
    case "SELECT_PAYMENT_METHOD":
    case "PROCESS_PAYMENT":
    case "PAYMENT_RECEIPT":
      return "cashier-payment";
    case "BOOKING_COMPLETE":
    case "ISSUE_QUEUE_TICKET":
    case "ROUTE_TO_DEPARTMENT":
      return "queue";
    case "CHECK_IN":
    case "VERIFY_IDENTITY":
    case "CONFIRM_APPOINTMENT":
      return "checkin";
    case "INFORMATION_INQUIRY":
    case "FAQ_RESPONSE":
    case "DEPARTMENT_INFO":
    case "DOCTOR_PROFILE":
    case "SHOW_DEPARTMENT_INFO":
    case "SHOW_DOCTOR_PROFILE":
      return "info";
    case "RECORD_FEEDBACK":
    case "COMPLAINT":
    case "HAND_OFF":
      return "handoff";
    case "FAREWELL":
      return "farewell";
    default:
      return "idle";
  }
}

// ── Directional animation variants ──────────────────────────

function getDirection(prev: ScreenKey, next: ScreenKey): "forward" | "back" | "fade" {
  if (prev === "idle" || next === "idle") return "fade";
  if (prev === "farewell" || next === "farewell") return "fade";

  const prevIdx = SCREEN_ORDER.indexOf(prev);
  const nextIdx = SCREEN_ORDER.indexOf(next);

  if (next === "intent" && prevIdx > SCREEN_ORDER.indexOf("intent")) return "back";

  return nextIdx >= prevIdx ? "forward" : "back";
}

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
  }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({
    x: direction > 0 ? -300 : 300,
    opacity: 0,
  }),
};

const fadeVariants = {
  enter: { opacity: 0, scale: 1.03 },
  center: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.97 },
};

const springTransition = {
  type: "spring" as const,
  stiffness: 300,
  damping: 30,
};

const fadeTransition = {
  duration: 0.35,
  ease: [0.25, 0.46, 0.45, 0.94] as [number, number, number, number],
};

// ── Main Router ─────────────────────────────────────────────

export function ScreenRouter() {
  const visitorState = useSessionStore((s) => s.state);
  const screenKey = getScreenKey(visitorState);
  const prevScreenRef = useRef<ScreenKey>(screenKey);
  const directionRef = useRef<"forward" | "back" | "fade">("fade");

  const handlers = useScreenHandlers();

  useEffect(() => {
    if (prevScreenRef.current !== screenKey) {
      directionRef.current = getDirection(prevScreenRef.current, screenKey);
      prevScreenRef.current = screenKey;
      // Notify inactivity timer that screen changed (user is actively navigating)
      window.dispatchEvent(new Event("screen-navigated"));
    }
  }, [screenKey]);

  const isFade = directionRef.current === "fade";
  const directionNum = directionRef.current === "back" ? -1 : 1;

  return (
    <AnimatePresence mode="wait" custom={directionNum}>
      <motion.div
        key={screenKey}
        custom={directionNum}
        variants={isFade ? fadeVariants : slideVariants}
        initial="enter"
        animate="center"
        exit="exit"
        transition={isFade ? fadeTransition : springTransition}
        className="h-screen w-screen"
      >
        {screenKey === "idle" && (
          <IdleScreen
            onFaceDetected={handlers.handleFaceDetected}
            onTouchStart={handlers.handleTouchStart}
          />
        )}
        {screenKey === "greeting" && (
          <GreetingScreen
            onContinue={handlers.handleContinueToIntent}
            onCheckIn={handlers.handleCheckIn}
            onSelectIntent={handlers.handleSelectIntent}
          />
        )}
        {screenKey === "department" && (
          <DepartmentSelectScreen
            onSelectDepartment={handlers.handleSelectDepartment}
            onBack={handlers.handleBackToIntent}
          />
        )}
        {screenKey === "doctor" && (
          <DoctorSelectScreen
            onSelectDoctor={handlers.handleSelectDoctor}
            onBack={handlers.handleBackToDepartments}
          />
        )}
        {screenKey === "timeslot" && (
          <TimeSlotScreen
            onSelectSlot={handlers.handleSelectSlot}
            onBack={handlers.handleBackToDoctors}
          />
        )}
        {screenKey === "confirm" && (
          <BookingConfirmScreen
            onConfirm={handlers.handleConfirmBooking}
            onCancel={handlers.handleCancelBooking}
            onBack={handlers.handleBackToSlots}
          />
        )}
        {screenKey === "checkin" && (
          <CheckInScreen
            onCheckInComplete={handlers.handleCheckInComplete}
            onBookAppointment={handlers.handleBookFromCheckIn}
            onBack={handlers.handleBackFromCheckIn}
          />
        )}
        {screenKey === "queue" && (
          <QueueTicketScreen onDone={handlers.handleQueueDone} />
        )}
        {screenKey === "cashier-payment" && (
          <CashierPaymentScreen
            onDone={handlers.handlePaymentSuccess}
            onBack={handlers.handlePaymentBack}
          />
        )}
        {screenKey === "info" && (
          <InfoScreen onBack={handlers.handleInfoBack} />
        )}
        {screenKey === "farewell" && (
          <FarewellScreen onDone={handlers.handleFarewellDone} />
        )}
        {screenKey === "handoff" && (
          <HandOffScreen onCancel={handlers.handleHandOffCancel} />
        )}
      </motion.div>
    </AnimatePresence>
  );
}
