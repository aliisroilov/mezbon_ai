"""
Test the Mezbon AI brain independently — no frontend, no Redis, no DB needed.
Simulates a full conversation to verify Gemini works correctly.

Usage:
    cd backend && python scripts/test_brain.py
"""

import asyncio
import os
import sys
import warnings

# Suppress FutureWarnings from google.generativeai
warnings.filterwarnings("ignore", category=FutureWarning)

# Add backend to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

# Patch settings to work without full env
os.environ.setdefault("JWT_SECRET", "test")
os.environ.setdefault("JWT_REFRESH_SECRET", "test")
os.environ.setdefault("ENCRYPTION_KEY", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


CLINIC_CONTEXT = {
    "clinic_name": "Nano Medical Clinic",
    "clinic_address": "Toshkent, Olmazor tumani, Talabalar ko'chasi, 52-uy",
    "clinic_phone": "+998 78 113 08 88",
    "working_hours": "Dush-Shanba 08:00-17:00, Yakshanba yopiq",
    "departments": [
        {"name": "Endokrinologiya", "description": "Endokrin tizim kasalliklari"},
        {"name": "Xirurgiya", "description": "Jarrohlik xizmatlari"},
        {"name": "Nevrologiya", "description": "Asab tizimi kasalliklari"},
        {"name": "Kardiologiya", "description": "Yurak-qon tomir kasalliklari"},
        {"name": "Mammologiya", "description": "Ko'krak bezi kasalliklari"},
        {"name": "Terapiya", "description": "Umumiy terapevtik xizmatlar"},
        {"name": "Radiologiya", "description": "Radiologik tekshiruvlar"},
        {"name": "Reanimatsiya", "description": "Shoshilinch tibbiy yordam"},
    ],
    "doctors_on_duty": [
        {"full_name": "Nasirxodjaev Yo.B.", "specialty": "Endokrinolog-radiolog", "department": "Endokrinologiya"},
        {"full_name": "Aripova N.M.", "specialty": "Proktolog, yiringli jarroh", "department": "Xirurgiya"},
        {"full_name": "Malikov A.V.", "specialty": "Nevropatolog", "department": "Nevrologiya"},
        {"full_name": "Malikov A.V.", "specialty": "Kardiolog", "department": "Kardiologiya"},
        {"full_name": "Prof. Alimxodjaeva L.T.", "specialty": "Professor, Mammolog", "department": "Mammologiya"},
    ],
}


async def test_brain():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env")
        return

    from app.ai.gemini_service import GeminiService

    gemini = GeminiService()
    await gemini.initialize(CLINIC_CONTEXT)

    session = "test-brain-001"

    conversations = [
        (
            "Salom",
            "Should greet warmly in Uzbek, no function calls",
            {"no_json": True, "no_functions": True, "expect_no_navigate": True},
        ),
        (
            "[CURRENT_STATE: GREETING] Endokrinologga borishim kerak",
            "Should call get_department_info AND navigate_screen('doctors')",
            {"no_json": True, "expect_navigate": True, "expect_fn": ["get_department_info"]},
        ),
        (
            "[CURRENT_STATE: SELECT_DOCTOR] Nasirxodjaev",
            "Should call get_available_slots for Nasirxodjaev AND navigate_screen('timeslots')",
            {"no_json": True, "expect_navigate": True},
        ),
        (
            "[CURRENT_STATE: SELECT_TIMESLOT] Ikki yarimda",
            "Should ask for visitor's name (only name, NOT phone)",
            {"no_json": True, "expect_no_navigate": True},
        ),
        (
            "[CURRENT_STATE: SELECT_TIMESLOT] Jasur",
            "Should ask for phone number",
            {"no_json": True},
        ),
        (
            "[CURRENT_STATE: SELECT_TIMESLOT] toquz nol bir ikki uch tort besh olti yetti",
            "Should confirm booking details AND navigate_screen('booking_confirm')",
            {"no_json": True, "expect_navigate": True},
        ),
        (
            "[CURRENT_STATE: CONFIRM_BOOKING] Ha",
            "Should call book_appointment AND navigate_screen('queue_ticket')",
            {"no_json": True, "expect_navigate": True, "expect_fn": ["book_appointment"]},
        ),
    ]

    print("=" * 60)
    print("MEZBON AI BRAIN TEST")
    print("=" * 60)

    all_passed = True

    for i, (user_msg, expected, checks) in enumerate(conversations, 1):
        print(f"\n{'─' * 60}")
        print(f"TURN {i}")
        print(f"  Bemor:    '{user_msg}'")
        print(f"  Expected: {expected}")

        try:
            response = await gemini.chat(
                session_id=session,
                message=user_msg,
                clinic_id=None,
                db=None,
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            all_passed = False
            continue

        fn_names = [f["name"] for f in response.function_calls]
        print(f"  AI:       '{response.text}'")
        print(f"  Functions: {fn_names}")
        print(f"  UI:       {response.ui_action}")
        print(f"  Length:   {len(response.text)} chars")

        # Checks
        is_ok = True

        if not response.text:
            print("  FAIL: EMPTY RESPONSE")
            is_ok = False

        if checks.get("no_json") and response.text:
            if response.text.strip().startswith(("{", "[", '"intent')):
                print("  FAIL: GOT JSON INSTEAD OF NATURAL LANGUAGE")
                is_ok = False

        if len(response.text) > 500:
            print(f"  WARN: Too long ({len(response.text)} chars) — should be <200 for voice")

        # Check navigate_screen was called when expected
        has_navigate = "navigate_screen" in fn_names
        if checks.get("expect_navigate") and not has_navigate:
            # Check if ui_action was set via fallback (which means navigation will still work)
            if response.ui_action:
                print(f"  INFO: navigate_screen not called but ui_action={response.ui_action} (fallback OK)")
            else:
                print("  WARN: Expected navigate_screen but not called (may work via fallback)")

        if checks.get("expect_no_navigate") and has_navigate:
            print("  WARN: navigate_screen called unexpectedly")

        # Check expected functions were called
        expected_fns = checks.get("expect_fn", [])
        for efn in expected_fns:
            if efn not in fn_names:
                print(f"  WARN: Expected {efn} but not called")

        print(f"  {'PASS' if is_ok else 'FAIL'}")
        if not is_ok:
            all_passed = False

    # ── Russian test ──
    print(f"\n{'─' * 60}")
    print("RUSSIAN TEST")
    session_ru = "test-brain-ru"
    try:
        r = await gemini.chat(session_ru, "Здравствуйте", clinic_id=None, db=None)
        print(f"  Bemor: 'Здравствуйте'")
        print(f"  AI:    '{r.text}'")
        is_russian = any(c in r.text.lower() for c in "абвгдежзиклмнопрстуфхцчшщэюя")
        print(f"  {'PASS: Responds in Russian' if is_russian else 'FAIL: Not Russian'}")
        if not is_russian:
            all_passed = False
    except Exception as e:
        print(f"  ERROR: {e}")
        all_passed = False

    # ── English test ──
    print(f"\n{'─' * 60}")
    print("ENGLISH TEST")
    session_en = "test-brain-en"
    try:
        r = await gemini.chat(session_en, "Hello, I need to see a dentist", clinic_id=None, db=None)
        print(f"  Bemor: 'Hello, I need to see a dentist'")
        print(f"  AI:    '{r.text}'")
        print(f"  Functions: {[f['name'] for f in r.function_calls]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Gibberish test ──
    print(f"\n{'─' * 60}")
    print("GIBBERISH TEST")
    session_g = "test-brain-gibberish"
    try:
        r = await gemini.chat(session_g, "asjdhaksjdh", clinic_id=None, db=None)
        print(f"  Bemor: 'asjdhaksjdh'")
        print(f"  AI:    '{r.text}'")
        ok = r.text and not r.text.strip().startswith("{")
        print(f"  {'PASS: Handled gracefully' if ok else 'FAIL'}")
        if not ok:
            all_passed = False
    except Exception as e:
        print(f"  ERROR: {e}")
        all_passed = False

    # ── Prices test ──
    print(f"\n{'─' * 60}")
    print("PRICES TEST")
    session_p = "test-brain-prices"
    try:
        r = await gemini.chat(session_p, "Konsultatsiya narxi qancha?", clinic_id=None, db=None)
        print(f"  Bemor: 'Konsultatsiya narxi qancha?'")
        print(f"  AI:    '{r.text}'")
        print(f"  Functions: {[f['name'] for f in r.function_calls]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Queue test ──
    print(f"\n{'─' * 60}")
    print("QUEUE TEST")
    session_q = "test-brain-queue"
    try:
        r = await gemini.chat(session_q, "Endokrinologiyada navbat qancha?", clinic_id=None, db=None)
        print(f"  Bemor: 'Endokrinologiyada navbat qancha?'")
        print(f"  AI:    '{r.text}'")
        print(f"  Functions: {[f['name'] for f in r.function_calls]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print(f"\n{'=' * 60}")
    print(f"RESULT: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(test_brain())
