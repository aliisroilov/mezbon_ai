import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, time, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.database import Base
from app.core.security import create_access_token, hash_password
from app.models.clinic import Clinic
from app.models.department import Department
from app.models.doctor import Doctor, DoctorSchedule
from app.models.patient import Patient
from app.models.service import Service
from app.models.user import User, UserRole

# ---------------------------------------------------------------------------
# Test database engine — NullPool avoids stale connections between tests
# Each test runs inside a savepoint that is rolled back after.
# ---------------------------------------------------------------------------
test_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(autouse=True)
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session that rolls back after each test."""
    async with test_engine.connect() as conn:
        txn = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        yield session

        await session.close()
        await txn.rollback()


@pytest_asyncio.fixture
async def seed_clinic(db_session: AsyncSession) -> dict:
    """Seed a minimal clinic + admin user. Returns dict with IDs."""
    clinic_id = uuid.uuid4()
    clinic = Clinic(
        id=clinic_id,
        name="Test Clinic",
        address="Test Address",
        phone="+998901234567",
        email="test@clinic.uz",
    )
    db_session.add(clinic)
    await db_session.flush()

    admin_id = uuid.uuid4()
    admin = User(
        id=admin_id,
        clinic_id=clinic_id,
        email="admin@test.uz",
        password_hash=hash_password("testpass123"),
        full_name="Test Admin",
        role=UserRole.CLINIC_ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    return {
        "clinic_id": clinic_id,
        "admin_id": admin_id,
        "admin_email": "admin@test.uz",
        "admin_password": "testpass123",
    }


@pytest_asyncio.fixture
async def another_clinic(db_session: AsyncSession) -> dict:
    """Seed a second clinic + admin for tenant isolation tests."""
    clinic_id = uuid.uuid4()
    clinic = Clinic(
        id=clinic_id,
        name="Other Clinic",
        address="Other Address",
        phone="+998909999999",
        email="other@clinic.uz",
    )
    db_session.add(clinic)
    await db_session.flush()

    admin_id = uuid.uuid4()
    admin = User(
        id=admin_id,
        clinic_id=clinic_id,
        email="admin@other.uz",
        password_hash=hash_password("otherpass123"),
        full_name="Other Admin",
        role=UserRole.CLINIC_ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    return {
        "clinic_id": clinic_id,
        "admin_id": admin_id,
        "admin_email": "admin@other.uz",
        "admin_password": "otherpass123",
    }


@pytest_asyncio.fixture
async def auth_headers(seed_clinic: dict) -> dict[str, str]:
    """Return JWT auth headers for the seeded admin."""
    token_data = {
        "sub": str(seed_clinic["admin_id"]),
        "clinic_id": str(seed_clinic["clinic_id"]),
        "role": UserRole.CLINIC_ADMIN.value,
    }
    access_token = create_access_token(token_data)
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def other_auth_headers(another_clinic: dict) -> dict[str, str]:
    """Return JWT auth headers for the second clinic admin."""
    token_data = {
        "sub": str(another_clinic["admin_id"]),
        "clinic_id": str(another_clinic["clinic_id"]),
        "role": UserRole.CLINIC_ADMIN.value,
    }
    access_token = create_access_token(token_data)
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client with dependency overrides for the test DB session."""
    from app.api.deps import get_db
    from app.main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper fixtures for seeding test data
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def seed_department(db_session: AsyncSession, seed_clinic: dict) -> Department:
    """Create a single test department."""
    dept = Department(
        clinic_id=seed_clinic["clinic_id"],
        name="Terapiya",
        description="General therapy",
        floor=1,
        room_number="101",
    )
    db_session.add(dept)
    await db_session.flush()
    return dept


@pytest_asyncio.fixture
async def seed_doctor(
    db_session: AsyncSession, seed_clinic: dict, seed_department: Department
) -> Doctor:
    """Create a single test doctor."""
    doctor = Doctor(
        clinic_id=seed_clinic["clinic_id"],
        department_id=seed_department.id,
        full_name="Dr. Karimov",
        specialty="Terapevt",
    )
    db_session.add(doctor)
    await db_session.flush()
    return doctor


@pytest_asyncio.fixture
async def seed_schedule(
    db_session: AsyncSession, seed_clinic: dict, seed_doctor: Doctor
) -> DoctorSchedule:
    """Create a Monday schedule 09:00-17:00 with break 13:00-14:00."""
    sched = DoctorSchedule(
        clinic_id=seed_clinic["clinic_id"],
        doctor_id=seed_doctor.id,
        day_of_week=0,  # Monday
        start_time=time(9, 0),
        end_time=time(17, 0),
        break_start=time(13, 0),
        break_end=time(14, 0),
    )
    db_session.add(sched)
    await db_session.flush()
    return sched


@pytest_asyncio.fixture
async def seed_service(
    db_session: AsyncSession, seed_clinic: dict, seed_department: Department
) -> Service:
    """Create a single test service."""
    svc = Service(
        clinic_id=seed_clinic["clinic_id"],
        department_id=seed_department.id,
        name="Konsultatsiya",
        description="Doctor consultation",
        duration_minutes=30,
        price_uzs=150000,
    )
    db_session.add(svc)
    await db_session.flush()
    return svc


@pytest_asyncio.fixture
async def seed_patient(db_session: AsyncSession, seed_clinic: dict) -> Patient:
    """Create a single test patient with encrypted fields."""
    from app.core.encryption import encrypt_field

    patient = Patient(
        clinic_id=seed_clinic["clinic_id"],
        full_name_enc=encrypt_field("Alisher Usmanov"),
        phone_enc=encrypt_field("+998901112233"),
        dob_enc=encrypt_field("1990-01-15"),
        language_preference="uz",
    )
    db_session.add(patient)
    await db_session.flush()
    return patient
