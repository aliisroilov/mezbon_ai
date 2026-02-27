"""Gemini function declarations for clinic receptionist actions."""

from google.generativeai.types import FunctionDeclaration, Tool

book_appointment = FunctionDeclaration(
    name="book_appointment",
    description=(
        "Book an appointment. Call this ONLY after confirming ALL details with the patient: "
        "doctor, date, time, and patient name. You can pass doctor_id (UUID) or doctor name. "
        "After booking, tell the patient their confirmation code and appointment details."
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
        "Look up a patient by phone number. The system normalizes the number automatically — "
        "pass whatever format the patient gave you. Do NOT ask the patient to correct their phone format."
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
        "Register a new patient. Call this when lookup_patient returns not found. "
        "You need at minimum: name and phone. Date of birth and language are optional."
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
        "Get available appointment slots for a doctor on a date. Call this AFTER "
        "the patient has chosen a doctor AND a date. Tell the patient the available "
        "times and ask which one they prefer."
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
        "Get department info including its doctors. Call this FIRST when a patient "
        "wants to book an appointment or asks about a department. The result includes "
        "the department's doctors so you can offer them to the patient. "
        "After getting results, tell the patient about the available doctors."
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

# DISABLED: Payment not ready for pilot
# process_payment = FunctionDeclaration(
#     name="process_payment",
#     description=(
#         "Initiate a payment for a patient. Use this when the visitor wants to pay "
#         "for a service or appointment. Always confirm the amount before processing."
#     ),
#     parameters={
#         "type": "object",
#         "properties": {
#             "patient_id": {
#                 "type": "string",
#                 "description": "UUID of the patient making the payment.",
#             },
#             "amount": {
#                 "type": "number",
#                 "description": "Payment amount in UZS (Uzbek so'm).",
#             },
#             "method": {
#                 "type": "string",
#                 "description": "Payment method.",
#                 "enum": ["uzcard", "humo", "click", "payme", "cash"],
#             },
#         },
#         "required": ["patient_id", "amount", "method"],
#     },
# )

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
        "Issue a queue ticket after booking or check-in. Tell the patient their "
        "ticket number and estimated wait time."
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

FUNCTION_DECLARATIONS = [
    book_appointment,
    check_in,
    lookup_patient,
    register_patient,
    get_available_slots,
    get_department_info,
    get_doctor_info,
    # process_payment,  # DISABLED: Payment not ready for pilot
    get_queue_status,
    issue_queue_ticket,
    search_faq,
    escalate_to_human,
    # navigate_screen REMOVED — UI navigation auto-derived from data functions
]

CLINIC_TOOLS = Tool(function_declarations=FUNCTION_DECLARATIONS)
