import type { APIResponse } from "../types";
import { getDeviceToken } from "./socket";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

class APIError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = getDeviceToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });
  const json = (await response.json()) as APIResponse<T>;

  if (!response.ok || !json.success) {
    throw new APIError(
      json.error?.code ?? "UNKNOWN_ERROR",
      json.error?.message ?? "An unexpected error occurred",
      response.status,
    );
  }

  return json.data as T;
}

// === Department ===
export function getDepartments(clinicId?: string) {
  const query = clinicId ? `?clinic_id=${clinicId}` : "";
  return request<import("../types").Department[]>(`/departments${query}`);
}

export function getDepartment(id: string) {
  return request<import("../types").Department>(`/departments/${id}`);
}

// === Doctors ===
export function getDoctors(departmentId?: string) {
  const query = departmentId ? `?department_id=${departmentId}` : "";
  return request<import("../types").Doctor[]>(`/doctors${query}`);
}

export function getDoctor(id: string) {
  return request<import("../types").Doctor>(`/doctors/${id}`);
}

export function getAvailableSlots(doctorId: string, date: string) {
  return request<import("../types").AvailableSlots>(
    `/doctors/${doctorId}/slots?date=${date}`,
  );
}

// === Services ===
export function getServices(departmentId?: string) {
  const query = departmentId ? `?department_id=${departmentId}` : "";
  return request<import("../types").MedicalService[]>(`/services${query}`);
}

// === Patients ===
export function lookupPatient(phone: string) {
  return request<import("../types").Patient>("/patients/lookup", {
    method: "POST",
    body: JSON.stringify({ phone }),
  });
}

export function registerPatient(data: {
  full_name: string;
  phone: string;
  date_of_birth?: string;
  language_preference: string;
}) {
  return request<import("../types").Patient>("/patients", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// === Appointments ===
export function bookAppointment(data: {
  patient_id: string;
  doctor_id: string;
  service_id: string;
  scheduled_at: string;
  duration_minutes: number;
  notes?: string;
}) {
  return request<import("../types").Appointment>("/appointments", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function checkInAppointment(appointmentId: string) {
  return request<import("../types").Appointment>(
    `/appointments/${appointmentId}/check-in`,
    { method: "POST" },
  );
}

// === Queue ===
export function issueQueueTicket(data: {
  patient_id: string;
  department_id: string;
  doctor_id?: string;
}) {
  return request<import("../types").QueueTicket>("/queue", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getQueueStats() {
  return request<Record<string, unknown>>("/queue/stats");
}

// === Payments ===
export function initiatePayment(data: {
  patient_id: string;
  appointment_id: string;
  amount: number;
  method: string;
}) {
  return request<import("../types").Payment>("/payments", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// === FAQ ===
export function getFAQs(language?: string, departmentId?: string) {
  const params = new URLSearchParams();
  if (language) params.set("language", language);
  if (departmentId) params.set("department_id", departmentId);
  const query = params.toString() ? `?${params}` : "";
  return request<import("../types").FAQ[]>(`/faq${query}`);
}

// === AI ===
export function processAI(data: import("../types").OrchestratorRequest) {
  return request<import("../types").OrchestratorResponse>("/ai/process", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * Convert a data-URI or raw base64 JPEG to a File for multipart upload.
 */
function base64ToFile(frame: string, filename = "frame.jpg"): File {
  const base64 = frame.includes(",") ? frame.split(",")[1]! : frame;
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new File([bytes], filename, { type: "image/jpeg" });
}

export async function detectFaces(frame: string) {
  const formData = new FormData();
  formData.append("image", base64ToFile(frame));
  const url = `${API_BASE}/ai/detect`;
  const token = getDeviceToken();
  const res = await fetch(url, {
    method: "POST",
    body: formData,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  const json = (await res.json()) as APIResponse<import("../types").FaceDetectionResponse>;
  if (!res.ok || !json.success) {
    throw new APIError(
      json.error?.code ?? "DETECT_ERROR",
      json.error?.message ?? "Face detection failed",
      res.status,
    );
  }
  return json.data as import("../types").FaceDetectionResponse;
}

export async function identifyFace(frame: string) {
  const formData = new FormData();
  formData.append("image", base64ToFile(frame));
  const url = `${API_BASE}/ai/identify`;
  const token = getDeviceToken();
  const res = await fetch(url, {
    method: "POST",
    body: formData,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  const json = (await res.json()) as APIResponse<import("../types").FaceIdentifyResponse>;
  if (!res.ok || !json.success) {
    throw new APIError(
      json.error?.code ?? "IDENTIFY_ERROR",
      json.error?.message ?? "Face identification failed",
      res.status,
    );
  }
  return json.data as import("../types").FaceIdentifyResponse;
}

export async function speechToText(audio: Blob, format: string = "wav") {
  const formData = new FormData();
  formData.append("audio", audio);
  formData.append("format", format);
  const url = `${API_BASE}/ai/stt`;
  const token = getDeviceToken();
  const res = await fetch(url, {
    method: "POST",
    body: formData,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  const json = (await res.json()) as APIResponse<import("../types").STTResponse>;
  if (!res.ok || !json.success) {
    throw new APIError(
      json.error?.code ?? "STT_ERROR",
      json.error?.message ?? "Speech recognition failed",
      res.status,
    );
  }
  return json.data as import("../types").STTResponse;
}

export function textToSpeech(text: string, language: string) {
  return request<import("../types").TTSResponse>("/ai/tts", {
    method: "POST",
    body: JSON.stringify({ text, language }),
  });
}

export { APIError };
