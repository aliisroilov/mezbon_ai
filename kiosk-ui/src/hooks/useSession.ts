import { useEffect } from "react";
import { useSessionStore } from "../store/sessionStore";
import {
  connectSocket,
  disconnectSocket,
  onAIResponse,
  onAIProcessing,
  onAIStateChange,
  onAIError,
  onSessionTimeout,
  onConnectionStatus,
  emitTouchAction,
} from "../services/socket";
import type { OrchestratorResponse } from "../types";

/** Delay (ms) before mic auto-restarts after text response (time to read) */
const MIC_RESTART_DELAY = 3000;

export function useSession() {
  const store = useSessionStore;

  useEffect(() => {
    const { deviceId, clinicId } = store.getState();
    // connectSocket is now async — fetches device JWT then connects
    connectSocket(deviceId, clinicId);

    const unsubs = [
      onConnectionStatus((status) => {
        const s = store.getState();
        s.setIsConnected(status === "connected");
        // On reconnect with an active session, verify it's still valid
        if (status === "connected" && s.sessionId && s.state !== "IDLE") {
          emitTouchAction(s.deviceId, s.sessionId, "ping", {});
        }
      }),
      onAIProcessing((data) => {
        // Instant acknowledgment from backend — ensure processing indicator shows
        console.log("[session] ai:processing — backend acknowledged audio");
        const s = store.getState();
        if (data.session_id) s.setSessionId(data.session_id);
        s.setIsProcessing(true);
      }),
      onAIResponse((data: OrchestratorResponse) => {
        console.log("=== 🎤 VOICE DEBUG: ai:response received ===");
        console.log("  text:", JSON.stringify(data.text));
        console.log("  text length:", data.text?.length ?? 0);
        console.log("  transcript:", JSON.stringify(data.transcript));
        console.log("  state:", data.state);
        console.log("  ui_action:", data.ui_action);
        console.log("  session_id:", data.session_id);
        console.log("  has ui_data:", !!data.ui_data);
        console.log("  all keys:", Object.keys(data));
        console.log("=== END VOICE DEBUG ===");

        const s = store.getState();
        s.setSessionId(data.session_id);
        s.setState(data.state);
        s.setIsProcessing(false);

        // Empty text = backend says "stay silent" (e.g. 3+ empty transcripts)
        // Wait longer before re-enabling mic to prevent rapid-fire loop
        if (!data.text || data.text.trim().length === 0) {
          console.log("[session] Empty response — 5s cooldown before mic restart");
          s.setIsSpeaking(false);
          setTimeout(() => {
            store.getState().setShouldListen(true);
          }, 5000); // 5s cooldown to break silence → empty transcript loop
          return;
        }

        s.setAIMessage(data.text);

        // Show visitor's transcribed speech
        if (data.transcript) {
          s.setUserTranscript(data.transcript);
        }

        // Set patient if backend recognized one
        if (data.patient) {
          s.setPatient({
            id: data.patient.id,
            clinic_id: "",
            full_name: data.patient.name,
            phone: "",
            date_of_birth: null,
            language_preference: s.language,
            has_face_embedding: false,
            created_at: "",
            updated_at: "",
          });
        }

        // TTS disabled — no audio playback.
        // Show text immediately and restart mic after short reading delay.
        s.setIsSpeaking(false);
        window.dispatchEvent(new Event("ai-response-received"));
        setTimeout(() => {
          store.getState().setShouldListen(true);
        }, MIC_RESTART_DELAY);

        // Handle UI action — backend sends plain string like "show_departments"
        if (data.ui_action) {
          handleUIAction(data.ui_action, data.ui_data || {}, s);
        }
      }),
      onAIStateChange((data) => {
        store.getState().setState(data.state);
      }),
      onAIError((data) => {
        const s = store.getState();
        s.setIsProcessing(false);
        s.setIsListening(false);
        s.setIsSpeaking(false);
        // Show error to user so they know what happened
        s.setAIMessage(
          data.message || "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
        );
        if (import.meta.env.DEV) console.error("[useSession] ai:error received:", data);
        // Re-enable mic after error so user can try again
        setTimeout(() => {
          store.getState().setShouldListen(true);
        }, MIC_RESTART_DELAY);
      }),
      onSessionTimeout((data) => {
        if (!data.warning) {
          // Only reset if we're not in the middle of processing or speaking
          const s = store.getState();
          if (!s.isProcessing && !s.isSpeaking && !s.isListening) {
            s.resetSession();
          }
        }
      }),
    ];

    return () => {
      unsubs.forEach((fn) => fn());
      disconnectSocket();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

function handleUIAction(
  action: string,
  uiData: Record<string, unknown>,
  s: ReturnType<typeof useSessionStore.getState>,
) {
  // The backend ui_data now contains structured fields (departments, doctors,
  // slots, ticket, appointment) alongside the raw function_results.
  const fnResults = uiData.function_results as
    | Array<{ name: string; args: Record<string, unknown>; result?: Record<string, unknown> }>
    | undefined;

  // CRITICAL: Force state navigation so ScreenRouter renders the correct screen.
  // The backend state may already be correct, but we enforce it here as a safety net.
  switch (action) {
    case "show_departments":
      if (Array.isArray(uiData.departments)) {
        s.setDepartments(uiData.departments as import("../types").Department[]);
      }
      s.setState("SELECT_DEPARTMENT");
      break;
    case "show_doctors":
      if (Array.isArray(uiData.doctors)) {
        s.setDoctors(normalizeDoctors(uiData.doctors));
      }
      s.setState("SELECT_DOCTOR");
      break;
    case "show_time_slots":
    case "show_slots":
      if (Array.isArray(uiData.slots)) {
        s.setAvailableSlots(uiData.slots as import("../types").TimeSlot[]);
      }
      s.setState("SELECT_TIMESLOT");
      break;
    case "show_queue_ticket":
      if (uiData.ticket) {
        // Normalize ticket data — backend may send partial ticket from booking result
        const rawTicket = uiData.ticket as Record<string, unknown>;
        s.setQueueTicket({
          id: String(rawTicket.id ?? ""),
          clinic_id: String(rawTicket.clinic_id ?? ""),
          patient_id: String(rawTicket.patient_id ?? ""),
          department_id: String(rawTicket.department_id ?? ""),
          doctor_id: (rawTicket.doctor_id as string) ?? null,
          ticket_number: String(rawTicket.ticket_number ?? rawTicket.confirmation_code ?? ""),
          status: "WAITING",
          estimated_wait_minutes: Number(rawTicket.estimated_wait_minutes ?? 10),
          department_name: String(rawTicket.department_name ?? ""),
          called_at: null,
          completed_at: null,
          created_at: new Date().toISOString(),
        });
      }
      s.setState("BOOKING_COMPLETE");
      break;
    case "show_booking_confirmation":
      if (uiData.appointment) {
        s.setCurrentAppointment(uiData.appointment as import("../types").Appointment);
      }
      s.setState("CONFIRM_BOOKING");
      break;
    case "show_booking_complete":
      // Booking is done — go to queue ticket screen, not confirm form
      if (uiData.ticket) {
        const rawTkt = uiData.ticket as Record<string, unknown>;
        s.setQueueTicket({
          id: String(rawTkt.id ?? ""),
          clinic_id: String(rawTkt.clinic_id ?? ""),
          patient_id: String(rawTkt.patient_id ?? ""),
          department_id: String(rawTkt.department_id ?? ""),
          doctor_id: (rawTkt.doctor_id as string) ?? null,
          ticket_number: String(rawTkt.ticket_number ?? rawTkt.confirmation_code ?? ""),
          status: "WAITING",
          estimated_wait_minutes: Number(rawTkt.estimated_wait_minutes ?? 10),
          department_name: String(rawTkt.department_name ?? ""),
          called_at: null,
          completed_at: null,
          created_at: new Date().toISOString(),
        });
      }
      s.setState("BOOKING_COMPLETE");
      break;
    case "show_checkin":
    case "show_checkin_confirmation":
    case "show_verification":
    case "show_appointment_confirmation":
      s.setState("CHECK_IN");
      break;
    case "show_route":
      // Route to department → show queue ticket
      s.setState("ROUTE_TO_DEPARTMENT");
      break;
    case "show_department_info":
    case "show_doctor_profile":
      s.setState("INFORMATION_INQUIRY");
      break;
    case "show_payment":
    case "show_payment_methods":
    case "show_payment_processing":
      s.setState("PAYMENT");
      break;
    case "show_receipt":
      // Payment receipt → go to queue ticket if ticket available, else farewell
      if (uiData.ticket) {
        const rawTkt = uiData.ticket as Record<string, unknown>;
        s.setQueueTicket({
          id: String(rawTkt.id ?? ""),
          clinic_id: String(rawTkt.clinic_id ?? ""),
          patient_id: String(rawTkt.patient_id ?? ""),
          department_id: String(rawTkt.department_id ?? ""),
          doctor_id: (rawTkt.doctor_id as string) ?? null,
          ticket_number: String(rawTkt.ticket_number ?? ""),
          status: "WAITING",
          estimated_wait_minutes: Number(rawTkt.estimated_wait_minutes ?? 10),
          department_name: String(rawTkt.department_name ?? ""),
          called_at: null,
          completed_at: null,
          created_at: new Date().toISOString(),
        });
        s.setState("BOOKING_COMPLETE");
      } else {
        s.setState("FAREWELL");
      }
      break;
    case "show_farewell":
      s.setState("FAREWELL");
      break;
    case "show_info":
    case "show_faq":
      s.setState("INFORMATION_INQUIRY");
      break;
    case "show_greeting":
      s.setState("GREETING");
      break;
    case "show_intent_options":
      s.setState("INTENT_DISCOVERY");
      break;
    case "show_handoff":
      s.setState("HAND_OFF");
      break;
    case "show_queue_status":
      break;
    case "reset":
      s.resetSession();
      break;
  }

  // Also check function call results for extractable data (fallback
  // in case the orchestrator's structured ui_data is missing a field).
  if (fnResults) {
    for (const fc of fnResults) {
      const result = fc.result || {};

      if (fc.name === "get_department_info" && !uiData.departments) {
        if (Array.isArray(result.departments)) {
          s.setDepartments(result.departments as import("../types").Department[]);
        } else if (result.department_id || result.name) {
          s.setDepartments([result] as unknown as import("../types").Department[]);
        }
      }

      if (fc.name === "get_doctor_info" && !uiData.doctors) {
        if (result.doctor_id || result.full_name || result.name) {
          s.setDoctors(normalizeDoctors([result]));
        }
      }

      if (fc.name === "get_department_info" && !uiData.doctors) {
        // get_department_info may embed doctors for the matched department
        if (Array.isArray(result.doctors) && result.doctors.length > 0) {
          s.setDoctors(normalizeDoctors(result.doctors));
        }
      }

      if (fc.name === "get_available_slots" && !uiData.slots) {
        const rawSlots = result.available_slots;
        if (Array.isArray(rawSlots)) {
          const slots = rawSlots.map((sl: string | { start: string; end: string }) =>
            typeof sl === "string"
              ? { start_time: sl, end_time: sl, is_available: true }
              : { start_time: sl.start, end_time: sl.end, is_available: true },
          );
          s.setAvailableSlots(slots);
        }
      }

      // book_appointment result — set ticket from confirmation code
      if (fc.name === "book_appointment" && result.confirmation_code) {
        s.setQueueTicket({
          id: "",
          clinic_id: "",
          patient_id: "",
          department_id: "",
          doctor_id: null,
          ticket_number: String(result.confirmation_code),
          status: "WAITING",
          estimated_wait_minutes: Number(result.estimated_wait_minutes || 10),
          department_name: "",
          called_at: null,
          completed_at: null,
          created_at: new Date().toISOString(),
        });
      }

      if (fc.name === "issue_queue_ticket" && !uiData.ticket && result.ticket_number) {
        s.setQueueTicket({
          id: "",
          clinic_id: "",
          patient_id: "",
          department_id: "",
          doctor_id: null,
          ticket_number: String(result.ticket_number),
          status: "WAITING",
          estimated_wait_minutes: Number(result.estimated_wait_minutes || 0),
          department_name: "",
          called_at: null,
          completed_at: null,
          created_at: new Date().toISOString(),
        });
      }
    }
  }
}

/**
 * Normalize doctor data from AI/backend into the frontend Doctor type.
 * The AI may return `name` instead of `full_name`, and omit many fields.
 */
function normalizeDoctors(
  raw: Record<string, unknown>[],
): import("../types").Doctor[] {
  return raw.map((d) => ({
    id: String(d.id ?? d.doctor_id ?? ""),
    clinic_id: String(d.clinic_id ?? ""),
    department_id: String(d.department_id ?? ""),
    full_name: String(d.full_name ?? d.name ?? ""),
    specialty: String(d.specialty ?? ""),
    bio: (d.bio as string) ?? null,
    photo_url: (d.photo_url as string) ?? null,
    is_active: d.is_active !== false,
    department_name: String(d.department_name ?? d.department ?? ""),
    schedules: (d.schedules as import("../types").DoctorSchedule[]) ?? [],
    next_available_slot: (d.next_available_slot as string) ?? null,
    created_at: String(d.created_at ?? ""),
    updated_at: String(d.updated_at ?? ""),
  }));
}
