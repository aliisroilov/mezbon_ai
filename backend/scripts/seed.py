#!/usr/bin/env python3
"""
Seed script for Mezbon AI — Nano Medical Clinic data.

Creates the Nano Medical Clinic with real departments, doctors,
schedules, services, patients, appointments, payments, queue
tickets, FAQs, announcements, devices, and an admin user.

Usage:
    cd backend && python scripts/seed.py

Idempotent: if the clinic already exists, all its data is deleted and re-seeded.
"""

import asyncio
import os
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

# Ensure backend/ is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, engine
from app.core.encryption import encrypt_field
from app.core.security import hash_password
from app.models.appointment import Appointment, AppointmentStatus, PaymentStatus
from app.models.clinic import Clinic
from app.models.content import Announcement
from app.models.department import Department
from app.models.device import Device, DeviceStatus
from app.models.doctor import Doctor, DoctorSchedule
from app.models.faq import FAQ
from app.models.patient import Patient
from app.models.payment import Payment, PaymentMethod, PaymentTransactionStatus
from app.models.queue import QueueStatus, QueueTicket
from app.models.service import Service, doctor_services
from app.models.user import User, UserRole

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NOW = datetime.now(timezone.utc)
TODAY = NOW.date()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
DAY_AFTER = TODAY + timedelta(days=2)

CLINIC_NAME = "Nano Medical Clinic"
CLINIC_EMAIL = "nanomediccalclinic@gmail.com"
ADMIN_EMAIL = "admin@nanomedical.uz"
ADMIN_PASSWORD = "NanoAdmin2026!"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def dt(d: date, h: int, m: int = 0) -> datetime:
    """Create a timezone-aware datetime."""
    return datetime.combine(d, time(h, m), tzinfo=timezone.utc)


def uid() -> uuid.UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Pre-generate all IDs so we can cross-reference
# ---------------------------------------------------------------------------
clinic_id = uid()

# Department IDs (8 departments)
dept_ids = {
    "endokrinologiya": uid(),
    "xirurgiya": uid(),
    "nevrologiya": uid(),
    "kardiologiya": uid(),
    "mammologiya": uid(),
    "terapiya": uid(),
    "radiologiya": uid(),
    "reanimatsiya": uid(),
}

# Doctor IDs (5 doctors, Malikov appears twice)
doctor_ids = {
    "nasirxodjaev": uid(),
    "aripova": uid(),
    "malikov_nevro": uid(),
    "malikov_kardio": uid(),
    "alimxodjaeva": uid(),
}

# Service IDs (8 services)
svc_ids = {name: uid() for name in [
    "konsultatsiya", "professor_konsultatsiya",
    "checkup_erkak", "checkup_ayol",
    "terapiya_palata", "xirurgiya_palata",
    "radiologiya_palata", "reanimatsiya_palata",
]}

# Patient IDs
patient_ids = [uid() for _ in range(5)]

# Device IDs
device_ids = [uid(), uid()]

# Appointment IDs
appt_ids = [uid() for _ in range(8)]

# Payment IDs
payment_ids = [uid() for _ in range(4)]

# Queue ticket IDs
ticket_ids = [uid() for _ in range(4)]

# Admin user ID
admin_id = uid()


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------
async def clear_existing(db: AsyncSession) -> bool:
    """Delete existing clinic if found. Returns True if cleared."""
    from sqlalchemy import text

    result = await db.execute(
        select(Clinic).where(Clinic.name == CLINIC_NAME)
    )
    existing = result.scalar_one_or_none()
    if existing:
        cid = existing.id
        print(f"  Found existing clinic '{CLINIC_NAME}' (id={cid}). Deleting...")
        await db.execute(text("DELETE FROM clinics WHERE id = :id"), {"id": cid})
        await db.flush()
        return True
    return False


async def seed_clinic(db: AsyncSession) -> Clinic:
    clinic = Clinic(
        id=clinic_id,
        name=CLINIC_NAME,
        address="Toshkent shahri, Olmazor tumani, Talabalar ko'chasi, 52-uy",
        phone="+998781130888",
        email=CLINIC_EMAIL,
        timezone="Asia/Tashkent",
        settings={
            "working_hours": {
                "mon_sat": "08:00-17:00",
                "sunday": "closed",
            },
            "phones": ["+998781130888", "+998555000550", "+998994678000"],
            "languages": ["uz", "ru"],
            "logo": "nano-medical-logo.png",
        },
    )
    db.add(clinic)
    await db.flush()
    return clinic


async def seed_admin(db: AsyncSession) -> User:
    user = User(
        id=admin_id,
        clinic_id=clinic_id,
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        full_name="Admin Nano Medical",
        role=UserRole.CLINIC_ADMIN,
    )
    db.add(user)
    await db.flush()
    return user


async def seed_departments(db: AsyncSession) -> dict[str, Department]:
    dept_data = [
        ("endokrinologiya", "Endokrinologiya", "Endokrin tizim kasalliklari", 1, "101-xona"),
        ("xirurgiya", "Xirurgiya", "Jarrohlik xizmatlari", 1, "102-xona"),
        ("nevrologiya", "Nevrologiya", "Asab tizimi kasalliklari", 2, "201-xona"),
        ("kardiologiya", "Kardiologiya", "Yurak-qon tomir kasalliklari", 2, "202-xona"),
        ("mammologiya", "Mammologiya", "Ko'krak bezi kasalliklari", 2, "203-xona"),
        ("terapiya", "Terapiya", "Umumiy terapevtik xizmatlar", 1, "103-xona"),
        ("radiologiya", "Radiologiya", "Radiologik tekshiruvlar", 1, "104-xona"),
        ("reanimatsiya", "Reanimatsiya", "Shoshilinch tibbiy yordam", 1, "105-xona"),
    ]
    depts = {}
    for i, (key, name, desc, floor, room) in enumerate(dept_data):
        dept = Department(
            id=dept_ids[key],
            clinic_id=clinic_id,
            name=name,
            description=desc,
            floor=floor,
            room_number=room,
            sort_order=i,
        )
        db.add(dept)
        depts[key] = dept
    await db.flush()
    return depts


async def seed_doctors(db: AsyncSession) -> dict[str, Doctor]:
    doctor_data = [
        ("nasirxodjaev", "endokrinologiya", "Nasirxodjaev Yo.B.", "Endokrinolog-radiolog", "28 yillik tajriba. Endokrin tizim kasalliklari mutaxassisi."),
        ("aripova", "xirurgiya", "Aripova N.M.", "Proktolog, yiringli jarroh", "35 yillik tajriba. Jarrohlik bo'yicha oliy toifali mutaxassis."),
        ("malikov_nevro", "nevrologiya", "Malikov A.V.", "Nevropatolog", "30 yillik tajriba. Asab tizimi kasalliklari mutaxassisi."),
        ("malikov_kardio", "kardiologiya", "Malikov A.V.", "Kardiolog", "35 yillik tajriba. Yurak-qon tomir kasalliklari mutaxassisi."),
        ("alimxodjaeva", "mammologiya", "Prof. Alimxodjaeva L.T.", "Professor, Mammolog", "30 yillik tajriba. Mammologiya bo'yicha professor."),
    ]
    doctors = {}
    for key, dept_key, name, specialty, bio in doctor_data:
        doc = Doctor(
            id=doctor_ids[key],
            clinic_id=clinic_id,
            department_id=dept_ids[dept_key],
            full_name=name,
            specialty=specialty,
            bio=bio,
        )
        db.add(doc)
        doctors[key] = doc
    await db.flush()
    return doctors


async def seed_schedules(db: AsyncSession) -> None:
    """Individual schedules per doctor — Mon-Sat (0-5)."""
    # Doctor-specific hours
    schedule_map = {
        "nasirxodjaev": (time(8, 0), time(16, 0), time(12, 0), time(13, 0)),
        "aripova": (time(9, 0), time(16, 0), time(12, 0), time(13, 0)),
        "malikov_nevro": (time(8, 0), time(16, 0), time(12, 0), time(13, 0)),
        "malikov_kardio": (time(8, 0), time(16, 0), time(12, 0), time(13, 0)),
        "alimxodjaeva": (time(10, 0), time(13, 0), None, None),  # Only 3 hours, no break
    }
    for doc_key, doc_id in doctor_ids.items():
        start, end, brk_start, brk_end = schedule_map[doc_key]
        for day in range(6):  # 0=Mon .. 5=Sat
            sched = DoctorSchedule(
                clinic_id=clinic_id,
                doctor_id=doc_id,
                day_of_week=day,
                start_time=start,
                end_time=end,
                break_start=brk_start,
                break_end=brk_end,
            )
            db.add(sched)
    await db.flush()


async def seed_services(db: AsyncSession) -> dict[str, Service]:
    svc_data = [
        # Consultation services
        ("konsultatsiya", "endokrinologiya", "Konsultatsiya", "Birlamchi ko'rik", 30, 260000),
        ("professor_konsultatsiya", "mammologiya", "Professor konsultatsiyasi", "Professor tomonidan birlamchi ko'rik", 40, 500000),
        # Checkup packages
        ("checkup_erkak", "terapiya", "Checkup — Erkaklar", "Erkaklar uchun to'liq tekshiruv", 120, 2000000),
        ("checkup_ayol", "terapiya", "Checkup — Ayollar", "Ayollar uchun to'liq tekshiruv", 120, 2000000),
        # Inpatient daily rates (duration=0 means daily rate)
        ("terapiya_palata", "terapiya", "Terapiya — Lyuks palata", "Lyuks palata, ovqatlanish bilan", 0, 1500000),
        ("xirurgiya_palata", "xirurgiya", "Xirurgiya — Lyuks palata", "Lyuks palata, ovqatlanish bilan", 0, 1200000),
        ("radiologiya_palata", "radiologiya", "Radiologiya bo'limi", "Ovqatlanish bilan", 0, 1100000),
        ("reanimatsiya_palata", "reanimatsiya", "Reanimatsiya bo'limi", "Ovqatlanish bilan", 0, 2100000),
    ]
    services = {}
    for key, dept_key, name, desc, duration, price in svc_data:
        svc = Service(
            id=svc_ids[key],
            clinic_id=clinic_id,
            department_id=dept_ids[dept_key],
            name=name,
            description=desc,
            duration_minutes=duration,
            price_uzs=Decimal(str(price)),
        )
        db.add(svc)
        services[key] = svc
    await db.flush()
    return services


async def seed_doctor_services(db: AsyncSession) -> None:
    """Link doctors to their services."""
    mappings = {
        "nasirxodjaev": ["konsultatsiya"],
        "aripova": ["konsultatsiya"],
        "malikov_nevro": ["konsultatsiya"],
        "malikov_kardio": ["konsultatsiya"],
        "alimxodjaeva": ["professor_konsultatsiya"],
    }
    for doc_key, svc_keys in mappings.items():
        for svc_key in svc_keys:
            await db.execute(
                doctor_services.insert().values(
                    doctor_id=doctor_ids[doc_key],
                    service_id=svc_ids[svc_key],
                )
            )
    await db.flush()


async def seed_patients(db: AsyncSession) -> list[Patient]:
    patient_data = [
        ("Kamolov Otabek Sherzod o'g'li", "+998901234567", "1985-03-15", "uz"),
        ("Ergasheva Malika Rustam qizi", "+998935551234", "1992-07-22", "uz"),
        ("Petrov Aleksandr Ivanovich", "+998712223344", "1978-11-10", "ru"),
        ("Sultanova Zulfiya Akbar qizi", "+998944445566", "2001-01-05", "uz"),
        ("Kim Yevgeniy Sergeevich", "+998977778899", "1965-09-30", "ru"),
    ]
    patients = []
    for i, (name, phone, dob, lang) in enumerate(patient_data):
        p = Patient(
            id=patient_ids[i],
            clinic_id=clinic_id,
            full_name_enc=encrypt_field(name),
            phone_enc=encrypt_field(phone),
            dob_enc=encrypt_field(dob),
            language_preference=lang,
        )
        db.add(p)
        patients.append(p)
    await db.flush()
    return patients


async def seed_devices(db: AsyncSession) -> list[Device]:
    device_data = [
        (device_ids[0], "MZB-KIOSK-001", "Kiosk Lobby 1", "Asosiy vestibul, 1-qavat", DeviceStatus.ONLINE),
        (device_ids[1], "MZB-KIOSK-002", "Kiosk Floor 2", "2-qavat koridori", DeviceStatus.ONLINE),
    ]
    devices = []
    for did, serial, name, location, status in device_data:
        dev = Device(
            id=did,
            clinic_id=clinic_id,
            serial_number=serial,
            name=name,
            location_description=location,
            status=status,
            last_heartbeat=NOW - timedelta(minutes=2),
            config={"display_resolution": "1920x1080", "camera_enabled": True},
        )
        db.add(dev)
        devices.append(dev)
    await db.flush()
    return devices


async def seed_faqs(db: AsyncSession) -> None:
    faqs = [
        ("Klinika qaysi soatlarda ishlaydi?", "Nano Medical Clinic dushanba-shanba kunlari soat 08:00 dan 17:00 gacha ishlaydi. Yakshanba — dam olish kuni."),
        ("Klinika manzili qayerda?", "Toshkent shahri, Olmazor tumani, Talabalar ko'chasi, 52-uy."),
        ("Telefon raqamlar?", "+998 78 113 08 88, +998 55 500 05 50, +998 99 467 80 00"),
        ("Konsultatsiya narxi qancha?", "Oddiy konsultatsiya 260,000 so'm, professor konsultatsiyasi 500,000 so'm."),
        ("Checkup narxi qancha?", "Erkaklar va ayollar uchun to'liq checkup 2,000,000 so'm."),
        ("Qanday shifokorlar bor?", "Bizda endokrinolog, jarroh (proktolog), nevropatolog, kardiolog va mammolog ishlaydi."),
        ("To'lov qanday usullarda qabul qilinadi?", "Naqd pul, Uzcard, Humo, Click va Payme orqali to'lashingiz mumkin."),
        ("Qabulga qanday yozilish mumkin?", "Kiosk terminal orqali yoki telefon raqamlarimizga qo'ng'iroq qilib yozilishingiz mumkin."),
        ("Lyuks palata narxi qancha?", "Terapiya — 1,500,000, Xirurgiya — 1,200,000, Radiologiya — 1,100,000, Reanimatsiya — 2,100,000 so'm/kun. Ovqatlanish kiritilgan."),
        ("Professor Alimxodjaeva qachon qabul qiladi?", "Professor Alimxodjaeva L.T. dushanba-shanba kunlari soat 10:00 dan 13:00 gacha qabul qiladi."),
        ("Qanday to'lov usullari mavjud?", "Naqd pul, Uzcard, Humo, Click va Payme orqali to'lashingiz mumkin."),
        ("Online qabulga yozilish mumkinmi?", "Ha, siz Mezbon kiosk orqali yoki telefon raqamingiz bilan qabulga yozilishingiz mumkin."),
        ("Kutish vaqti qancha?", "O'rtacha kutish vaqti 10-20 daqiqa. Navbat tizimi orqali aniq vaqtni bilib olishingiz mumkin."),
        ("Sug'urta qabul qilasizlarmi?", "Ha, biz asosiy sug'urta kompaniyalari bilan ishlaymiz. Iltimos, sug'urta kartangizni olib keling."),
        ("Natijalarni qanday olish mumkin?", "Tahlil natijalari 1-3 ish kuni ichida tayyor bo'ladi. SMS orqali xabar beriladi."),
    ]
    for i, (q, a) in enumerate(faqs):
        faq = FAQ(
            clinic_id=clinic_id,
            question=q,
            answer=a,
            language="uz",
            sort_order=i,
        )
        db.add(faq)
    await db.flush()


async def seed_announcements(db: AsyncSession) -> None:
    anns = [
        (
            "Nano Medical Clinic ga xush kelibsiz!",
            "Klinikamizda zamonaviy tibbiy uskunalar va tajribali shifokorlar "
            "sizga xizmat ko'rsatadi. Olmazor tumani, Talabalar ko'chasi, 52.",
            NOW - timedelta(days=3),
            NOW + timedelta(days=30),
        ),
        (
            "Professor Alimxodjaeva qabuli",
            "Professor Alimxodjaeva L.T. dushanba-shanba kunlari soat 10:00 dan 13:00 gacha qabul qiladi. "
            "Mammologiya bo'limiga murojaat qiling.",
            NOW - timedelta(days=1),
            NOW + timedelta(days=29),
        ),
        (
            "Bayram kunlari ish tartibi",
            "21-22 mart Navro'z bayrami kunlari klinika soat 09:00 dan 15:00 gacha ishlaydi.",
            NOW,
            NOW + timedelta(days=14),
        ),
    ]
    for title, body, active_from, active_to in anns:
        ann = Announcement(
            clinic_id=clinic_id,
            title=title,
            body=body,
            language="uz",
            active_from=active_from,
            active_to=active_to,
        )
        db.add(ann)
    await db.flush()


async def seed_appointments(db: AsyncSession) -> None:
    """8 appointments referencing Nano Medical doctors and services."""
    appt_data = [
        # Past completed (yesterday)
        (0, patient_ids[0], "nasirxodjaev", "konsultatsiya", YESTERDAY, 9, AppointmentStatus.COMPLETED, PaymentStatus.PAID),
        (1, patient_ids[1], "aripova", "konsultatsiya", YESTERDAY, 10, AppointmentStatus.COMPLETED, PaymentStatus.PAID),
        (2, patient_ids[2], "malikov_nevro", "konsultatsiya", YESTERDAY, 14, AppointmentStatus.COMPLETED, PaymentStatus.PAID),
        # Today
        (3, patient_ids[0], "malikov_kardio", "konsultatsiya", TODAY, 9, AppointmentStatus.CHECKED_IN, PaymentStatus.PENDING),
        (4, patient_ids[3], "alimxodjaeva", "professor_konsultatsiya", TODAY, 10, AppointmentStatus.SCHEDULED, PaymentStatus.PENDING),
        (5, patient_ids[4], "nasirxodjaev", "konsultatsiya", TODAY, 11, AppointmentStatus.SCHEDULED, PaymentStatus.PENDING),
        # Future
        (6, patient_ids[2], "aripova", "konsultatsiya", TOMORROW, 9, AppointmentStatus.SCHEDULED, PaymentStatus.PENDING),
        (7, patient_ids[3], "malikov_nevro", "konsultatsiya", DAY_AFTER, 10, AppointmentStatus.SCHEDULED, PaymentStatus.PENDING),
    ]
    svc_durations = {
        "konsultatsiya": 30,
        "professor_konsultatsiya": 40,
        "checkup_erkak": 120,
        "checkup_ayol": 120,
        "terapiya_palata": 0,
        "xirurgiya_palata": 0,
        "radiologiya_palata": 0,
        "reanimatsiya_palata": 0,
    }
    for idx, pid, doc_key, svc_key, d, hour, status, pay_status in appt_data:
        appt = Appointment(
            id=appt_ids[idx],
            clinic_id=clinic_id,
            patient_id=pid,
            doctor_id=doctor_ids[doc_key],
            service_id=svc_ids[svc_key],
            scheduled_at=dt(d, hour),
            duration_minutes=svc_durations[svc_key],
            status=status,
            payment_status=pay_status,
        )
        db.add(appt)
    await db.flush()


async def seed_payments(db: AsyncSession) -> None:
    """4 payments linked to completed appointments + today."""
    pay_data = [
        # Completed payments for yesterday's appointments
        (0, patient_ids[0], appt_ids[0], 260000, PaymentMethod.UZCARD, PaymentTransactionStatus.COMPLETED, "TXN-2026-001"),
        (1, patient_ids[1], appt_ids[1], 260000, PaymentMethod.CLICK, PaymentTransactionStatus.COMPLETED, "TXN-2026-002"),
        (2, patient_ids[2], appt_ids[2], 260000, PaymentMethod.CASH, PaymentTransactionStatus.COMPLETED, "TXN-2026-003"),
        # Pending payment for today
        (3, patient_ids[3], appt_ids[4], 500000, PaymentMethod.PAYME, PaymentTransactionStatus.PENDING, None),
    ]
    for idx, pid, aid, amount, method, status, txn_id in pay_data:
        pay = Payment(
            id=payment_ids[idx],
            clinic_id=clinic_id,
            patient_id=pid,
            appointment_id=aid,
            amount=Decimal(str(amount)),
            method=method,
            status=status,
            transaction_id=txn_id,
        )
        db.add(pay)
    await db.flush()


async def seed_queue_tickets(db: AsyncSession) -> None:
    """4 queue tickets for today."""
    ticket_data = [
        (0, patient_ids[0], "kardiologiya", "malikov_kardio", "K-001", QueueStatus.COMPLETED),
        (1, patient_ids[3], "mammologiya", "alimxodjaeva", "M-001", QueueStatus.IN_PROGRESS),
        (2, patient_ids[4], "endokrinologiya", "nasirxodjaev", "E-001", QueueStatus.WAITING),
        (3, patient_ids[1], "xirurgiya", "aripova", "X-001", QueueStatus.WAITING),
    ]
    for idx, pid, dept_key, doc_key, number, status in ticket_data:
        called = dt(TODAY, 9, 15) if status in (QueueStatus.IN_PROGRESS, QueueStatus.COMPLETED) else None
        completed = dt(TODAY, 9, 35) if status == QueueStatus.COMPLETED else None
        wait = 0 if status == QueueStatus.COMPLETED else (5 if status == QueueStatus.IN_PROGRESS else (idx + 1) * 10)

        ticket = QueueTicket(
            id=ticket_ids[idx],
            clinic_id=clinic_id,
            patient_id=pid,
            department_id=dept_ids[dept_key],
            doctor_id=doctor_ids[doc_key],
            ticket_number=number,
            status=status,
            estimated_wait_minutes=wait,
            called_at=called,
            completed_at=completed,
        )
        db.add(ticket)
    await db.flush()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    print("=" * 60)
    print("  Mezbon AI — Seed Nano Medical Clinic Data")
    print("=" * 60)

    async with async_session_factory() as db:
        try:
            # 1. Clear existing
            cleared = await clear_existing(db)
            if cleared:
                await db.commit()
                print("  Existing data cleared.\n")

            # 2. Seed everything
            print("  [1/12] Seeding clinic...")
            await seed_clinic(db)

            print("  [2/12] Seeding admin user...")
            await seed_admin(db)

            print("  [3/12] Seeding departments...")
            await seed_departments(db)

            print("  [4/12] Seeding doctors...")
            await seed_doctors(db)

            print("  [5/12] Seeding schedules...")
            await seed_schedules(db)

            print("  [6/12] Seeding services...")
            await seed_services(db)

            print("  [7/12] Linking doctors ↔ services...")
            await seed_doctor_services(db)

            print("  [8/12] Seeding patients (PII encrypted)...")
            await seed_patients(db)

            print("  [9/12] Seeding devices...")
            await seed_devices(db)

            print(" [10/12] Seeding FAQs...")
            await seed_faqs(db)

            print(" [11/12] Seeding announcements...")
            await seed_announcements(db)

            print(" [12/12] Seeding appointments, payments, queue...")
            await seed_appointments(db)
            await seed_payments(db)
            await seed_queue_tickets(db)

            await db.commit()

            print("\n" + "=" * 60)
            print("  SEED COMPLETE!")
            print("=" * 60)
            print(f"""
  Clinic:        {CLINIC_NAME}
  Admin login:   {ADMIN_EMAIL} / {ADMIN_PASSWORD}
  Departments:   8
  Doctors:       5 (with individual Mon-Sat schedules)
  Services:      8
  Patients:      5 (PII encrypted)
  Devices:       2 kiosks
  FAQs:          15 (Uzbek)
  Announcements: 3
  Appointments:  8 (3 past + 3 today + 2 future)
  Payments:      4 (3 completed + 1 pending)
  Queue tickets: 4 (1 completed + 1 in-progress + 2 waiting)
""")

        except Exception as e:
            await db.rollback()
            print(f"\n  ERROR: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
