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

export type UserRole = "SUPER_ADMIN" | "CLINIC_ADMIN" | "STAFF";

// === API Response ===

export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: { code: string; message: string } | null;
  meta?: { page: number; limit: number; total: number } | null;
}

// === Auth ===

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  clinic_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

// === Domain Models ===

export interface Clinic {
  id: string;
  name: string;
  address: string;
  phone: string;
  logo_url: string | null;
  working_hours: Record<string, { open: string; close: string }> | null;
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
  services?: DoctorServiceAssignment[];
  next_available_slot: string | null;
  created_at: string;
  updated_at: string;
}

export interface DoctorServiceAssignment {
  service_id: string;
  service_name: string;
  price_uzs: number;
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
  department_name?: string;
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
  patient_name?: string;
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
  patient_name?: string;
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

export interface Announcement {
  id: string;
  clinic_id: string;
  title: string;
  body: string;
  language: Language;
  active_from: string;
  active_to: string;
  is_active: boolean;
  created_at: string;
}

export interface Device {
  id: string;
  clinic_id: string;
  serial_number: string;
  name: string;
  location: string;
  status: DeviceStatus;
  config: Record<string, unknown>;
  last_heartbeat: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeviceHeartbeat {
  id: string;
  device_id: string;
  timestamp: string;
  uptime_seconds: number;
  cpu_percent: number;
  memory_percent: number;
  errors: string[];
}

export interface ConsentRecord {
  id: string;
  patient_id: string;
  consent_type: string;
  granted_at: string;
  device_id: string | null;
  revoked_at: string | null;
}

export interface VisitLog {
  id: string;
  patient_id: string | null;
  device_id: string;
  session_id: string;
  intent: string;
  language: Language;
  sentiment: string | null;
  success: boolean;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  created_at: string;
}

// === Analytics ===

export interface DashboardStats {
  today_visitors: number;
  today_appointments: number;
  today_revenue: number;
  avg_wait_minutes: number;
  visitors_change: number;
  appointments_change: number;
  revenue_change: number;
  wait_change: number;
}

export interface ChartDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface DepartmentStat {
  department_id: string;
  department_name: string;
  appointments: number;
  revenue: number;
}

export interface ActivityFeedItem {
  id: string;
  type: "appointment" | "payment" | "check_in" | "queue" | "device";
  message: string;
  timestamp: string;
}

// === Socket Events ===

export interface AdminListenEvents {
  "queue:update": { department_id: string; tickets: QueueTicket[] };
  "device:heartbeat": DeviceHeartbeat;
  "device:status_change": { device_id: string; status: DeviceStatus };
  "payment:confirmed": Payment;
  "appointment:update": Appointment;
  "activity:new": ActivityFeedItem;
}
