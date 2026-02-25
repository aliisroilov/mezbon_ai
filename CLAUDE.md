# Mezbon AI — Clinic Reception System

## YOU ARE BUILDIN


An **Autonomous Digital Receptionist** for medical clinics in Uzbekistan. This is NOT a chatbot — it is a **digital employee** that replaces a human receptionist. It detects visitors via camera, speaks Uzbek/Russian/English, books appointments, processes payments, routes patients, and manages queues — all autonomously.

**This is a production system. Every line of code must be deployable, testable, and demo-ready.**

---

## ARCHITECTURE (Unified Python Backend)

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND LAYER                                          │
│                                                          │
│  ┌─────────────────┐    ┌──────────────────────┐        │
│  │  Kiosk UI        │    │  Admin Dashboard      │        │
│  │  React+TS+Vite   │    │  React+TS+Vite        │        │
│  │  Port 5173       │    │  Port 5174             │        │
│  └────────┬─────────┘    └──────────┬────────────┘        │
│           │ WebSocket + REST         │ REST                │
└───────────┼──────────────────────────┼───────────────────┘
            │                          │
┌───────────▼──────────────────────────▼───────────────────┐
│  BACKEND (Single Unified Python Service)                  │
│  Python 3.11 + FastAPI + SQLAlchemy + Socket.IO           │
│  Port 8000                                                │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  API Layer (FastAPI Routers)                       │    │
│  │  /api/v1/auth, /departments, /doctors, /patients  │    │
│  │  /appointments, /queue, /payments, /devices, /faq │    │
│  │  /admin/analytics, /admin/settings                │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  AI Services                                       │    │
│  │  ├── gemini_service.py  (Gemini 2.0 Flash)       │    │
│  │  ├── muxlisa_service.py (Uzbek/Russian STT+TTS)  │    │
│  │  ├── face_service.py    (InsightFace detection)   │    │
│  │  └── session_manager.py (visitor state machine)   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Integrations                                      │    │
│  │  ├── payment/ (Uzcard, Humo, Click, Payme)        │    │
│  │  ├── crm/     (Bitrix24, AmoCRM)                  │    │
│  │  └── storage/ (MinIO S3)                          │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Data Layer                                        │    │
│  │  SQLAlchemy ORM + Alembic migrations              │    │
│  │  PostgreSQL 16 | Redis 7                          │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Real-Time Layer                                   │    │
│  │  python-socketio (async)                          │    │
│  │  Kiosk events + Admin dashboard live updates      │    │
│  └──────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────┘
            │                    │
    ┌───────▼────────┐   ┌──────▼───────┐
    │  PostgreSQL 16  │   │   Redis 7    │
    │  Port 5432      │   │   Port 6379  │
    └─────────────────┘   └──────────────┘
```

**Why unified Python:**
- One language for ALL backend logic (API + AI + integrations)
- No cross-service HTTP calls — Gemini/InsightFace called directly in-process
- Simpler deployment (1 container instead of 2)
- SQLAlchemy + Alembic is battle-tested for production PostgreSQL
- FastAPI is as fast as Node.js for I/O-bound work
- Easier to debug, maintain, and extend

---

## TECH STACK (LOCKED — Do NOT Substitute)

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Backend** | Python 3.11 + FastAPI + Uvicorn | Single unified service |
| **ORM** | SQLAlchemy 2.0 (async) + Alembic | Async queries, type-safe |
| **Database** | PostgreSQL 16 | Multi-tenant, `clinic_id` everywhere |
| **Cache** | Redis 7 (via `redis.asyncio`) | Sessions, rate limits, caching |
| **LLM** | **Google Gemini 2.0 Flash** | `google-generativeai` Python SDK |
| **STT/TTS** | Muxlisa AI | `httpx` async client |
| **Face AI** | InsightFace + ONNX Runtime | `insightface` package, buffalo_l model |
| **Real-time** | `python-socketio` (async) | WebSocket for kiosk + admin |
| **Validation** | Pydantic v2 | Request/response models |
| **Auth** | `python-jose` (JWT) + `passlib` (bcrypt) | Access + refresh tokens |
| **Encryption** | `cryptography` (Fernet / AES-256-GCM) | PII field encryption |
| **HTTP Client** | `httpx` (async) | External API calls |
| **Logging** | `loguru` | Structured JSON logging |
| **Testing** | `pytest` + `pytest-asyncio` + `httpx` | Async test client |
| **Kiosk UI** | React 18 + TypeScript + Vite | Zustand, Socket.IO client, Tailwind |
| **Admin UI** | React 18 + TypeScript + Vite | TanStack Query, Recharts, Tailwind |
| **Containers** | Docker + Docker Compose | All services containerized |
| **Storage** | MinIO (S3-compatible) | `aioboto3` for async access |
| **Task Queue** | `arq` (Redis-based) | Background jobs (CRM sync, cleanup) |

### Gemini Rules
- Model: `gemini-2.0-flash` for ALL LLM calls
- `import google.generativeai as genai`
- Function calling for all clinic actions (book, check-in, pay, etc.)
- Structured output (JSON mode) for intent classification
- Streaming for long kiosk responses
- **Never use OpenAI. Never use ChatGPT. Gemini only.**

---

## PROJECT STRUCTURE

```
mezbon-clinic/
├── backend/                          # Unified Python backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app + lifespan + Socket.IO mount
│   │   ├── config.py                 # Pydantic Settings (all env vars)
│   │   │
│   │   ├── api/                      # FastAPI routers
│   │   │   ├── __init__.py           # Router registry
│   │   │   ├── deps.py              # Dependency injection (get_db, get_current_user, get_clinic_id)
│   │   │   ├── auth.py              # POST /login, /refresh, /logout
│   │   │   ├── departments.py       # CRUD + doctors listing
│   │   │   ├── doctors.py           # CRUD + schedule + available slots
│   │   │   ├── services.py          # Medical services CRUD
│   │   │   ├── patients.py          # CRUD + lookup + registration (PII encrypted)
│   │   │   ├── appointments.py      # Book, check-in, cancel, status
│   │   │   ├── queue.py             # Issue ticket, call next, status
│   │   │   ├── payments.py          # Initiate, webhook, status, refund
│   │   │   ├── devices.py           # Register, heartbeat, config
│   │   │   ├── faq.py               # CRUD per language
│   │   │   ├── content.py           # Announcements, media
│   │   │   ├── analytics.py         # Dashboard stats, reports
│   │   │   └── health.py            # Health check endpoint
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base model with id, created_at, updated_at, clinic_id
│   │   │   ├── clinic.py
│   │   │   ├── department.py
│   │   │   ├── doctor.py
│   │   │   ├── service.py
│   │   │   ├── patient.py
│   │   │   ├── appointment.py
│   │   │   ├── payment.py
│   │   │   ├── queue.py
│   │   │   ├── device.py
│   │   │   ├── faq.py
│   │   │   ├── content.py
│   │   │   ├── visit_log.py
│   │   │   ├── audit_log.py
│   │   │   ├── user.py
│   │   │   └── consent.py
│   │   │
│   │   ├── schemas/                  # Pydantic request/response models
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── department.py
│   │   │   ├── doctor.py
│   │   │   ├── patient.py
│   │   │   ├── appointment.py
│   │   │   ├── payment.py
│   │   │   ├── queue.py
│   │   │   ├── device.py
│   │   │   ├── faq.py
│   │   │   ├── ai.py               # Chat, intent, vision, speech schemas
│   │   │   └── common.py           # APIResponse, PaginationMeta, ErrorDetail
│   │   │
│   │   ├── services/                 # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py      # JWT creation, verification, password hashing
│   │   │   ├── department_service.py
│   │   │   ├── doctor_service.py    # Includes slot calculation logic
│   │   │   ├── patient_service.py   # PII encryption/decryption
│   │   │   ├── appointment_service.py # Booking with conflict detection
│   │   │   ├── queue_service.py     # Ticket generation, ordering
│   │   │   ├── payment_service.py   # Gateway orchestration
│   │   │   ├── device_service.py
│   │   │   ├── analytics_service.py # Aggregation queries
│   │   │   └── audit_service.py     # Audit log recording
│   │   │
│   │   ├── ai/                       # AI services (the "Brain")
│   │   │   ├── __init__.py
│   │   │   ├── gemini_service.py    # Gemini 2.0 Flash — chat, intent, function calling
│   │   │   ├── muxlisa_service.py   # STT + TTS via Muxlisa API
│   │   │   ├── face_service.py      # InsightFace detection + recognition
│   │   │   ├── session_manager.py   # Visitor state machine (Redis-backed)
│   │   │   ├── orchestrator.py      # Central coordinator — ties all AI together
│   │   │   ├── prompts/
│   │   │   │   ├── system_prompt.py # Clinic receptionist persona template
│   │   │   │   └── functions.py     # Gemini function declarations
│   │   │   └── api/                 # AI-specific FastAPI routes
│   │   │       ├── chat.py          # POST /ai/chat — main conversation endpoint
│   │   │       ├── vision.py        # POST /ai/detect, /ai/identify, /ai/register-face
│   │   │       └── speech.py        # POST /ai/stt, /ai/tts
│   │   │
│   │   ├── integrations/             # External service integrations
│   │   │   ├── __init__.py
│   │   │   ├── payment/
│   │   │   │   ├── base.py          # Abstract gateway interface
│   │   │   │   ├── factory.py       # Gateway factory
│   │   │   │   ├── uzcard.py
│   │   │   │   ├── humo.py
│   │   │   │   ├── click.py
│   │   │   │   ├── payme.py
│   │   │   │   └── mock.py          # Auto-confirm for dev/demo
│   │   │   ├── crm/
│   │   │   │   ├── base.py
│   │   │   │   ├── factory.py
│   │   │   │   ├── bitrix24.py
│   │   │   │   └── amocrm.py
│   │   │   └── storage/
│   │   │       └── minio_client.py  # S3-compatible file storage
│   │   │
│   │   ├── core/                     # Shared utilities
│   │   │   ├── __init__.py
│   │   │   ├── database.py          # Async SQLAlchemy engine + session factory
│   │   │   ├── redis.py             # Async Redis connection pool
│   │   │   ├── security.py          # JWT encode/decode, password hash/verify
│   │   │   ├── encryption.py        # AES-256-GCM encrypt/decrypt for PII
│   │   │   ├── exceptions.py        # Custom exception classes
│   │   │   ├── middleware.py        # CORS, rate limiter, request ID, tenant isolation
│   │   │   ├── response.py         # Standard APIResponse helper
│   │   │   └── logger.py           # Loguru configuration
│   │   │
│   │   ├── sockets/                  # Socket.IO event handlers
│   │   │   ├── __init__.py
│   │   │   ├── server.py           # Socket.IO async server setup
│   │   │   ├── kiosk_events.py     # face_detected, speech_audio, touch_action
│   │   │   └── admin_events.py     # queue_update, device_status, payment_confirmed
│   │   │
│   │   └── tasks/                    # Background jobs (arq workers)
│   │       ├── __init__.py
│   │       ├── crm_sync.py         # Periodic CRM sync
│   │       ├── cleanup.py          # Session cleanup, expired token cleanup
│   │       └── analytics.py        # Daily stats aggregation
│   │
│   ├── alembic/                      # Database migrations
│   │   ├── env.py
│   │   ├── versions/
│   │   └── alembic.ini
│   │
│   ├── tests/                        # All backend tests
│   │   ├── conftest.py              # Fixtures: test DB, client, auth headers
│   │   ├── test_auth.py
│   │   ├── test_departments.py
│   │   ├── test_doctors.py
│   │   ├── test_patients.py
│   │   ├── test_appointments.py
│   │   ├── test_queue.py
│   │   ├── test_payments.py
│   │   ├── test_ai_gemini.py
│   │   ├── test_ai_face.py
│   │   ├── test_ai_orchestrator.py
│   │   ├── test_session_machine.py
│   │   └── test_e2e_visitor.py      # Full visitor journey tests
│   │
│   ├── scripts/
│   │   ├── seed.py                  # Seed demo clinic data
│   │   ├── create_admin.py          # Create admin user
│   │   └── test_gemini.py           # Quick Gemini connection test
│   │
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── .env.example
│
├── kiosk-ui/                         # React kiosk interface
│   ├── src/
│   │   ├── components/              # Reusable UI (buttons, cards, modals, numpad)
│   │   ├── screens/                 # Full screens (14 screens — see state machine)
│   │   ├── hooks/                   # useSocket, useCamera, useMicrophone, useSession
│   │   ├── services/               # API client, socket service, audio service
│   │   ├── store/                  # Zustand stores (session, ui, patient)
│   │   ├── i18n/                   # uz.json, ru.json, en.json
│   │   ├── types/                  # TypeScript interfaces
│   │   └── assets/                 # Images, sounds, animations
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.ts
│
├── admin-dashboard/                  # React admin panel
│   ├── src/
│   │   ├── pages/                   # 10 pages (Dashboard, Doctors, Queue, Analytics, etc.)
│   │   ├── components/             # Tables, charts, forms, layout
│   │   ├── api/                    # API client with interceptors
│   │   ├── store/                  # Auth store, UI store
│   │   └── types/
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.ts
│
├── docker-compose.yml                # Full stack orchestration
├── docker-compose.dev.yml            # Dev overrides (hot reload)
├── docker-compose.prod.yml           # Production config
├── nginx/
│   └── nginx.conf                   # Reverse proxy config
├── .env.example
├── .github/workflows/
│   ├── test.yml                     # CI: lint + test
│   └── deploy.yml                   # CD: build + deploy
├── scripts/
│   ├── deploy.sh
│   ├── backup-db.sh
│   └── restore-db.sh
├── CLAUDE.md                         # ← THIS FILE
└── README.md
```

---

## CLINIC DOMAIN MODEL (SQLAlchemy)

```
Clinic (tenant root)
├── Department
│   ├── name, floor, room_number, is_active, sort_order
│   └── Doctor (belongs to department)
│       ├── full_name, specialty, bio, photo_url, is_active
│       ├── DoctorSchedule (weekday, start_time, end_time, break_start, break_end)
│       ├── Service (name, description, duration_minutes, price_uzs)
│       └── DoctorService (many-to-many: doctor ↔ service)
│
├── Patient (PII encrypted at app level)
│   ├── full_name_enc, phone_enc, dob_enc, language_preference
│   ├── face_embedding_enc (nullable, consent required)
│   ├── ConsentRecord (consent_type, granted_at, device_id, revoked_at)
│   ├── Appointment (doctor, service, scheduled_at, status, payment_status)
│   ├── Payment (amount, method, transaction_id, status)
│   └── VisitLog (device, session_id, intent, language, sentiment, success)
│
├── QueueTicket
│   ├── patient, department, doctor, ticket_number
│   ├── status (WAITING / IN_PROGRESS / COMPLETED / NO_SHOW)
│   └── estimated_wait_minutes
│
├── Device (kiosk)
│   ├── serial_number, name, location, status, config (JSONB)
│   └── DeviceHeartbeat (timestamp, uptime, cpu, memory, errors)
│
├── FAQ (question, answer, language, department, sort_order)
├── Announcement (title, body, language, active_from, active_to)
├── AuditLog (user_id, action, entity_type, entity_id, old_value, new_value)
└── User (admin — email, password_hash, role: SUPER_ADMIN/CLINIC_ADMIN/STAFF)
```

### Base Model Pattern (every model inherits this)
```python
class BaseModel:
    id: UUID (primary key, auto-generated)
    clinic_id: UUID (FK to Clinic, indexed, REQUIRED on every table except Clinic)
    created_at: datetime (auto)
    updated_at: datetime (auto on update)
```

### Tenant Isolation Pattern
```python
# EVERY query must be scoped:
async def get_departments(db: AsyncSession, clinic_id: UUID):
    result = await db.execute(
        select(Department).where(Department.clinic_id == clinic_id)
    )
    return result.scalars().all()
```

---

## VISITOR STATE MACHINE

```
IDLE
  │ (camera detects face)
  ▼
DETECTED → GREETING
  │
  ├── Known Patient → "Salom, [Name]! Bugun qanday yordam beraman?"
  └── New Visitor   → "Xush kelibsiz! Men Mezbon — raqamli resepshn."
  │
  ▼
INTENT_DISCOVERY (Gemini classifies from speech/touch)
  │
  ├─→ APPOINTMENT_BOOKING
  │     → SELECT_DEPARTMENT → SELECT_DOCTOR → SELECT_TIMESLOT
  │     → CONFIRM_BOOKING → PAYMENT (optional) → BOOKING_COMPLETE
  │
  ├─→ CHECK_IN
  │     → VERIFY_IDENTITY → CONFIRM_APPOINTMENT
  │     → ISSUE_QUEUE_TICKET → ROUTE_TO_DEPARTMENT
  │
  ├─→ INFORMATION_INQUIRY
  │     → FAQ_RESPONSE / DEPARTMENT_INFO / DOCTOR_PROFILE
  │
  ├─→ PAYMENT → SELECT_METHOD → PROCESS → RECEIPT
  │
  ├─→ COMPLAINT → RECORD_FEEDBACK → ESCALATE_TO_HUMAN (if needed)
  │
  └─→ HAND_OFF → NOTIFY_STAFF → WAIT_MESSAGE
  │
  ▼
FAREWELL → IDLE (clear session + PII from memory)
```

Session stored in Redis with 10-min TTL. Auto-reset on timeout.

---

## GEMINI PROMPT ENGINEERING

### System Instruction (injected per session)
```
You are "Mezbon", the digital receptionist at {clinic_name}.
Warm, professional, efficient — like the best 5-star clinic front desk.

CONTEXT:
- Clinic: {clinic_name} at {clinic_address}
- Today: {date}, {day_of_week}, {current_time}
- Kiosk location: {device_location}

DEPARTMENTS TODAY:
{departments_json}

DOCTORS ON DUTY:
{doctors_on_duty_json}

QUEUE STATUS:
{queue_status_json}

{patient_context_if_recognized}

RULES:
1. NEVER diagnose or give medical advice
2. NEVER share one patient's data with another
3. Payment amounts EXACT — never estimate
4. Offer human staff if you cannot help
5. Confirm bookings/payments before executing
6. Speak visitor's language (auto-detected). Default: Uzbek
7. Max 2-3 sentences per response (this is a kiosk)
8. Use visitor's name if known

USE FUNCTION CALLING for all actions — never fake data.
```

### Gemini Function Declarations
```python
CLINIC_FUNCTIONS = [
    book_appointment(doctor_id, service_id, date, time),
    check_in(patient_id, appointment_id),
    lookup_patient(phone),
    register_patient(name, phone, dob, language),
    get_available_slots(doctor_id, date),
    get_department_info(department_name),
    get_doctor_info(doctor_name),
    process_payment(patient_id, amount, method),
    get_queue_status(department_id),
    issue_queue_ticket(patient_id, department_id),
    search_faq(query),
    escalate_to_human(reason),
]
```

Function call flow: Gemini returns `function_call` → backend executes → result fed back → Gemini generates final response.

---

## MULTI-LANGUAGE

```
Visitor speaks → Muxlisa STT → transcript + detected_language
  → sent to Gemini (responds in same language)
  → Gemini response → Muxlisa TTS (same language) → audio on kiosk

Supported: uz (Uzbek), ru (Russian), en (English)
Default: uz | Fallback: uz
```

UI strings: `react-i18next` with `uz.json`, `ru.json`, `en.json`

---

## API STANDARDS

- Base: `/api/v1/`
- AI routes: `/api/v1/ai/`
- Tenant: `clinic_id` from JWT (never from request body)
- Standard envelope:
```json
{"success": true, "data": {}, "error": null, "meta": {"page": 1, "limit": 20, "total": 150}}
```
- Error envelope:
```json
{"success": false, "data": null, "error": {"code": "SLOT_UNAVAILABLE", "message": "..."}}
```
- Pagination: `?page=1&limit=20&sort=created_at&order=desc`
- Docs: auto-generated at `/api/docs` (Swagger) and `/api/redoc`

---

## SECURITY (Non-Negotiable)

1. PII encrypted with AES-256-GCM at app level before DB write
2. Face embeddings stored ONLY after on-screen consent (logged with timestamp + device)
3. Transient face detection by default — no persist without consent
4. Every DB query includes `clinic_id` filter — NO exceptions
5. Rate limiting: 100 req/min per IP (Redis-backed)
6. All inputs validated via Pydantic (FastAPI handles this)
7. CORS: whitelist only, no `*` in production
8. JWT: access 15min, refresh 7d, httpOnly secure cookies
9. Every admin action + payment + data access → AuditLog
10. Secrets via `.env` only, never in code

---

## ENVIRONMENT VARIABLES

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/mezbon_clinic
DATABASE_URL_SYNC=postgresql://user:pass@postgres:5432/mezbon_clinic  # for Alembic

# Redis
REDIS_URL=redis://redis:6379/0

# Auth
JWT_SECRET=<openssl rand -hex 32>
JWT_REFRESH_SECRET=<openssl rand -hex 32>
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# Encryption
ENCRYPTION_KEY=<openssl rand -hex 32>

# AI
GEMINI_API_KEY=<your-google-ai-key>
GEMINI_MODEL=gemini-2.0-flash
MUXLISA_API_URL=https://api.muxlisa.uz
MUXLISA_API_KEY=<your-key>
MUXLISA_MOCK=true  # true for dev without real Muxlisa

# Face AI
INSIGHTFACE_MODEL=buffalo_l
INSIGHTFACE_DEVICE=cpu  # or cuda

# Payments
UZCARD_MERCHANT_ID=...
HUMO_MERCHANT_ID=...
CLICK_SERVICE_ID=...
PAYME_MERCHANT_ID=...
PAYMENT_MOCK=true  # true for dev

# CRM
BITRIX24_WEBHOOK_URL=...
AMOCRM_API_KEY=...

# Storage
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=mezbon-clinic

# App
APP_ENV=development  # development | staging | production
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:5174
LOG_LEVEL=DEBUG  # DEBUG | INFO | WARNING | ERROR
```

---

## CODING RULES

1. **Async everywhere** — all DB queries, HTTP calls, Redis ops must be async
2. **Type hints on everything** — function params, returns, variables when not obvious
3. **Pydantic for all I/O** — request bodies, response models, config
4. **No raw SQL** — SQLAlchemy ORM only. Always filter by `clinic_id`
5. **No `print()`** — use `loguru` logger
6. **No `except: pass`** — always log errors with context

7. **Services layer** — routers call services, services call ORM. Never put DB logic in routers
8. **Dependency injection** — use FastAPI `Depends()` for db, auth, clinic context
9. **Commits**: conventional (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`)
10. **Tests**: pytest + pytest-asyncio. Async test client. Min 80% coverage on services


---

## 🎨 UI/UX DESIGN SYSTEM — "NANO MEDICAL PREMIUM EXPERIENCE"

### Design Philosophy

This kiosk is the **first thing a patient sees** when entering Nano Medical Clinic. It must feel like walking into a 5-star hospital lobby — not a government office terminal. Every pixel, animation, and interaction must communicate: **"You are in good hands."**

Think: Samsung hospital kiosk meets Emirates check-in terminal. Calm confidence, not flashy tech.

### Current Client: Nano Medical Clinic
- Logo: `nano-medical-logo.png` — deep indigo-navy wordmark
- Brand color: Deep indigo-navy (`#1E2A6E` family, extracted from logo)
- Logo appears: IdleScreen (large, 280px, centered), HeaderBar on all other screens (48px, top-left)

### Visual Identity

**Color Palette (Nano Medical Brand):**
```
Primary:          #1E2A6E (Deep indigo-navy)    — Logo color, trust, authority
Primary Dark:     #141D52                        — Hover states, pressed
Primary Light:    #2D3A8C                        — Lighter interactive elements
Primary 50:       #EEF0F7                        — Very light backgrounds
Primary 100:      #D0D4E8                        — Light borders, subtle fills
Primary 200:      #A8AECF                        — Soft emphasis
Primary 500:      #1E2A6E                        — Standard primary
Primary 800:      #0F1642                        — Deep emphasis

Accent:           #3B82F6 (Bright blue)          — CTAs, links, secondary actions
Accent Light:     #DBEAFE                        — Blue highlight backgrounds
Accent 50:        #EFF6FF                        — Lightest blue

Surface:          #F8FAFC (Slate 50)             — Main background
Surface Card:     #FFFFFF                        — Card backgrounds

Text Primary:     #0F172A (Slate 900)            — Headings
Text Body:        #334155 (Slate 700)            — Body text
Text Muted:       #94A3B8 (Slate 400)            — Secondary, placeholders
Text Inverse:     #FFFFFF                        — On dark/primary backgrounds

Success:          #10B981 (Emerald 500)          — Confirmations, check-in
Warning:          #F59E0B (Amber 500)            — Attention, alerts
Danger:           #EF4444 (Red 500)              — Errors, cancel
Info:             #3B82F6 (Blue 500)             — Informational

Border:           #E2E8F0 (Slate 200)            — Subtle borders
Border Active:    #1E2A6E                        — Selected/focused borders

Shadow Color:     rgba(30, 42, 110, 0.08)        — Indigo-tinted card shadows
Glow Color:       rgba(30, 42, 110, 0.15)        — Avatar/logo glow

Background gradient (full screen):
  linear-gradient(135deg, #EEF0F7 0%, #F8FAFC 30%, #E8ECF5 60%, #F0F2FA 100%)
  — Subtle indigo warmth, NOT flat white. Slowly rotating (20s cycle).

⚠️ NEVER USE TEAL/EMERALD AS PRIMARY. Teal (#0D9488) was the old generic color.
   All teal references must be replaced with indigo-navy (#1E2A6E) family.
```

**Typography:**
```
Font Family:  "Plus Jakarta Sans" (Google Fonts) — modern, warm, medical-appropriate
              Fallback: "Inter", system-ui, sans-serif

Sizes (kiosk-optimized — viewers stand 60-100cm from 32" screen):
  Display:    56px / 700 weight  — Ticket numbers, main greetings
  H1:         40px / 700 weight  — Screen titles
  H2:         28px / 600 weight  — Section headers
  H3:         22px / 600 weight  — Card titles
  Body:       18px / 400 weight  — Regular text
  Body Large: 20px / 400 weight  — Important info
  Caption:    14px / 500 weight  — Labels, timestamps
  Button:     18px / 600 weight  — Button text

Line height: 1.5 for body, 1.2 for headings
Letter spacing: -0.02em for headings, normal for body
```

**Spacing & Layout (1080×1920 Portrait Kiosk):**
```
Target device: 32" vertical touchscreen, 1080×1920 resolution

Screen layout template:
  ┌──────────────────────────┐ ← 0px
  │  Header Bar (80px)        │  Logo left, title center, lang right
  │  ─────────────────────── │
  │  AI Section (300-400px)   │  Avatar + message + voice indicator
  │  ─────────────────────── │
  │  Content Area (flex-1)    │  Cards, lists, forms (scrollable)
  │  ─────────────────────── │
  │  Bottom Nav (100px)       │  Back + Home buttons
  └──────────────────────────┘ ← 1920px

Border radius:
  Cards:      20px  — Soft, approachable
  Buttons:    16px  — Rounded but not pill
  Modals:     24px  — Premium feel
  Inputs:     12px
  Full round: 9999px — Avatars, status dots

Shadows (indigo-tinted):
  Card:       0 4px 24px rgba(30, 42, 110, 0.06), 0 1px 3px rgba(30, 42, 110, 0.04)
  Card Hover: 0 8px 32px rgba(30, 42, 110, 0.12), 0 2px 4px rgba(30, 42, 110, 0.06)
  Modal:      0 24px 48px rgba(30, 42, 110, 0.18)
  Button:     0 2px 12px rgba(30, 42, 110, 0.25)
  Glow:       0 0 40px rgba(30, 42, 110, 0.15)

Padding:
  Screen:     32px outer padding (not 48 — maximize 1080px width)
  Cards:      24px inner padding
  Buttons:    16px 32px (min height 56px, min width 160px)
  Between cards: 16px gap
  Section gap: 32px
```

### Touch Interaction Design

```
Minimum touch target: 56px × 56px (Apple HIG for kiosk)
Recommended: 64px height for primary actions
Large actions: 72px height (confirm, cancel, payment)

Touch feedback:
  - scale(0.97) on press (spring animation, 150ms)
  - scale(1.02) on release then scale(1) (bounce effect)
  - Background opacity shift on press
  - NEVER just color change — must have motion

Button hierarchy:
  Primary:   Filled indigo (#1E2A6E bg), white text, indigo shadow → Book, Confirm, Check-in
  Secondary: White fill, indigo border, indigo text → Back, Other options
  Accent:    Filled blue (#3B82F6 bg), white text → Secondary CTAs
  Ghost:     No border, indigo text → Cancel, Skip
  Danger:    Red fill, white text → only for destructive actions
  
  All buttons: rounded-2xl, font-semibold, min-h-[56px], transition-all duration-200
```

### Animation & Motion

```
Framework: Framer Motion

Principles:
  1. PURPOSEFUL — every animation must communicate something
  2. SMOOTH — 60fps, no jank, spring physics
  3. SUBTLE — premium = restraint. No bouncing logos or spinning icons
  4. FAST — max 400ms for transitions, 200ms for micro-interactions

Screen Transitions:
  Enter:  fadeIn + slideUp (from y:30 to y:0), duration: 400ms, ease: [0.25, 0.46, 0.45, 0.94]
  Exit:   fadeOut + slideDown (to y:-20), duration: 300ms
  Use AnimatePresence with mode="wait" for clean transitions

Micro-interactions:
  Card hover/tap:  scale(0.97) → scale(1.02) → scale(1), spring physics
  Button press:    scale(0.96), 150ms
  Success:         checkmark draws in (SVG path animation), 600ms
  Loading:         3 dots pulse sequentially, not spinning circle
  Error:           gentle shake (x: [-4, 4, -4, 4, 0]), 400ms

Ambient animations (IdleScreen):
  Breathing glow:  box-shadow pulses with indigo tint (2s cycle, ease-in-out, infinite)
  Gradient shift:  background gradient slowly rotates (20s cycle)
  Floating orbs:   2-3 blurred circles (indigo rgba(30,42,110,0.1-0.15)), slow drift

AI Avatar animations (PROFESSIONAL ABSTRACT ORB — no cartoon face):
  The avatar is a deep indigo gradient orb. NO eyes, NO smile, NO face features.
  It communicates state through light, motion, and surrounding effects only.

  Idle:       Slow breathing scale (1.0 → 1.04 → 1.0), 3s cycle, soft indigo glow
  Listening:  Concentric ripple rings expand outward (indigo), orb slightly enlarged
  Speaking:   Thin elegant waveform lines around the orb, subtle pulse
  Thinking:   Gentle pulse + 3 dots below (sequentially fade, 800ms)
  Success:    Green gradient + checkmark SVG draws in
  
Voice indicator:
  Prominent pill-shaped container: bg-primary-50, rounded-full, px-8 py-4
  Active listening:  Mic icon pulsing + concentric ring ripple + "Gapiring..." text
  Inactive:          Muted mic icon + "Tinglash uchun bosing" text
  Speaking:          Speaker icon + "Javob berilmoqda..." text
  Min height: 56px, tappable to toggle mic
```

### Component Design Specs

**Header Bar (NEW — appears on all screens except IdleScreen):**
```
Height: 80px
Background: white, subtle bottom border (border-b border-slate-200)
Left:   Nano Medical logo (48px height)
Center: Screen title (H2 size, text-primary)
Right:  Language selector (pill buttons: UZ | RU, 44px height each)
Sticky at top of every screen.
```

**Bottom Navigation (NEW — appears on all screens except Idle/Farewell):**
```
Height: 100px
Background: white, subtle top border
Left:   "← Orqaga" button (secondary style, icon + text, 56px height)
Center: Optional progress indicator for multi-step flows
Right:  "🏠 Asosiy" home button (ghost style, icon + text)
Safe area for standing users looking down at bottom of 32" screen.
```

**Cards (Department, Doctor, Service, Intent):**
```
- White background (#FFFFFF)
- 20px border-radius
- Indigo-tinted shadow: 0 4px 24px rgba(30, 42, 110, 0.06)
- 24px inner padding
- Min height: 120px (departments), 160px (intents — taller, centered text)
- Left side: 48px circle (primary-50 bg) with icon/emoji in primary color
- Title: H3 (22px/600), one line
- Subtitle: Body (18px/400), muted color, max 2 lines
- On tap: scale(0.97) + shadow elevation + 3px left-border appears (primary color)
- Selected: primary-50 bg + 4px left-border (primary) + checkmark top-right
- Hover: translateY(-2px) + enhanced shadow
- Gap between cards: 16px
- Grid: 2 columns for departments/intents, full-width for doctors
```

**Doctor Cards:**
```
- Full width, horizontal layout
- Left: 56px circle with doctor initial letter (primary bg, white text, 24px font)
- Center: Name (H3) + Specialty (body, muted) + "X yil tajriba" pill badge
- Right: Schedule "08:00-16:00" (caption)
- Min height: 100px
```

**Time Slot Pills:**
```
- Rounded-full (pill shape)
- Padding: 12px 24px, min-height: 48px
- Default: white bg, slate-200 border, slate-700 text
- Available: white bg, primary-100 border, primary text
- Selected: primary bg (#1E2A6E), white text, button shadow
- Unavailable: slate-100 bg, slate-400 text, line-through
- Grid: 3 columns, 12px gap
```

**Queue Ticket Display:**
```
- Centered on screen
- Ticket number: 80px font, 800 weight, primary color
- Background: radial gradient (primary-50 center → transparent)
- Department + room: 28px, below ticket number
- Animated entrance: number "counts up" then lands (slot machine effect)
- Pulsing indigo glow behind the number
```

**Phone Number Input (NumPad):**
```
- Large display at top: 40px font, shows entered number
- +998 prefix: grayed out, non-editable
- Number buttons: 72px × 72px, rounded-2xl, 28px font
- Layout: 3×4 grid + backspace + clear
- Tap: scale(0.95) + subtle background flash
```

**Confirmation Summary Card:**
```
- Elevated card (modal-level shadow)
- 32px padding, 24px border-radius
- Top: Doctor name + specialty (primary color header area)
- Divider (slate-200)
- Detail rows: icon (in primary-50 circle) + label (muted) + value (body)
  📅 Sana | 🕐 Vaqt | 💊 Xizmat | 💰 Narx
- Divider
- "Tasdiqlash" primary button (72px height, full width)
- "Bekor qilish" ghost button below
```

### Screen-Specific Design Notes

**IdleScreen:**
```
- Full-screen animated gradient background (indigo-tinted)
- Clinic logo: centered, 280px white circle container, indigo breathing glow shadow
- Logo image: nano-medical-logo.png inside the circle, ~220px width
- Clinic name: H1, below logo, primary color
- "Raqamli qabulxona" tagline: Body-lg, muted
- Approach prompt: "Yaqinlashing yoki ekranni bosing" pulsing opacity (0.5→1→0.5), 3s
- 2-3 floating blurred orbs (indigo, rgba(30,42,110,0.1-0.15), slow drift)
- Bottom bar: Language selector (left) | Clock + Date (center) | "Nano Medical" (right)
- Camera running in background — no visible feed
- This screen must feel ALIVE but CALM — luxury hospital lobby display
```

**GreetingScreen + Intent Selection (combined or sequential):**
```
- [Header Bar] with logo + "Xush kelibsiz" + language
- AI Avatar (120px, professional indigo orb, no face) centered
- Greeting bubble: white card, max-width 85%, indigo-50 left accent
- Voice indicator: prominent pill below bubble
- "Sizga qanday yordam beraman?" — H2 centered
- Intent cards: 2-column grid, 160px tall each, vertically centered icons
  📅 Qabulga yozilish | ✅ Ro'yxatdan o'tish
  ℹ️ Ma'lumot olish   | 💳 To'lov qilish
       ❓ Ko'p so'raladigan savollar
- [Bottom Nav]
```

**DepartmentSelectScreen:**
```
- [Header: "Bo'limni tanlang"]
- AI bubble: "Qaysi bo'limga murojaat qilmoqchisiz?" + voice indicator
- 2-column card grid, 16px gap, 32px outer padding
- Each card: 120-140px height, icon circle left, dept name + floor/room + doctor count
- Cards use medical emoji: 🔬🔪🧠🫀🩺💊📡🚑
- Must fill the vertical space — cards should take 60%+ of screen height
- [Bottom Nav: ← Orqaga  🏠]
```

**PaymentScreen:**
```
- Amount: Display size (56px), centered, with "so'm" label
- Payment method cards: large (120px height), provider logo, name
- QR Code: 280px × 280px, white padding
  Below: "Telefoningiz bilan skanerlang" with phone icon
- Success: large green checkmark (SVG draw) + "To'lov qabul qilindi!"
- Subtle particle/confetti effect on success (2 seconds)
```

**FarewellScreen:**
```
- Large message: "Rahmat! Sog'liq tilaymiz!" in H1, centered
- Nano Medical logo below (120px)
- Satisfaction rating: 3 emoji buttons (😊 😐 😞), 72px each (optional)
- Progress bar: 10-second countdown to auto-reset
- Smooth fade-out transition to Idle
```

### Accessibility

```
- Color contrast: WCAG AA minimum (4.5:1 for body text, 3:1 for large text)
- Focus indicators: 3px indigo outline, 4px offset (keyboard/accessibility mode)
- Touch targets: minimum 56px (exceeds WCAG 44px requirement)
- Text scaling: all rem-based, responds to system font size
- Reduced motion: respect prefers-reduced-motion (disable ambient animations)
- Screen reader: all interactive elements have aria-labels (in current language)
```

### Icon System

```
Use: Lucide React icons (consistent, clean line style)
Size: 24px default, 32px for cards, 48px for feature icons
Stroke width: 2px (default)
Color: inherit from text color (primary on light bg, white on dark bg)
For departments: use relevant medical emoji in primary-50 circle backgrounds
Department emoji: 🔬 🔪 🧠 🫀 🩺 💊 📡 🚑
```

### DO NOT

1. ❌ No dark mode — medical kiosk in bright lobby, dark mode is wrong context
2. ❌ No skeleton loaders — use pulsing dots or shimmer (more premium)
3. ❌ No browser-default spinners — custom animated indicators only
4. ❌ No sharp corners — minimum 12px radius everywhere
5. ❌ No flat design — indigo-tinted shadows and depth are essential
6. ❌ No stock photos — use icons, illustrations, gradients instead
7. ❌ No red/green only — always pair with icons (accessibility)
8. ❌ No text walls — max 3 lines per message, break into steps
9. ❌ No generic "Loading..." — always context-specific ("Shifokorlar qidirilmoqda...")
10. ❌ No sudden layout shifts — all content areas have fixed dimensions
11. ❌ No teal/emerald as primary color — use indigo-navy (#1E2A6E) family ONLY
12. ❌ No cartoon face on AI avatar — professional abstract orb only
13. ❌ No visible browser chrome — must run in kiosk/fullscreen mode
14. ❌ No empty space — every screen must fill 1080×1920 portrait layout

## KEY COMMANDS

```bash
# Full stack dev
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Backend only
docker-compose up backend postgres redis

# Run backend locally (outside Docker)
cd backend && uvicorn app.main:app --reload --port 8000

# Run tests
cd backend && pytest -v --cov=app --cov-report=term-missing

# Create migration
cd backend && alembic revision --autogenerate -m "description"

# Run migrations
cd backend && alembic upgrade head

# Seed demo data
cd backend && python scripts/seed.py

# Kiosk UI dev
cd kiosk-ui && npm run dev

# Admin dashboard dev
cd admin-dashboard && npm run dev

# Lint
cd backend && ruff check . && mypy app/

# Format
cd backend && ruff format .
```

---

## WHAT NOT TO DO

1. ❌ Never use OpenAI / ChatGPT — **Gemini only**
2. ❌ Never use SQLite — **PostgreSQL only**
3. ❌ Never use Node.js for backend — **Python FastAPI only**
4. ❌ Never skip `clinic_id` in queries
5. ❌ Never store PII unencrypted
6. ❌ Never store face data without consent
7. ❌ Never hardcode secrets
8. ❌ Never use sync DB calls — **async only**
9. ❌ Never put business logic in routers (use services layer)
10. ❌ Never make AI diagnose patients
11. ❌ Never share patient data across tenants
12. ❌ Never commit `.env` files
13. ❌ Never use `requests` library — use `httpx` (async)
14. ❌ Never use `print()` — use `loguru`



 