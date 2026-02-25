import { create } from "zustand";
import type {
  VisitorState,
  Language,
  Patient,
  Department,
  Doctor,
  MedicalService,
  TimeSlot,
  QueueTicket,
  Appointment,
} from "../types";

interface SessionState {
  // Session
  sessionId: string | null;
  deviceId: string;
  clinicId: string;
  state: VisitorState;

  // Patient
  patient: Patient | null;
  language: Language;

  // Navigation data
  departments: Department[];
  doctors: Doctor[];
  services: MedicalService[];
  availableSlots: TimeSlot[];
  selectedDate: string | null;

  // Selections
  currentDepartment: Department | null;
  currentDoctor: Doctor | null;
  currentService: MedicalService | null;
  selectedSlot: TimeSlot | null;

  // Booking result
  currentAppointment: Appointment | null;
  queueTicket: QueueTicket | null;

  // AI state
  aiMessage: string;
  aiAudioUrl: string | null;
  /** The visitor's last transcribed speech (from STT) */
  userTranscript: string;
  isListening: boolean;
  isSpeaking: boolean;
  isProcessing: boolean;
  /** When true, the active screen should auto-start the microphone */
  shouldListen: boolean;

  // Connection
  isConnected: boolean;

  // Degradation flags
  voiceAvailable: boolean;
  aiAvailable: boolean;

  // Actions
  setSessionId: (id: string | null) => void;
  setState: (state: VisitorState) => void;
  setPatient: (patient: Patient | null) => void;
  setLanguage: (lang: Language) => void;
  setDepartments: (departments: Department[]) => void;
  setDoctors: (doctors: Doctor[]) => void;
  setServices: (services: MedicalService[]) => void;
  setAvailableSlots: (slots: TimeSlot[]) => void;
  setSelectedDate: (date: string | null) => void;
  setCurrentDepartment: (dept: Department | null) => void;
  setCurrentDoctor: (doc: Doctor | null) => void;
  setCurrentService: (svc: MedicalService | null) => void;
  setSelectedSlot: (slot: TimeSlot | null) => void;
  setCurrentAppointment: (appt: Appointment | null) => void;
  setQueueTicket: (ticket: QueueTicket | null) => void;
  setAIMessage: (message: string) => void;
  setAIAudioUrl: (url: string | null) => void;
  setUserTranscript: (transcript: string) => void;
  setIsListening: (val: boolean) => void;
  setIsSpeaking: (val: boolean) => void;
  setIsProcessing: (val: boolean) => void;
  setShouldListen: (val: boolean) => void;
  setIsConnected: (val: boolean) => void;
  setVoiceAvailable: (val: boolean) => void;
  setAIAvailable: (val: boolean) => void;
  resetSession: () => void;
}

const initialState = {
  sessionId: null,
  state: "IDLE" as VisitorState,
  patient: null,
  language: "uz" as Language,
  departments: [],
  doctors: [],
  services: [],
  availableSlots: [],
  selectedDate: null,
  currentDepartment: null,
  currentDoctor: null,
  currentService: null,
  selectedSlot: null,
  currentAppointment: null,
  queueTicket: null,
  aiMessage: "",
  aiAudioUrl: null,
  userTranscript: "",
  isListening: false,
  isSpeaking: false,
  isProcessing: false,
  shouldListen: false,
  isConnected: false,
  voiceAvailable: true,
  aiAvailable: true,
};

export const useSessionStore = create<SessionState>()((set) => ({
  ...initialState,
  deviceId: import.meta.env.VITE_DEVICE_ID || "kiosk-001",
  clinicId: import.meta.env.VITE_CLINIC_ID || "",

  setSessionId: (sessionId) => set({ sessionId }),
  setState: (state) => set({ state }),
  setPatient: (patient) => set({ patient }),
  setLanguage: (language) => set({ language }),
  setDepartments: (departments) => set({ departments }),
  setDoctors: (doctors) => set({ doctors }),
  setServices: (services) => set({ services }),
  setAvailableSlots: (availableSlots) => set({ availableSlots }),
  setSelectedDate: (selectedDate) => set({ selectedDate }),
  setCurrentDepartment: (currentDepartment) => set({ currentDepartment }),
  setCurrentDoctor: (currentDoctor) => set({ currentDoctor }),
  setCurrentService: (currentService) => set({ currentService }),
  setSelectedSlot: (selectedSlot) => set({ selectedSlot }),
  setCurrentAppointment: (currentAppointment) => set({ currentAppointment }),
  setQueueTicket: (queueTicket) => set({ queueTicket }),
  setAIMessage: (aiMessage) => set({ aiMessage }),
  setAIAudioUrl: (aiAudioUrl) => set({ aiAudioUrl }),
  setUserTranscript: (userTranscript) => set({ userTranscript }),
  setIsListening: (isListening) => set({ isListening }),
  setIsSpeaking: (isSpeaking) => set({ isSpeaking }),
  setIsProcessing: (isProcessing) => set({ isProcessing }),
  setShouldListen: (shouldListen) => set({ shouldListen }),
  setIsConnected: (isConnected) => set({ isConnected }),
  setVoiceAvailable: (voiceAvailable) => set({ voiceAvailable }),
  setAIAvailable: (aiAvailable) => set({ aiAvailable }),
  resetSession: () =>
    set((s) => ({
      ...initialState,
      deviceId: s.deviceId,
      clinicId: s.clinicId,
    })),
}));
