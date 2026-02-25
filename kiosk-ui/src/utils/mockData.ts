import type {
  Department,
  Doctor,
  DoctorSchedule,
  MedicalService,
  TimeSlot,
  Patient,
  Appointment,
  QueueTicket,
  FAQ,
} from "../types";

// ── Clinic ID (demo) ────────────────────────────────────────

const CLINIC_ID = "clinic-demo-001";

// ── Departments (8 Nano Medical departments) ─────────────────

export const MOCK_DEPARTMENTS: Department[] = [
  {
    id: "dept-endokrinologiya",
    clinic_id: CLINIC_ID,
    name: "Endokrinologiya",
    description: "Endokrin tizim kasalliklari",
    floor: 1,
    room_number: "101",
    is_active: true,
    sort_order: 1,
    doctor_count: 1,
    icon: "🔬",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "dept-xirurgiya",
    clinic_id: CLINIC_ID,
    name: "Xirurgiya",
    description: "Jarrohlik xizmatlari",
    floor: 1,
    room_number: "102",
    is_active: true,
    sort_order: 2,
    doctor_count: 1,
    icon: "🔪",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "dept-nevrologiya",
    clinic_id: CLINIC_ID,
    name: "Nevrologiya",
    description: "Asab tizimi kasalliklari",
    floor: 2,
    room_number: "201",
    is_active: true,
    sort_order: 3,
    doctor_count: 1,
    icon: "🧠",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "dept-kardiologiya",
    clinic_id: CLINIC_ID,
    name: "Kardiologiya",
    description: "Yurak-qon tomir kasalliklari",
    floor: 2,
    room_number: "202",
    is_active: true,
    sort_order: 4,
    doctor_count: 1,
    icon: "🫀",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "dept-mammologiya",
    clinic_id: CLINIC_ID,
    name: "Mammologiya",
    description: "Ko'krak bezi kasalliklari",
    floor: 2,
    room_number: "203",
    is_active: true,
    sort_order: 5,
    doctor_count: 1,
    icon: "🩺",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "dept-terapiya",
    clinic_id: CLINIC_ID,
    name: "Terapiya",
    description: "Umumiy terapevtik xizmatlar",
    floor: 1,
    room_number: "103",
    is_active: true,
    sort_order: 6,
    doctor_count: 0,
    icon: "💊",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "dept-radiologiya",
    clinic_id: CLINIC_ID,
    name: "Radiologiya",
    description: "Radiologik tekshiruvlar",
    floor: 1,
    room_number: "104",
    is_active: true,
    sort_order: 7,
    doctor_count: 0,
    icon: "📡",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "dept-reanimatsiya",
    clinic_id: CLINIC_ID,
    name: "Reanimatsiya",
    description: "Shoshilinch tibbiy yordam",
    floor: 1,
    room_number: "105",
    is_active: true,
    sort_order: 8,
    doctor_count: 0,
    icon: "🚑",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
];

// ── Schedules ───────────────────────────────────────────────

function makeSchedule(
  doctorId: string,
  startTime = "08:00",
  endTime = "16:00",
  breakStart = "12:00",
  breakEnd = "13:00",
): DoctorSchedule[] {
  return [1, 2, 3, 4, 5, 6].map((day) => ({
    id: `sched-${doctorId}-${day}`,
    day_of_week: day,
    start_time: startTime,
    end_time: endTime,
    break_start: breakStart,
    break_end: breakEnd,
    is_active: true,
  }));
}

// ── Doctors (5 real Nano Medical doctors) ────────────────────

export const MOCK_DOCTORS: Doctor[] = [
  {
    id: "doc-nasirxodjaev",
    clinic_id: CLINIC_ID,
    department_id: "dept-endokrinologiya",
    full_name: "Nasirxodjaev Yo.B.",
    specialty: "Endokrinolog-radiolog",
    bio: "28 yillik tajriba. Endokrin tizim kasalliklari mutaxassisi.",
    photo_url: null,
    is_active: true,
    department_name: "Endokrinologiya",
    schedules: makeSchedule("doc-nasirxodjaev", "08:00", "16:00"),
    next_available_slot: getTodayAt(10, 0),
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "doc-aripova",
    clinic_id: CLINIC_ID,
    department_id: "dept-xirurgiya",
    full_name: "Aripova N.M.",
    specialty: "Proktolog, yiringli jarroh",
    bio: "35 yillik tajriba. Jarrohlik bo'yicha oliy toifali mutaxassis.",
    photo_url: null,
    is_active: true,
    department_name: "Xirurgiya",
    schedules: makeSchedule("doc-aripova", "09:00", "16:00"),
    next_available_slot: getTodayAt(11, 0),
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "doc-malikov-nevro",
    clinic_id: CLINIC_ID,
    department_id: "dept-nevrologiya",
    full_name: "Malikov A.V.",
    specialty: "Nevropatolog",
    bio: "30 yillik tajriba. Asab tizimi kasalliklari mutaxassisi.",
    photo_url: null,
    is_active: true,
    department_name: "Nevrologiya",
    schedules: makeSchedule("doc-malikov-nevro", "08:00", "16:00"),
    next_available_slot: getTodayAt(9, 30),
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "doc-malikov-kardio",
    clinic_id: CLINIC_ID,
    department_id: "dept-kardiologiya",
    full_name: "Malikov A.V.",
    specialty: "Kardiolog",
    bio: "35 yillik tajriba. Yurak-qon tomir kasalliklari mutaxassisi.",
    photo_url: null,
    is_active: true,
    department_name: "Kardiologiya",
    schedules: makeSchedule("doc-malikov-kardio", "08:00", "16:00"),
    next_available_slot: getTodayAt(14, 0),
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "doc-alimxodjaeva",
    clinic_id: CLINIC_ID,
    department_id: "dept-mammologiya",
    full_name: "Prof. Alimxodjaeva L.T.",
    specialty: "Professor, Mammolog",
    bio: "30 yillik tajriba. Mammologiya bo'yicha professor.",
    photo_url: null,
    is_active: true,
    department_name: "Mammologiya",
    schedules: makeSchedule("doc-alimxodjaeva", "10:00", "13:00", "12:00", "12:00"),
    next_available_slot: getTodayAt(10, 30),
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
];

// ── Services (8 real Nano Medical services) ──────────────────

export const MOCK_SERVICES: MedicalService[] = [
  {
    id: "svc-konsultatsiya",
    clinic_id: CLINIC_ID,
    department_id: "dept-endokrinologiya",
    name: "Konsultatsiya",
    description: "Birlamchi ko'rik",
    duration_minutes: 30,
    price_uzs: 260000,
    is_active: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "svc-professor",
    clinic_id: CLINIC_ID,
    department_id: "dept-mammologiya",
    name: "Professor konsultatsiyasi",
    description: "Professor tomonidan birlamchi ko'rik",
    duration_minutes: 40,
    price_uzs: 500000,
    is_active: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "svc-checkup-erkak",
    clinic_id: CLINIC_ID,
    department_id: "dept-terapiya",
    name: "Checkup — Erkaklar",
    description: "Erkaklar uchun to'liq tekshiruv",
    duration_minutes: 120,
    price_uzs: 2000000,
    is_active: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "svc-checkup-ayol",
    clinic_id: CLINIC_ID,
    department_id: "dept-terapiya",
    name: "Checkup — Ayollar",
    description: "Ayollar uchun to'liq tekshiruv",
    duration_minutes: 120,
    price_uzs: 2000000,
    is_active: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "svc-terapiya-palata",
    clinic_id: CLINIC_ID,
    department_id: "dept-terapiya",
    name: "Terapiya — Lyuks palata",
    description: "Lyuks palata, ovqatlanish bilan",
    duration_minutes: 0,
    price_uzs: 1500000,
    is_active: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "svc-xirurgiya-palata",
    clinic_id: CLINIC_ID,
    department_id: "dept-xirurgiya",
    name: "Xirurgiya — Lyuks palata",
    description: "Lyuks palata, ovqatlanish bilan",
    duration_minutes: 0,
    price_uzs: 1200000,
    is_active: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "svc-radiologiya",
    clinic_id: CLINIC_ID,
    department_id: "dept-radiologiya",
    name: "Radiologiya bo'limi",
    description: "Ovqatlanish bilan",
    duration_minutes: 0,
    price_uzs: 1100000,
    is_active: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "svc-reanimatsiya",
    clinic_id: CLINIC_ID,
    department_id: "dept-reanimatsiya",
    name: "Reanimatsiya bo'limi",
    description: "Ovqatlanish bilan",
    duration_minutes: 0,
    price_uzs: 2100000,
    is_active: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
];

// ── Time Slots (generate for any date) ──────────────────────

export function generateTimeSlots(date: string): TimeSlot[] {
  const slots: TimeSlot[] = [];
  const hours = [8, 9, 10, 11, 13, 14, 15, 16];

  for (const h of hours) {
    for (const m of [0, 30]) {
      if (h === 16 && m === 30) continue; // end of day at 17:00
      const start = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:00`;
      const endH = m === 30 ? h + 1 : h;
      const endM = m === 30 ? 0 : 30;
      const end = `${String(endH).padStart(2, "0")}:${String(endM).padStart(2, "0")}:00`;

      // Randomly make ~25% unavailable
      const seed = hashCode(`${date}-${start}`);
      const isAvailable = seed % 4 !== 0;

      slots.push({
        start_time: start,
        end_time: end,
        is_available: isAvailable,
      });
    }
  }

  return slots;
}

// ── Sample Patient ──────────────────────────────────────────

export const MOCK_PATIENT: Patient = {
  id: "patient-001",
  clinic_id: CLINIC_ID,
  full_name: "Kamolov Otabek Sherzod o'g'li",
  phone: "+998901234567",
  date_of_birth: "1985-03-15",
  language_preference: "uz",
  has_face_embedding: false,
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
};

// ── Sample Appointment ──────────────────────────────────────

export const MOCK_APPOINTMENT: Appointment = {
  id: "appt-001",
  clinic_id: CLINIC_ID,
  patient_id: "patient-001",
  doctor_id: "doc-nasirxodjaev",
  service_id: "svc-konsultatsiya",
  scheduled_at: getTodayAt(14, 30),
  duration_minutes: 30,
  status: "SCHEDULED",
  payment_status: "PENDING",
  notes: null,
  patient_name: "Kamolov Otabek Sherzod o'g'li",
  doctor_name: "Nasirxodjaev Yo.B.",
  service_name: "Konsultatsiya",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
};

// ── Sample Queue Ticket ─────────────────────────────────────

export const MOCK_QUEUE_TICKET: QueueTicket = {
  id: "ticket-001",
  clinic_id: CLINIC_ID,
  patient_id: "patient-001",
  department_id: "dept-endokrinologiya",
  doctor_id: "doc-nasirxodjaev",
  ticket_number: "E-014",
  status: "WAITING",
  estimated_wait_minutes: 12,
  department_name: "Endokrinologiya",
  called_at: null,
  completed_at: null,
  created_at: new Date().toISOString(),
};

// ── FAQ Items (Nano Medical) ─────────────────────────────────

export const MOCK_FAQS: FAQ[] = [
  {
    id: "faq-001",
    question: "Klinika qaysi soatlarda ishlaydi?",
    answer: "Nano Medical Clinic dushanba-shanba kunlari soat 08:00 dan 17:00 gacha ishlaydi. Yakshanba — dam olish kuni.",
    language: "uz",
    department_id: null,
    is_active: true,
    sort_order: 1,
  },
  {
    id: "faq-002",
    question: "Qabulga qanday yozilaman?",
    answer: "Kiosk terminal orqali yoki telefon raqamlarimizga qo'ng'iroq qilib yozilishingiz mumkin: +998 78 113 08 88, +998 55 500 05 50, +998 99 467 80 00.",
    language: "uz",
    department_id: null,
    is_active: true,
    sort_order: 2,
  },
  {
    id: "faq-003",
    question: "To'lov qanday usullarda qabul qilinadi?",
    answer: "Naqd pul, Uzcard, Humo, Click va Payme orqali to'lashingiz mumkin.",
    language: "uz",
    department_id: null,
    is_active: true,
    sort_order: 3,
  },
  {
    id: "faq-004",
    question: "Konsultatsiya narxi qancha?",
    answer: "Oddiy konsultatsiya 260,000 so'm, professor konsultatsiyasi 500,000 so'm.",
    language: "uz",
    department_id: null,
    is_active: true,
    sort_order: 4,
  },
  {
    id: "faq-005",
    question: "Klinika manzili qayerda?",
    answer: "Toshkent shahri, Olmazor tumani, Talabalar ko'chasi, 52-uy.",
    language: "uz",
    department_id: null,
    is_active: true,
    sort_order: 5,
  },
  {
    id: "faq-006",
    question: "Qanday shifokorlar bor?",
    answer: "Bizda endokrinolog, jarroh (proktolog), nevropatolog, kardiolog va mammolog ishlaydi.",
    language: "uz",
    department_id: null,
    is_active: true,
    sort_order: 6,
  },
];

// ── Helpers ─────────────────────────────────────────────────

function getTodayAt(hours: number, minutes: number): string {
  const d = new Date();
  d.setHours(hours, minutes, 0, 0);
  return d.toISOString();
}

function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  return Math.abs(hash);
}

// ── Get doctors filtered by department ──────────────────────

export function getDoctorsByDepartment(departmentId: string): Doctor[] {
  return MOCK_DOCTORS.filter((d) => d.department_id === departmentId);
}

// ── Get services filtered by department ─────────────────────

export function getServicesByDepartment(departmentId: string): MedicalService[] {
  return MOCK_SERVICES.filter((s) => s.department_id === departmentId);
}
