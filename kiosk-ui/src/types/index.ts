// === Enums ===

export type Language = "uz" | "ru" | "en";

export type AppointmentStatus =
  | "SCHEDULED"
  | "CHECKED_IN"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
  | "NO_SHOW";

export type PaymentStatus = "PENDING" | "PAID" | "REFUNDED";

export type PaymentMethod = "CASH" | "UZCARD" | "HUMO" | "CLICK" | "PAYME";

export type TransactionStatus = "PENDING" | "COMPLETED" | "FAILED" | "REFUNDED";

export type QueueTicketStatus = "WAITING" | "IN_PROGRESS" | "COMPLETED" | "NO_SHOW";

export type DeviceStatus = "ONLINE" | "OFFLINE" | "MAINTENANCE";

export type VisitorState =
  | "IDLE"
  | "DETECTED"
  | "GREETING"
  | "INTENT_DISCOVERY"
  | "APPOINTMENT_BOOKING"
  | "SELECT_DEPARTMENT"
  | "SELECT_DOCTOR"
  | "SELECT_TIMESLOT"
  | "CONFIRM_BOOKING"
  | "BOOKING_PAYMENT"
  | "PAYMENT"
  | "SELECT_PAYMENT_METHOD"
  | "PROCESS_PAYMENT"
  | "PAYMENT_RECEIPT"
  | "BOOKING_COMPLETE"
  | "CHECK_IN"
  | "VERIFY_IDENTITY"
  | "CONFIRM_APPOINTMENT"
  | "ISSUE_QUEUE_TICKET"
  | "ROUTE_TO_DEPARTMENT"
  | "INFORMATION_INQUIRY"
  | "FAQ_RESPONSE"
  | "DEPARTMENT_INFO"
  | "DOCTOR_PROFILE"
  | "RECORD_FEEDBACK"
  | "COMPLAINT"
  | "HAND_OFF"
  | "FAREWELL";

export type InputType = "face" | "speech" | "touch" | "timeout" | "text";

// === API Response ===

export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: { code: string; message: string } | null;
  meta?: { page: number; limit: number; total: number } | null;
}

// === Domain Models ===

export interface Clinic {
  id: string;
  name: string;
  address: string;
  phone: string;
  logo_url: string | null;
}

export interface Department {
  id: string;
  clinic_id: string;
  name: string;
  description: string | null;
  floor: number | null;
  room_number: string | null;
  is_active: boolean;
  sort_order: number;
  doctor_count: number;
  icon?: string;
  created_at: string;
  updated_at: string;
}

export interface DoctorSchedule {
  id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  break_start: string | null;
  break_end: string | null;
  is_active: boolean;
}

export interface Doctor {
  id: string;
  clinic_id: string;
  department_id: string;
  full_name: string;
  specialty: string;
  bio: string | null;
  photo_url: string | null;
  is_active: boolean;
  department_name: string;
  schedules: DoctorSchedule[];
  next_available_slot: string | null;
  created_at: string;
  updated_at: string;
}

export interface MedicalService {
  id: string;
  clinic_id: string;
  department_id: string;
  name: string;
  description: string | null;
  duration_minutes: number;
  price_uzs: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TimeSlot {
  start_time: string;
  end_time: string;
  is_available: boolean;
}

export interface AvailableSlots {
  date: string;
  doctor_id: string;
  slots: TimeSlot[];
}

export interface Patient {
  id: string;
  clinic_id: string;
  full_name: string;
  phone: string;
  date_of_birth: string | null;
  language_preference: Language;
  has_face_embedding: boolean;
  created_at: string;
  updated_at: string;
}

export interface Appointment {
  id: string;
  clinic_id: string;
  patient_id: string;
  doctor_id: string;
  service_id: string;
  scheduled_at: string;
  duration_minutes: number;
  status: AppointmentStatus;
  payment_status: PaymentStatus;
  notes: string | null;
  patient_name: string;
  doctor_name: string;
  service_name: string;
  created_at: string;
  updated_at: string;
}

export interface Payment {
  id: string;
  clinic_id: string;
  patient_id: string;
  appointment_id: string | null;
  amount: number;
  method: PaymentMethod;
  status: TransactionStatus;
  transaction_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface QueueTicket {
  id: string;
  clinic_id: string;
  patient_id: string;
  department_id: string;
  doctor_id: string | null;
  ticket_number: string;
  status: QueueTicketStatus;
  estimated_wait_minutes: number;
  department_name: string;
  called_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface FAQ {
  id: string;
  question: string;
  answer: string;
  language: Language;
  department_id: string | null;
  is_active: boolean;
  sort_order: number;
}

// === AI Types ===

export interface OrchestratorRequest {
  session_id: string;
  device_id: string;
  clinic_id: string;
  input_type: InputType;
  data: Record<string, unknown>;
}

export interface OrchestratorResponse {
  session_id: string;
  text: string;
  audio_base64: string | null;
  state: VisitorState;
  ui_action: string | null;
  ui_data: Record<string, unknown> | null;
  patient: { id: string; name: string } | null;
  transcript: string | null;
}

export interface FunctionCallResult {
  name: string;
  result: Record<string, unknown>;
}

export interface DetectedFace {
  bbox: { x: number; y: number; width: number; height: number };
  confidence: number;
}

export interface FaceDetectionResponse {
  faces: DetectedFace[];
}

export interface FaceIdentifyResponse {
  patient_id: string | null;
  similarity: number;
  patient_name: string | null;
}

export interface STTResponse {
  transcript: string;
  language: Language;
  confidence: number;
}

export interface TTSResponse {
  audio_url: string | null;
  audio_bytes: string | null;
}

// === Socket Events ===

export interface KioskEmitEvents {
  "kiosk:face_frame": { device_id: string; frame: string };
  "kiosk:speech_audio": { device_id: string; session_id: string; audio: string; format: string };
  "kiosk:chat_text": { device_id: string; session_id: string; text: string; language: string };
  "kiosk:touch_action": { device_id: string; session_id: string; action: string; data: Record<string, unknown> };
}

export interface KioskListenEvents {
  "ai:response": OrchestratorResponse;
  "ai:state_change": { session_id: string; state: VisitorState };
  "ai:error": { session_id: string; code: string; message: string };
  "session:timeout": { session_id: string; warning: boolean };
  "queue:update": { department_id: string; tickets: QueueTicket[] };
}
