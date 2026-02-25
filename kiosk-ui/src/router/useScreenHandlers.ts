import { useCallback, useRef } from "react";
import { useSessionStore } from "../store/sessionStore";
import { emitTouchAction } from "../services/socket";
import {
  MOCK_DEPARTMENTS,
  MOCK_DOCTORS,
  MOCK_QUEUE_TICKET,
  generateTimeSlots,
  getDoctorsByDepartment,
  getServicesByDepartment,
} from "../utils/mockData";
import type { Department, Doctor, TimeSlot } from "../types";

/**
 * Central hook for all screen navigation + data loading handlers.
 * Connects screens to the Zustand store and Socket.IO.
 *
 * When the backend is connected, socket events will drive state changes
 * via useSession. These handlers provide the fallback / touch-action path.
 */
export function useScreenHandlers() {
  const setState = useSessionStore((s) => s.setState);
  const resetSession = useSessionStore((s) => s.resetSession);
  const setDepartments = useSessionStore((s) => s.setDepartments);
  const setDoctors = useSessionStore((s) => s.setDoctors);
  const setServices = useSessionStore((s) => s.setServices);
  const setAvailableSlots = useSessionStore((s) => s.setAvailableSlots);
  const setCurrentDepartment = useSessionStore((s) => s.setCurrentDepartment);
  const setCurrentDoctor = useSessionStore((s) => s.setCurrentDoctor);
  const setCurrentService = useSessionStore((s) => s.setCurrentService);
  const setSelectedSlot = useSessionStore((s) => s.setSelectedSlot);
  const setSelectedDate = useSessionStore((s) => s.setSelectedDate);
  const setQueueTicket = useSessionStore((s) => s.setQueueTicket);

  const deviceId = useSessionStore((s) => s.deviceId);
  const sessionId = useSessionStore((s) => s.sessionId);

  // Helper to emit socket + provide fallback + reset inactivity timer
  const emit = useCallback(
    (action: string, data: Record<string, unknown> = {}) => {
      if (sessionId) {
        emitTouchAction(deviceId, sessionId, action, data);
      }
      // Reset inactivity timer on every touch action
      window.dispatchEvent(new Event("user-interaction"));
    },
    [deviceId, sessionId],
  );

  // ── Idle → Greeting ──

  const handleFaceDetected = useCallback(() => {
    setState("GREETING");
  }, [setState]);

  const handleTouchStart = useCallback(() => {
    setState("GREETING");
  }, [setState]);

  // ── Greeting → Intent ──

  const handleContinueToIntent = useCallback(() => {
    setState("INTENT_DISCOVERY");
  }, [setState]);

  const handleBackToGreeting = useCallback(() => {
    setState("GREETING");
  }, [setState]);

  const handleCheckIn = useCallback(() => {
    setState("CHECK_IN");
  }, [setState]);

  // ── Intent → specific flows ──

  const handleSelectIntent = useCallback(
    (intentId: string) => {
      emit("select_intent", { intent: intentId });

      switch (intentId) {
        case "book":
          // Load departments (mock fallback)
          setDepartments(MOCK_DEPARTMENTS);
          setState("SELECT_DEPARTMENT");
          break;
        case "checkin":
          setState("CHECK_IN");
          break;
        case "info":
          // Load info data (mock fallback)
          setDepartments(MOCK_DEPARTMENTS);
          setDoctors(MOCK_DOCTORS);
          setState("INFORMATION_INQUIRY");
          break;
        case "payment":
          setState("PAYMENT");
          break;
        case "other":
          setState("HAND_OFF");
          break;
      }
    },
    [setState, emit, setDepartments, setDoctors],
  );

  // ── Department selection ──

  const handleSelectDepartment = useCallback(
    (dept: Department) => {
      setCurrentDepartment(dept);
      emit("select_department", { department_id: dept.id });

      // Load doctors for department (mock fallback)
      const doctors = getDoctorsByDepartment(dept.id);
      setDoctors(doctors);

      // Load services for department (mock fallback)
      const services = getServicesByDepartment(dept.id);
      setServices(services);

      // Auto-select first service if available
      const firstService = services[0];
      if (firstService) {
        setCurrentService(firstService);
      }

      setState("SELECT_DOCTOR");
    },
    [setState, setCurrentDepartment, setDoctors, setServices, setCurrentService, emit],
  );

  const handleBackToIntent = useCallback(() => {
    setState("GREETING");
    setCurrentDepartment(null);
    setDoctors([]);
    setServices([]);
  }, [setState, setCurrentDepartment, setDoctors, setServices]);

  // ── Doctor selection ──

  const handleSelectDoctor = useCallback(
    (doc: Doctor) => {
      setCurrentDoctor(doc);
      emit("select_doctor", { doctor_id: doc.id });

      // Generate time slots (mock fallback)
      const today = new Date();
      const dateKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
      const slots = generateTimeSlots(dateKey);
      setAvailableSlots(slots);

      setState("SELECT_TIMESLOT");
    },
    [setState, setCurrentDoctor, setAvailableSlots, emit],
  );

  const handleBackToDepartments = useCallback(() => {
    setState("SELECT_DEPARTMENT");
    setCurrentDoctor(null);
    setCurrentService(null);
    setDoctors([]);
    setServices([]);
    setAvailableSlots([]);
  }, [setState, setCurrentDoctor, setCurrentService, setDoctors, setServices, setAvailableSlots]);

  // ── Time slot selection ──

  const handleSelectSlot = useCallback(
    (slot: TimeSlot, date: string) => {
      setSelectedSlot(slot);
      setSelectedDate(date);
      emit("select_slot", {
        start_time: slot.start_time,
        end_time: slot.end_time,
        date,
      });
      setState("CONFIRM_BOOKING");
    },
    [setState, setSelectedSlot, setSelectedDate, emit],
  );

  const handleBackToDoctors = useCallback(() => {
    setState("SELECT_DOCTOR");
    setSelectedSlot(null);
    setSelectedDate(null);
    setAvailableSlots([]);
  }, [setState, setSelectedSlot, setSelectedDate, setAvailableSlots]);

  // ── Booking confirmation ──

  const bookingFallbackRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleConfirmBooking = useCallback(() => {
    emit("confirm_booking", {});
    // Only use mock fallback if no active backend session —
    // when sessionId exists, let the backend ai:response drive state
    if (!sessionId) {
      setQueueTicket(MOCK_QUEUE_TICKET);
      setState("BOOKING_COMPLETE");
    } else {
      // Clear any existing fallback timer
      if (bookingFallbackRef.current) clearTimeout(bookingFallbackRef.current);
      // Set mock ticket as fallback in case backend doesn't respond
      // but don't change state — let backend response handle it
      bookingFallbackRef.current = setTimeout(() => {
        bookingFallbackRef.current = null;
        const s = useSessionStore.getState();
        if (s.state === "CONFIRM_BOOKING") {
          // Backend didn't respond in 5s — use mock fallback
          setQueueTicket(MOCK_QUEUE_TICKET);
          setState("BOOKING_COMPLETE");
        }
      }, 5000);
    }
  }, [setState, setQueueTicket, emit, sessionId]);

  const handleCancelBooking = useCallback(() => {
    setState("GREETING");
    setCurrentDepartment(null);
    setCurrentDoctor(null);
    setCurrentService(null);
    setSelectedSlot(null);
    setSelectedDate(null);
    setDoctors([]);
    setServices([]);
    setAvailableSlots([]);
  }, [
    setState,
    setCurrentDepartment,
    setCurrentDoctor,
    setCurrentService,
    setSelectedSlot,
    setSelectedDate,
    setDoctors,
    setServices,
    setAvailableSlots,
  ]);

  const handleBackToSlots = useCallback(() => {
    setState("SELECT_TIMESLOT");
  }, [setState]);

  // ── Check-in ──

  const handleCheckInComplete = useCallback(() => {
    emit("check_in_complete", {});
    setQueueTicket(MOCK_QUEUE_TICKET);
    setState("ISSUE_QUEUE_TICKET");
  }, [setState, setQueueTicket, emit]);

  const handleBookFromCheckIn = useCallback(() => {
    setDepartments(MOCK_DEPARTMENTS);
    setState("SELECT_DEPARTMENT");
  }, [setState, setDepartments]);

  const handleBackFromCheckIn = useCallback(() => {
    setState("GREETING");
  }, [setState]);

  // ── Queue ticket ──

  const handleQueueDone = useCallback(() => {
    setState("FAREWELL");
  }, [setState]);

  // ── Payment ──

  const handlePaymentSuccess = useCallback(() => {
    emit("payment_success", {});
    setQueueTicket(MOCK_QUEUE_TICKET);
    setState("ISSUE_QUEUE_TICKET");
  }, [setState, setQueueTicket, emit]);

  const handlePaymentBack = useCallback(() => {
    setState("GREETING");
  }, [setState]);

  // ── Info ──

  const handleInfoBack = useCallback(() => {
    setState("GREETING");
  }, [setState]);

  // ── Farewell ──

  const handleFarewellDone = useCallback(() => {
    resetSession();
  }, [resetSession]);

  // ── Hand off ──

  const handleHandOffCancel = useCallback(() => {
    setState("GREETING");
  }, [setState]);

  return {
    // Idle
    handleFaceDetected,
    handleTouchStart,
    // Greeting
    handleContinueToIntent,
    handleBackToGreeting,
    handleCheckIn,
    // Intent
    handleSelectIntent,
    // Department
    handleSelectDepartment,
    handleBackToIntent,
    // Doctor
    handleSelectDoctor,
    handleBackToDepartments,
    // Slot
    handleSelectSlot,
    handleBackToDoctors,
    // Booking
    handleConfirmBooking,
    handleCancelBooking,
    handleBackToSlots,
    // Check-in
    handleCheckInComplete,
    handleBookFromCheckIn,
    handleBackFromCheckIn,
    // Queue
    handleQueueDone,
    // Payment
    handlePaymentSuccess,
    handlePaymentBack,
    // Info
    handleInfoBack,
    // Farewell
    handleFarewellDone,
    // Hand off
    handleHandOffCancel,
  };
}
