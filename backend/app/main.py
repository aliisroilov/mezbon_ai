from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from loguru import logger

from app.config import settings
from app.core.database import async_session_factory, engine
from app.core.exceptions import AppError
from app.core.logger import setup_logging
from app.core.middleware import RateLimitMiddleware, RequestIDMiddleware
from app.core.redis import get_redis
from app.sockets import sio, create_sio_app, setup_socket_events

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.departments import router as departments_router
from app.api.doctors import router as doctors_router
from app.api.services import router as services_router
from app.api.patients import router as patients_router
from app.api.appointments import router as appointments_router
from app.api.payments import router as payments_router
from app.api.queue import router as queue_router
from app.api.devices import router as devices_router
from app.api.faq import router as faq_router
from app.api.content import router as content_router
from app.api.analytics import router as analytics_router
from app.ai.api.vision import router as vision_router
from app.ai.api.speech import router as speech_router
from app.ai.api.chat import router as chat_router
from app.api.printer import router as printer_router

# ---------------------------------------------------------------------------
# Orchestrator singleton (lazy-initialised during lifespan)
# ---------------------------------------------------------------------------
_orchestrator = None


async def _init_orchestrator() -> None:
    """Create and initialize the Orchestrator with all AI services."""
    global _orchestrator
    if _orchestrator is not None:
        return

    from app.ai.face_service import face_service as face
    from app.ai.gemini_service import GeminiService
    from app.ai.muxlisa_service import MuxlisaService
    from app.ai.session_manager import SessionManager
    from app.ai.orchestrator import Orchestrator

    gemini = GeminiService()
    muxlisa = MuxlisaService()
    session_mgr = SessionManager()

    # Initialize Gemini with clinic context so chat() works
    try:
        clinic_data = await _load_clinic_data()
        await gemini.initialize(clinic_data)
        logger.info("GeminiService initialized successfully")
    except Exception as e:
        logger.warning(f"GeminiService initialization deferred: {e}")

    # Initialize InsightFace model for face detection
    try:
        await face.initialize()
        logger.info("FaceService initialized successfully")
    except Exception as e:
        logger.warning(f"FaceService initialization deferred: {e}")

    _orchestrator = Orchestrator(
        gemini=gemini,
        face=face,
        muxlisa=muxlisa,
        session_mgr=session_mgr,
        db_session_factory=async_session_factory,
    )
    logger.info("Orchestrator created with all AI services")


async def _load_clinic_data() -> dict:
    """Load clinic info from DB for Gemini system prompt. Falls back to demo defaults."""
    data: dict = {
        "clinic_name": "Nano Medical Clinic",
        "clinic_address": "Toshkent, Olmazor tumani, Talabalar ko'chasi, 52-uy",
        "clinic_phone": "+998 78 113 08 88",
        "working_hours": "Dush-Shanba 08:00-17:00, Yakshanba yopiq",
        "departments": [],
        "doctors_on_duty": [],
    }

    try:
        from sqlalchemy import text as sql_text

        async with async_session_factory() as db:
            # Load clinic basic info
            result = await db.execute(
                sql_text("SELECT id, name, address, phone FROM clinics LIMIT 1")
            )
            row = result.first()
            if row:
                data["clinic_name"] = row.name or data["clinic_name"]
                data["clinic_address"] = row.address or data["clinic_address"]
                data["clinic_phone"] = row.phone or data["clinic_phone"]

            # Load departments
            try:
                dept_result = await db.execute(
                    sql_text(
                        "SELECT id, name, description, floor, room_number "
                        "FROM departments WHERE is_active = true ORDER BY sort_order"
                    )
                )
                for dept_row in dept_result.fetchall():
                    data["departments"].append({
                        "id": str(dept_row.id),
                        "name": dept_row.name,
                        "description": dept_row.description or "",
                    })
            except Exception as e:
                logger.debug(f"Could not load departments: {e}")

            # Load active doctors
            try:
                doc_result = await db.execute(
                    sql_text(
                        "SELECT d.id, d.full_name, d.specialty, dep.name AS department_name "
                        "FROM doctors d "
                        "LEFT JOIN departments dep ON d.department_id = dep.id "
                        "WHERE d.is_active = true ORDER BY d.full_name"
                    )
                )
                for doc_row in doc_result.fetchall():
                    data["doctors_on_duty"].append({
                        "full_name": doc_row.full_name,
                        "specialty": doc_row.specialty or "",
                        "department": doc_row.department_name or "",
                    })
            except Exception as e:
                logger.debug(f"Could not load doctors: {e}")

    except Exception as e:
        logger.debug(f"Could not load clinic data from DB: {e}")

    # Fall back to demo data if DB had nothing
    if not data["departments"]:
        data["departments"] = [
            {"name": "Endokrinologiya", "description": "Endokrin tizim kasalliklari"},
            {"name": "Xirurgiya", "description": "Jarrohlik xizmatlari"},
            {"name": "Nevrologiya", "description": "Asab tizimi kasalliklari"},
            {"name": "Kardiologiya", "description": "Yurak-qon tomir kasalliklari"},
            {"name": "Mammologiya", "description": "Ko'krak bezi kasalliklari"},
            {"name": "Terapiya", "description": "Umumiy terapevtik xizmatlar"},
            {"name": "Radiologiya", "description": "Radiologik tekshiruvlar"},
            {"name": "Reanimatsiya", "description": "Shoshilinch tibbiy yordam"},
        ]
    if not data["doctors_on_duty"]:
        data["doctors_on_duty"] = [
            {"full_name": "Nasirxodjaev Yo.B.", "specialty": "Endokrinolog-radiolog", "department": "Endokrinologiya"},
            {"full_name": "Aripova N.M.", "specialty": "Proktolog, yiringli jarroh", "department": "Xirurgiya"},
            {"full_name": "Malikov A.V.", "specialty": "Nevropatolog", "department": "Nevrologiya"},
            {"full_name": "Malikov A.V.", "specialty": "Kardiolog", "department": "Kardiologiya"},
            {"full_name": "Prof. Alimxodjaeva L.T.", "specialty": "Professor, Mammolog", "department": "Mammologiya"},
        ]

    logger.info(
        "Clinic data loaded for Gemini",
        extra={
            "clinic": data["clinic_name"],
            "departments": len(data["departments"]),
            "doctors": len(data["doctors_on_duty"]),
        },
    )
    return data


def _get_orchestrator():
    """Return the Orchestrator singleton — must be initialized at startup."""
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized — app lifespan not started")
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()

    # Verify DB connection
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        logger.warning(f"Database not available at startup: {e}")

    # Verify Redis connection
    try:
        redis = get_redis()
        await redis.ping()
        await redis.aclose()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.warning(f"Redis not available at startup: {e}")

    # Initialize Orchestrator (creates + initializes Gemini, Face, Muxlisa, Session)
    await _init_orchestrator()

    # Attach Socket.IO instance to app state
    app.state.sio = sio

    # Register Socket.IO event handlers (kiosk events, admin events)
    setup_socket_events(
        get_orchestrator=_get_orchestrator,
        get_db_factory=lambda: async_session_factory,
    )
    logger.info("Socket.IO server initialized with event handlers")

    yield

    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Mezbon AI Clinic API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    redirect_slashes=False,
)

# --- Middleware (order matters: first added = outermost) ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIDMiddleware)

if not settings.is_development:
    app.add_middleware(RateLimitMiddleware)

# --- Exception handlers ---


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {"code": exc.error_code, "message": exc.message},
        },
    )


# --- Routers ---

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(departments_router, prefix="/api/v1")
app.include_router(doctors_router, prefix="/api/v1")
app.include_router(services_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(queue_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(faq_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(vision_router, prefix="/api/v1")
app.include_router(speech_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(printer_router, prefix="/api/v1")


# --- Root redirect ---


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/api/docs")


# --- ASGI application ---
# Socket.IO wraps FastAPI — serves WebSocket on /ws/socket.io
# Use `uvicorn app.main:application` to run with WebSocket support
application = create_sio_app(app)
