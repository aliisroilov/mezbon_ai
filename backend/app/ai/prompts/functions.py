"""Gemini function declarations for clinic receptionist actions."""

from google.generativeai.types import FunctionDeclaration, Tool

book_appointment = FunctionDeclaration(
    name="book_appointment",
    description=(
        "Book a new appointment for a patient. Use this when the visitor confirms they want to book. "
        "You can pass either doctor_id (UUID) or doctor name — the system handles both. "
        "IMPORTANT: Always confirm date, time, and doctor with the visitor before calling this."
    ),
    parameters={
        "type": "object",
        "properties": {
            "doctor_id": {
                "type": "string",
                "description": "Doctor UUID or name.",
            },
            "service_id": {
                "type": "string",
                "description": "Service UUID (use department ID if unknown).",
            },
            "date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format.",
            },
            "time": {
                "type": "string",
                "description": "Time in HH:MM format (24-hour).",
            },
            "patient_name": {
                "type": "string",
                "description": "Patient's full name (if known).",
            },
            "patient_phone": {
                "type": "string",
                "description": "Patient's phone number (if known).",
            },
        },
        "required": ["doctor_id", "date", "time"],
    },
)

check_in = FunctionDeclaration(
    name="check_in",
    description=(
        "Check in a patient who has arrived for their scheduled appointment. "
        "Use this when a visitor says they have an existing appointment today."
    ),
    parameters={
        "type": "object",
        "properties": {
            "patient_identifier": {
                "type": "string",
                "description": (
                    "Patient identifier — can be a patient UUID or phone number. "
                    "The system will look up the patient and find today's appointment."
                ),
            },
        },
        "required": ["patient_identifier"],
    },
)

lookup_patient = FunctionDeclaration(
    name="lookup_patient",
    description=(
        "Look up an existing patient by their phone number. "
        "Use this to find a patient's record before booking or checking in."
    ),
    parameters={
        "type": "object",
        "properties": {
            "phone": {
                "type": "string",
                "description": "Patient phone number in +998XXXXXXXXX format.",
            },
        },
        "required": ["phone"],
    },
)

register_patient = FunctionDeclaration(
    name="register_patient",
    description=(
        "Register a new patient in the system. Use this when the visitor is not "
        "found in the database and needs to be registered before booking."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Full name of the patient.",
            },
            "phone": {
                "type": "string",
                "description": "Phone number in +998XXXXXXXXX format.",
            },
            "date_of_birth": {
                "type": "string",
                "description": "Date of birth in YYYY-MM-DD format.",
            },
            "language": {
                "type": "string",
                "description": "Preferred language: 'uz', 'ru', or 'en'.",
                "enum": ["uz", "ru", "en"],
            },
        },
        "required": ["name", "phone"],
    },
)

get_available_slots = FunctionDeclaration(
    name="get_available_slots",
    description=(
        "Get available appointment time slots for a specific doctor on a given date. "
        "Use this to show the visitor when the doctor is free."
    ),
    parameters={
        "type": "object",
        "properties": {
            "doctor_id": {
                "type": "string",
                "description": "UUID of the doctor.",
            },
            "date": {
                "type": "string",
                "description": "Date to check in YYYY-MM-DD format.",
            },
        },
        "required": ["doctor_id", "date"],
    },
)

get_department_info = FunctionDeclaration(
    name="get_department_info",
    description=(
        "Get information about a clinic department including its doctors and services. "
        "Use this when a visitor asks about a specific department or medical field."
    ),
    parameters={
        "type": "object",
        "properties": {
            "department_name": {
                "type": "string",
                "description": (
                    "Name or partial name of the department to search for "
                    "(e.g. 'Terapiya', 'Kardiologiya', 'Stomatologiya')."
                ),
            },
        },
        "required": ["department_name"],
    },
)

get_doctor_info = FunctionDeclaration(
    name="get_doctor_info",
    description=(
        "Get detailed information about a specific doctor including specialty, "
        "schedule, and available services. Use when a visitor asks about a doctor."
    ),
    parameters={
        "type": "object",
        "properties": {
            "doctor_name": {
                "type": "string",
                "description": "Full or partial name of the doctor to search for.",
            },
        },
        "required": ["doctor_name"],
    },
)

process_payment = FunctionDeclaration(
    name="process_payment",
    description=(
        "Initiate a payment for a patient. Use this when the visitor wants to pay "
        "for a service or appointment. Always confirm the amount before processing."
    ),
    parameters={
        "type": "object",
        "properties": {
            "patient_id": {
                "type": "string",
                "description": "UUID of the patient making the payment.",
            },
            "amount": {
                "type": "number",
                "description": "Payment amount in UZS (Uzbek so'm).",
            },
            "method": {
                "type": "string",
                "description": "Payment method.",
                "enum": ["uzcard", "humo", "click", "payme", "cash"],
            },
        },
        "required": ["patient_id", "amount", "method"],
    },
)

get_queue_status = FunctionDeclaration(
    name="get_queue_status",
    description=(
        "Get current queue status for a department — number of people waiting "
        "and estimated wait time. Use when visitor asks about wait times."
    ),
    parameters={
        "type": "object",
        "properties": {
            "department_id": {
                "type": "string",
                "description": "UUID of the department to check queue for.",
            },
        },
        "required": ["department_id"],
    },
)

issue_queue_ticket = FunctionDeclaration(
    name="issue_queue_ticket",
    description=(
        "Issue a queue ticket for a patient in a specific department. "
        "Use this after check-in or when a patient needs to wait for their turn."
    ),
    parameters={
        "type": "object",
        "properties": {
            "patient_id": {
                "type": "string",
                "description": "UUID of the patient.",
            },
            "department_id": {
                "type": "string",
                "description": "UUID of the department.",
            },
        },
        "required": ["patient_id", "department_id"],
    },
)

search_faq = FunctionDeclaration(
    name="search_faq",
    description=(
        "Search the clinic's FAQ database for answers to common questions. "
        "Use this when a visitor asks general questions about the clinic, "
        "services, working hours, parking, insurance, etc."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query in any language (uz/ru/en).",
            },
        },
        "required": ["query"],
    },
)

escalate_to_human = FunctionDeclaration(
    name="escalate_to_human",
    description=(
        "Escalate the conversation to a human staff member. Use this when "
        "the visitor's request cannot be handled automatically, when they "
        "explicitly ask for a human, or when there is a complaint."
    ),
    parameters={
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Brief description of why escalation is needed.",
            },
        },
        "required": ["reason"],
    },
)

navigate_screen = FunctionDeclaration(
    name="navigate_screen",
    description=(
        "Navigate the kiosk touchscreen to show a specific UI screen to the visitor. "
        "ALWAYS call this after fetching data (e.g., after get_department_info, call navigate_screen('departments')). "
        "When you call navigate_screen, keep your text response very short (1 sentence) — the screen will show the details. "
        "Available screens: departments, doctors, timeslots, booking_confirm, checkin, payment, queue_ticket, info, faq, farewell."
    ),
    parameters={
        "type": "object",
        "properties": {
            "screen": {
                "type": "string",
                "description": "Target screen to navigate to.",
                "enum": [
                    "departments",
                    "doctors",
                    "timeslots",
                    "booking_confirm",
                    "checkin",
                    "payment",
                    "queue_ticket",
                    "info",
                    "faq",
                    "farewell",
                ],
            },
        },
        "required": ["screen"],
    },
)

FUNCTION_DECLARATIONS = [
    book_appointment,
    check_in,
    lookup_patient,
    register_patient,
    get_available_slots,
    get_department_info,
    get_doctor_info,
    process_payment,
    get_queue_status,
    issue_queue_ticket,
    search_faq,
    escalate_to_human,
    navigate_screen,
]

CLINIC_TOOLS = Tool(function_declarations=FUNCTION_DECLARATIONS)
