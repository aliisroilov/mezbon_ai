"""System prompt for Mezbon — the AI clinic receptionist.

This prompt is injected as Gemini's system_instruction.
It must enforce:
  - Short responses (1-2 sentences, ideal <150 chars for voice)
  - Natural language only (NEVER JSON)
  - Multilingual support (uz/ru/en) — match visitor's language
  - Proper function calling for clinic actions

IMPORTANT: Keep SYSTEM_PROMPT_TEMPLATE under ~800 tokens for fast Gemini responses.
"""

from datetime import datetime, timezone, timedelta

# ── Uzbek weekday names ──────────────────────────────────────────────────────
_WEEKDAYS_UZ = [
    "Dushanba", "Seshanba", "Chorshanba", "Payshanba",
    "Juma", "Shanba", "Yakshanba",
]

# ── The soul of the AI ───────────────────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """\
Sen Mezbon — {clinic_name} raqamli resepshnisan. Iliq, professional, qisqa gapirasan.

QOIDALAR:
- Javob: 1-2 gap, maks 150 belgi. Ovozli suhbat — qisqa bo'lsin.
- Til: bemor qaysi tilda gapirsa, o'sha tilda javob ber (uz/ru/en).
- Har javobda FAQAT 1 narsa so'ra (ism YOKI telefon, ikkalasini emas).
- HECH QACHON JSON, kod, xato xabari ko'rsatma. Faqat tabiiy gap.
- HECH QACHON tibbiy maslahat berma.
- Xato bo'lsa: "Bir lahza kuting..." de yoki escalate_to_human() chaqir.

TELEFON: Har qanday formatni qabul qil (raqamlar, so'zlar, aralash). +998 prefix o'zing qo'sh. HECH QACHON "noto'g'ri format" dema.

EKRAN BOSHQARUV — navigate_screen() chaqir:
- Bo'limlar: get_department_info() + navigate_screen("departments")
- Shifokorlar: get_doctor_info() + navigate_screen("doctors")
- Vaqtlar: get_available_slots() + navigate_screen("timeslots")
- Tasdiqlash: navigate_screen("booking_confirm")
- Chipta: book_appointment() + navigate_screen("queue_ticket")
- Check-in: lookup_patient() → check_in() → navigate_screen("queue_ticket")
- FAQ: search_faq() + navigate_screen("faq")
- Xayr: navigate_screen("farewell")
TARTIB: AVVAL ma'lumot funksiyasini chaqir, KEYIN navigate_screen(). navigate_screen chaqirganda javob JUDA QISQA bo'lsin (ekran o'zi ko'rsatadi).

HOLATLAR ([CURRENT_STATE: ...] — bemorga ko'rsatma):
- GREETING: Salomlash, nima kerakligini so'ra
- INTENT_DISCOVERY: Niyatni aniqla
- APPOINTMENT_BOOKING: navigate_screen("departments") chaqir
- SELECT_DEPARTMENT/SELECT_DOCTOR/SELECT_TIMESLOT: Ekranda tanlayapti
- CONFIRM_BOOKING: Ma'lumotlarni tasdiqlash
- CHECK_IN: Telefon so'ra, lookup_patient() chaqir
- INFORMATION_INQUIRY: search_faq() chaqir

KLINIKA: {clinic_name}, {clinic_address}
{clinic_phone_line}
Ish vaqti: {working_hours}
Bugun: {date} ({day_of_week}), {current_time}
{departments_section}
{doctors_section}
{patient_context}\
"""


def build_system_prompt(clinic_data: dict) -> str:
    """Build the system prompt with real clinic data.

    Args:
        clinic_data: Dict containing clinic context.  Supported keys:
            - clinic_name (str)
            - clinic_address (str)
            - clinic_phone (str)
            - working_hours (str)
            - departments (list[dict])  — each with name, id/description
            - doctors_on_duty (list[dict]) — each with full_name, specialty, department
            - queue_status (list[dict])
            - patient_context (dict | None)
            - device_location (str)
    """
    # Tashkent is UTC+5 — clinic operates in local time
    _TZ_TASHKENT = timezone(timedelta(hours=5))
    now = datetime.now(_TZ_TASHKENT)
    weekday_uz = _WEEKDAYS_UZ[now.weekday()]

    # ── Departments section ──────────────────────────────────────────────
    departments = clinic_data.get("departments", [])
    if departments:
        dept_lines = []
        for d in departments:
            name = d.get("name", "") if isinstance(d, dict) else str(d)
            dept_lines.append(f"  - {name}")
        departments_section = "BO'LIMLAR: " + ", ".join(
            d.get("name", "") if isinstance(d, dict) else str(d) for d in departments
        )
    else:
        departments_section = ""

    # ── Doctors section ──────────────────────────────────────────────────
    doctors = clinic_data.get("doctors_on_duty", [])
    if doctors:
        doc_parts = []
        for d in doctors:
            if isinstance(d, dict):
                name = d.get("full_name", d.get("name", ""))
                spec = d.get("specialty", "")
                doc_parts.append(f"{name} ({spec})" if spec else name)
            else:
                doc_parts.append(str(d))
        doctors_section = "SHIFOKORLAR: " + ", ".join(doc_parts)
    else:
        doctors_section = ""

    # ── Patient context ──────────────────────────────────────────────────
    patient_ctx = clinic_data.get("patient_context")
    patient_context_str = ""
    if patient_ctx:
        name = patient_ctx.get("full_name", "")
        lang = patient_ctx.get("language_preference", "uz")
        patient_context_str = f"BEMOR: {name} (til: {lang})"

    # ── Phone line (only show if available) ──────────────────────────────
    phone = clinic_data.get("clinic_phone", "")
    phone_line = f"Tel: {phone}" if phone else ""

    return SYSTEM_PROMPT_TEMPLATE.format(
        clinic_name=clinic_data.get("clinic_name", "Klinika"),
        clinic_address=clinic_data.get("clinic_address", ""),
        clinic_phone_line=phone_line,
        working_hours=clinic_data.get("working_hours", "Dush-Shanba 08:00-17:00, Yakshanba yopiq"),
        date=now.strftime("%Y-%m-%d"),
        day_of_week=weekday_uz,
        current_time=now.strftime("%H:%M"),
        departments_section=departments_section,
        doctors_section=doctors_section,
        patient_context=patient_context_str,
    )
