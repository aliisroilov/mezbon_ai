import type { APIResponse } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export class APIError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function refreshAccessToken(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return null;
    const json = (await res.json()) as APIResponse<{ access_token: string }>;
    if (json.success && json.data) {
      accessToken = json.data.access_token;
      return accessToken;
    }
    return null;
  } catch {
    return null;
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  let response = await fetch(url, { ...options, headers, credentials: "include" });

  if (response.status === 401 && accessToken) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }
    const newToken = await refreshPromise;
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(url, { ...options, headers, credentials: "include" });
    } else {
      accessToken = null;
      window.location.href = "/login";
      throw new APIError("UNAUTHORIZED", "Session expired", 401);
    }
  }

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

export async function requestWithMeta<T>(
  path: string,
  options: RequestInit = {},
): Promise<{ data: T; meta: { page: number; limit: number; total: number } | null }> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, { ...options, headers, credentials: "include" });
  const json = (await response.json()) as APIResponse<T>;

  if (!response.ok || !json.success) {
    throw new APIError(
      json.error?.code ?? "UNKNOWN_ERROR",
      json.error?.message ?? "An unexpected error occurred",
      response.status,
    );
  }

  return { data: json.data as T, meta: json.meta ?? null };
}

export async function uploadFile(path: string, file: File): Promise<{ url: string }> {
  const url = `${API_BASE}${path}`;
  const formData = new FormData();
  formData.append("file", file);

  const headers: Record<string, string> = {};
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: formData,
    credentials: "include",
  });

  const json = (await response.json()) as APIResponse<{ url: string }>;

  if (!response.ok || !json.success) {
    throw new APIError(
      json.error?.code ?? "UPLOAD_ERROR",
      json.error?.message ?? "File upload failed",
      response.status,
    );
  }

  return json.data as { url: string };
}

// === Auth API ===
export const authAPI = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: import("../types").User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () =>
    request<null>("/auth/logout", { method: "POST" }),
  me: () =>
    request<import("../types").User>("/auth/me"),
};

// === Departments API ===
export const departmentsAPI = {
  list: () => request<import("../types").Department[]>("/departments"),
  get: (id: string) => request<import("../types").Department>(`/departments/${id}`),
  create: (data: Partial<import("../types").Department>) =>
    request<import("../types").Department>("/departments", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<import("../types").Department>) =>
    request<import("../types").Department>(`/departments/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<null>(`/departments/${id}`, { method: "DELETE" }),
};

// === Doctors API ===
export const doctorsAPI = {
  list: (params?: { department_id?: string; page?: number; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.department_id) searchParams.set("department_id", params.department_id);
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.limit) searchParams.set("limit", String(params.limit));
    const q = searchParams.toString();
    return request<import("../types").Doctor[]>(`/doctors${q ? `?${q}` : ""}`);
  },
  get: (id: string) => request<import("../types").Doctor>(`/doctors/${id}`),
  create: (data: Record<string, unknown>) =>
    request<import("../types").Doctor>("/doctors", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Record<string, unknown>) =>
    request<import("../types").Doctor>(`/doctors/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<null>(`/doctors/${id}`, { method: "DELETE" }),
  getSlots: (doctorId: string, date: string) =>
    request<import("../types").TimeSlot[]>(`/doctors/${doctorId}/slots?date=${date}`),
  updateSchedule: (doctorId: string, schedules: import("../types").DoctorSchedule[]) =>
    request<import("../types").DoctorSchedule[]>(`/doctors/${doctorId}/schedule`, {
      method: "PUT",
      body: JSON.stringify({ schedules }),
    }),
  updateServices: (doctorId: string, services: { service_id: string; price_uzs: number }[]) =>
    request<import("../types").DoctorServiceAssignment[]>(`/doctors/${doctorId}/services`, {
      method: "PUT",
      body: JSON.stringify({ services }),
    }),
};

// === Patients API ===
export const patientsAPI = {
  list: (params?: { search?: string; page?: number; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set("search", params.search);
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.limit) searchParams.set("limit", String(params.limit));
    const q = searchParams.toString();
    return requestWithMeta<import("../types").Patient[]>(`/patients${q ? `?${q}` : ""}`);
  },
  get: (id: string) => request<import("../types").Patient>(`/patients/${id}`),
  create: (data: Record<string, unknown>) =>
    request<import("../types").Patient>("/patients", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Record<string, unknown>) =>
    request<import("../types").Patient>(`/patients/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  getVisits: (patientId: string) =>
    request<import("../types").VisitLog[]>(`/patients/${patientId}/visits`),
  getPayments: (patientId: string) =>
    request<import("../types").Payment[]>(`/patients/${patientId}/payments`),
  getAppointments: (patientId: string) =>
    request<import("../types").Appointment[]>(`/patients/${patientId}/appointments`),
  getConsents: (patientId: string) =>
    request<import("../types").ConsentRecord[]>(`/patients/${patientId}/consents`),
};

// === Appointments API ===
export const appointmentsAPI = {
  list: (params?: {
    date_from?: string;
    date_to?: string;
    doctor_id?: string;
    department_id?: string;
    status?: string;
    page?: number;
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined) searchParams.set(key, String(val));
      });
    }
    const q = searchParams.toString();
    return requestWithMeta<import("../types").Appointment[]>(`/appointments${q ? `?${q}` : ""}`);
  },
  get: (id: string) => request<import("../types").Appointment>(`/appointments/${id}`),
  updateStatus: (id: string, status: import("../types").AppointmentStatus) =>
    request<import("../types").Appointment>(`/appointments/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  cancel: (id: string, reason?: string) =>
    request<import("../types").Appointment>(`/appointments/${id}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
};

// === Queue API ===
export const queueAPI = {
  list: (params?: { department_id?: string; status?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.department_id) searchParams.set("department_id", params.department_id);
    if (params?.status) searchParams.set("status", params.status);
    const q = searchParams.toString();
    return request<import("../types").QueueTicket[]>(`/queue${q ? `?${q}` : ""}`);
  },
  callNext: (departmentId: string) =>
    request<import("../types").QueueTicket>(`/queue/call-next`, {
      method: "POST",
      body: JSON.stringify({ department_id: departmentId }),
    }),
  complete: (ticketId: string) =>
    request<import("../types").QueueTicket>(`/queue/${ticketId}/complete`, {
      method: "POST",
    }),
  stats: () =>
    request<Record<string, unknown>>("/queue/stats"),
};

// === Payments API ===
export const paymentsAPI = {
  list: (params?: { page?: number; limit?: number; status?: string }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined) searchParams.set(key, String(val));
      });
    }
    const q = searchParams.toString();
    return requestWithMeta<import("../types").Payment[]>(`/payments${q ? `?${q}` : ""}`);
  },
  get: (id: string) => request<import("../types").Payment>(`/payments/${id}`),
};

// === Devices API ===
export const devicesAPI = {
  list: () => request<import("../types").Device[]>("/devices"),
  get: (id: string) => request<import("../types").Device>(`/devices/${id}`),
  register: (data: Record<string, unknown>) =>
    request<import("../types").Device>("/devices", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateConfig: (id: string, config: Record<string, unknown>) =>
    request<import("../types").Device>(`/devices/${id}/config`, {
      method: "PATCH",
      body: JSON.stringify({ config }),
    }),
  getHeartbeats: (id: string, hours?: number) =>
    request<import("../types").DeviceHeartbeat[]>(
      `/devices/${id}/heartbeats${hours ? `?hours=${hours}` : ""}`,
    ),
  restart: (id: string) =>
    request<null>(`/devices/${id}/restart`, { method: "POST" }),
  setMaintenance: (id: string, enabled: boolean) =>
    request<import("../types").Device>(`/devices/${id}/maintenance`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
};

// === FAQ API ===
export const faqAPI = {
  list: (params?: { language?: string }) => {
    const q = params?.language ? `?language=${params.language}` : "";
    return request<import("../types").FAQ[]>(`/faq${q}`);
  },
  create: (data: Record<string, unknown>) =>
    request<import("../types").FAQ>("/faq", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Record<string, unknown>) =>
    request<import("../types").FAQ>(`/faq/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<null>(`/faq/${id}`, { method: "DELETE" }),
};

// === Content API ===
export const contentAPI = {
  announcements: {
    list: () => request<import("../types").Announcement[]>("/content/announcements"),
    create: (data: Record<string, unknown>) =>
      request<import("../types").Announcement>("/content/announcements", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Record<string, unknown>) =>
      request<import("../types").Announcement>(`/content/announcements/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<null>(`/content/announcements/${id}`, { method: "DELETE" }),
  },
  media: {
    list: () => request<{ url: string; name: string; size: number; uploaded_at: string }[]>("/content/media"),
    upload: (file: File) => uploadFile("/content/media", file),
    delete: (name: string) =>
      request<null>(`/content/media/${encodeURIComponent(name)}`, { method: "DELETE" }),
  },
};

// === Analytics API ===
export const analyticsAPI = {
  dashboard: () =>
    request<import("../types").DashboardStats>("/analytics/dashboard"),
  visitors: (params: { from: string; to: string }) =>
    request<import("../types").ChartDataPoint[]>(
      `/analytics/visitors?from=${params.from}&to=${params.to}`,
    ),
  appointmentsByDepartment: (params: { from: string; to: string }) =>
    request<import("../types").DepartmentStat[]>(
      `/analytics/appointments-by-department?from=${params.from}&to=${params.to}`,
    ),
  revenue: (params: { from: string; to: string }) =>
    request<import("../types").ChartDataPoint[]>(
      `/analytics/revenue?from=${params.from}&to=${params.to}`,
    ),
  intents: (params: { from: string; to: string }) =>
    request<{ name: string; value: number }[]>(
      `/analytics/intents?from=${params.from}&to=${params.to}`,
    ),
  languages: (params: { from: string; to: string }) =>
    request<{ name: string; value: number }[]>(
      `/analytics/languages?from=${params.from}&to=${params.to}`,
    ),
  satisfaction: (params: { from: string; to: string }) =>
    request<import("../types").ChartDataPoint[]>(
      `/analytics/satisfaction?from=${params.from}&to=${params.to}`,
    ),
  peakHours: (params: { from: string; to: string }) =>
    request<{ hour: number; weekday: number; count: number }[]>(
      `/analytics/peak-hours?from=${params.from}&to=${params.to}`,
    ),
  funnel: (params: { from: string; to: string }) =>
    request<{ stage: string; count: number }[]>(
      `/analytics/funnel?from=${params.from}&to=${params.to}`,
    ),
  activityFeed: () =>
    request<import("../types").ActivityFeedItem[]>("/analytics/activity-feed"),
};

// === Settings API ===
export const settingsAPI = {
  getClinic: () => request<import("../types").Clinic>("/admin/settings/clinic"),
  updateClinic: (data: Record<string, unknown>) =>
    request<import("../types").Clinic>("/admin/settings/clinic", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  getUsers: () => request<import("../types").User[]>("/admin/settings/users"),
  createUser: (data: Record<string, unknown>) =>
    request<import("../types").User>("/admin/settings/users", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteUser: (id: string) =>
    request<null>(`/admin/settings/users/${id}`, { method: "DELETE" }),
  updateUserRole: (id: string, role: import("../types").UserRole) =>
    request<import("../types").User>(`/admin/settings/users/${id}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),
};
