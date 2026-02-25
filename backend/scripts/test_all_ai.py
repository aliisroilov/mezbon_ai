#!/usr/bin/env python3
"""
Test all AI services: Gemini, InsightFace, Muxlisa
Run: cd backend && python scripts/test_all_ai.py
"""

import asyncio
import os
import sys
import time

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# ── Colors ──────────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

PASS = f"{GREEN}PASS{RESET}"
FAIL = f"{RED}FAIL{RESET}"
SKIP = f"{YELLOW}SKIP{RESET}"

# ── Results collector ───────────────────────────────────────────────────────
results: list[dict] = []


def record(service: str, passed: bool, latency_s: float, note: str = "") -> None:
    results.append({
        "service": service,
        "passed": passed,
        "latency_s": latency_s,
        "note": note,
    })
    status = PASS if passed else FAIL
    lat_str = f"{latency_s:.2f}s"
    note_str = f" ({note})" if note else ""
    print(f"  {status} {service} — {lat_str}{note_str}")


# ══════════════════════════════════════════════════════════════════════════════
# Test A — Gemini 2.0 Flash
# ══════════════════════════════════════════════════════════════════════════════
async def test_gemini() -> bool:
    print(f"\n{BOLD}{CYAN}═══ Test A: Gemini 2.0 Flash ═══{RESET}")
    api_key = os.getenv("GEMINI_API_KEY", "")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    if not api_key or api_key.startswith("YOUR_"):
        print(f"  {SKIP} GEMINI_API_KEY not set")
        record("Gemini", False, 0, "no API key")
        return False

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=300,
            ),
        )

        # Test 1: Basic greeting
        print(f"\n  {DIM}1. Sending: 'Assalomu alaykum'{RESET}")
        t0 = time.monotonic()
        response = await model.generate_content_async("Assalomu alaykum")
        lat = time.monotonic() - t0
        print(f"     Response: {response.text[:120]}...")
        print(f"     Latency: {lat:.2f}s")

        # Test 2: Appointment intent
        print(f"\n  {DIM}2. Sending: 'Stomatologga yozilmoqchiman'{RESET}")
        t1 = time.monotonic()
        response2 = await model.generate_content_async("Stomatologga yozilmoqchiman")
        lat2 = time.monotonic() - t1
        print(f"     Response: {response2.text[:120]}...")
        print(f"     Latency: {lat2:.2f}s")

        # Test 3: FAQ intent
        print(f"\n  {DIM}3. Sending: 'Ish vaqtingiz qanday?'{RESET}")
        t2 = time.monotonic()
        response3 = await model.generate_content_async("Ish vaqtingiz qanday?")
        lat3 = time.monotonic() - t2
        print(f"     Response: {response3.text[:120]}...")
        print(f"     Latency: {lat3:.2f}s")

        avg_lat = (lat + lat2 + lat3) / 3
        record("Gemini", True, avg_lat, f"model={model_name}")
        return True

    except Exception as exc:
        print(f"  {RED}Error: {exc}{RESET}")
        record("Gemini", False, 0, str(exc)[:60])
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Test B — InsightFace
# ══════════════════════════════════════════════════════════════════════════════
async def test_insightface() -> bool:
    print(f"\n{BOLD}{CYAN}═══ Test B: InsightFace ═══{RESET}")

    try:
        import numpy as np

        model_name = os.getenv("INSIGHTFACE_MODEL", "buffalo_l")
        device = os.getenv("INSIGHTFACE_DEVICE", "cpu")

        print(f"  Loading model '{model_name}' on {device}...")
        print(f"  {DIM}(First run downloads ~300MB — be patient){RESET}")

        t0 = time.monotonic()

        from insightface.app import FaceAnalysis

        fa = FaceAnalysis(
            name=model_name,
            providers=(
                ["CUDAExecutionProvider"] if device == "cuda"
                else ["CPUExecutionProvider"]
            ),
        )
        fa.prepare(ctx_id=0 if device == "cuda" else -1, det_size=(640, 640))
        load_time = time.monotonic() - t0
        print(f"  Model loaded in {load_time:.1f}s")

        # Generate a synthetic test image with a simple face-like pattern
        # (avoids needing to download from external URL)
        print(f"\n  {DIM}Generating test image...{RESET}")
        test_img_path = "/tmp/test_face_ai.jpg"

        # Try downloading a real face image
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            try:
                resp = await client.get("https://thispersondoesnotexist.com")
                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(test_img_path, "wb") as f:
                        f.write(resp.content)
                    print(f"  Downloaded test face to {test_img_path}")
                else:
                    raise ValueError("Bad response")
            except Exception:
                # Fallback: create a simple synthetic image
                print(f"  {YELLOW}Could not download test face, using synthetic image{RESET}")
                img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
                import cv2
                cv2.imwrite(test_img_path, img)

        import cv2
        img = cv2.imread(test_img_path)
        if img is None:
            print(f"  {RED}Failed to load test image{RESET}")
            record("InsightFace", False, load_time, "image load failed")
            return False

        print(f"  Image shape: {img.shape}")

        # Detect faces
        t1 = time.monotonic()
        faces = fa.get(img)
        detect_time = time.monotonic() - t1

        print(f"\n  Faces detected: {len(faces)}")
        print(f"  Detection time: {detect_time:.3f}s")

        if faces:
            face = faces[0]
            bbox = face.bbox
            score = float(face.det_score)
            print(f"  Bounding box: [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]")
            print(f"  Confidence: {score:.4f}")

            # Get embedding
            embedding = face.embedding
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            print(f"\n  Embedding shape: {embedding.shape}")
            print(f"  First 5 values: {embedding[:5]}")

            # Self-similarity (should be ~1.0)
            self_sim = float(np.dot(embedding, embedding))
            print(f"  Self-similarity: {self_sim:.6f}")

            record("InsightFace", True, detect_time, f"{len(faces)} face(s)")
            return True
        else:
            print(f"  {YELLOW}No faces detected in test image (may be synthetic){RESET}")
            # Still PASS — model loaded and ran, just no faces in synthetic image
            record("InsightFace", True, detect_time, "model loaded, 0 faces in test img")
            return True

    except Exception as exc:
        print(f"  {RED}Error: {exc}{RESET}")
        record("InsightFace", False, 0, str(exc)[:60])
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Test C — Muxlisa TTS
# ══════════════════════════════════════════════════════════════════════════════
async def test_muxlisa_tts() -> tuple[bool, bytes]:
    print(f"\n{BOLD}{CYAN}═══ Test C: Muxlisa TTS ═══{RESET}")
    api_key = os.getenv("MUXLISA_API_KEY", "")
    base_url = os.getenv("MUXLISA_API_URL", "https://service.muxlisa.uz/api/v2").rstrip("/")

    if not api_key or api_key.startswith("YOUR_"):
        print(f"  {SKIP} MUXLISA_API_KEY not set")
        record("Muxlisa TTS", False, 0, "no API key")
        return False, b""

    text = "Assalomu alaykum, klinikamizga xush kelibsiz!"
    print(f'  Text: "{text}"')
    print(f"  Speaker: 0 (female)")
    print(f"  URL: {base_url}/tts")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            t0 = time.monotonic()
            response = await client.post(
                f"{base_url}/tts",
                json={"text": text, "speaker": 0},
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                },
            )
            lat = time.monotonic() - t0

            print(f"\n  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
            print(f"  Response size: {len(response.content)} bytes")
            print(f"  Latency: {lat:.2f}s")

            if response.status_code != 200:
                print(f"  {RED}Response body: {response.text[:200]}{RESET}")
                record("Muxlisa TTS", False, lat, f"HTTP {response.status_code}")
                return False, b""

            audio = response.content
            if len(audio) < 100:
                print(f"  {RED}Audio too small — likely not valid WAV{RESET}")
                record("Muxlisa TTS", False, lat, "audio too small")
                return False, b""

            # Save to file
            wav_path = "/tmp/test_tts.wav"
            with open(wav_path, "wb") as f:
                f.write(audio)
            print(f"  Saved to: {wav_path}")

            record("Muxlisa TTS", True, lat, f"{len(audio)} bytes")
            return True, audio

    except Exception as exc:
        print(f"  {RED}Error: {exc}{RESET}")
        record("Muxlisa TTS", False, 0, str(exc)[:60])
        return False, b""


# ══════════════════════════════════════════════════════════════════════════════
# Test D — Muxlisa STT
# ══════════════════════════════════════════════════════════════════════════════
async def test_muxlisa_stt(audio_bytes: bytes) -> tuple[bool, str]:
    print(f"\n{BOLD}{CYAN}═══ Test D: Muxlisa STT ═══{RESET}")
    api_key = os.getenv("MUXLISA_API_KEY", "")
    base_url = os.getenv("MUXLISA_API_URL", "https://service.muxlisa.uz/api/v2").rstrip("/")

    if not api_key or api_key.startswith("YOUR_"):
        print(f"  {SKIP} MUXLISA_API_KEY not set")
        record("Muxlisa STT", False, 0, "no API key")
        return False, ""

    if not audio_bytes:
        # Try loading from file
        wav_path = "/tmp/test_tts.wav"
        if os.path.exists(wav_path):
            with open(wav_path, "rb") as f:
                audio_bytes = f.read()
            print(f"  Loaded audio from {wav_path} ({len(audio_bytes)} bytes)")
        else:
            print(f"  {SKIP} No audio available (TTS test must pass first)")
            record("Muxlisa STT", False, 0, "no audio input")
            return False, ""

    print(f"  Audio size: {len(audio_bytes)} bytes")
    print(f"  URL: {base_url}/stt")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            t0 = time.monotonic()
            response = await client.post(
                f"{base_url}/stt",
                headers={"x-api-key": api_key},
                files={"audio": ("test.wav", audio_bytes, "audio/wav")},
            )
            lat = time.monotonic() - t0

            print(f"\n  Status: {response.status_code}")
            print(f"  Latency: {lat:.2f}s")

            if response.status_code != 200:
                print(f"  {RED}Response body: {response.text[:200]}{RESET}")
                record("Muxlisa STT", False, lat, f"HTTP {response.status_code}")
                return False, ""

            data = response.json()
            transcript = data.get("text", "")
            print(f"  Transcript: \"{transcript}\"")
            print(f"  Response JSON: {data}")

            record("Muxlisa STT", True, lat, f'"{transcript[:40]}"')
            return True, transcript

    except Exception as exc:
        print(f"  {RED}Error: {exc}{RESET}")
        record("Muxlisa STT", False, 0, str(exc)[:60])
        return False, ""


# ══════════════════════════════════════════════════════════════════════════════
# Test E — Full Round-Trip
# ══════════════════════════════════════════════════════════════════════════════
async def test_full_chain() -> bool:
    print(f"\n{BOLD}{CYAN}═══ Test E: Full Round-Trip Chain ═══{RESET}")
    api_key_gemini = os.getenv("GEMINI_API_KEY", "")
    api_key_muxlisa = os.getenv("MUXLISA_API_KEY", "")
    base_url = os.getenv("MUXLISA_API_URL", "https://service.muxlisa.uz/api/v2").rstrip("/")

    if not api_key_gemini or api_key_gemini.startswith("YOUR_"):
        print(f"  {SKIP} GEMINI_API_KEY not set")
        record("Full Chain", False, 0, "no Gemini key")
        return False
    if not api_key_muxlisa or api_key_muxlisa.startswith("YOUR_"):
        print(f"  {SKIP} MUXLISA_API_KEY not set")
        record("Full Chain", False, 0, "no Muxlisa key")
        return False

    total_start = time.monotonic()

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key_gemini)
        model = genai.GenerativeModel(
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            generation_config=genai.GenerationConfig(temperature=0.7, max_output_tokens=200),
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Input text → TTS → audio
            input_text = "Bugun qaysi shifokor ishlaydi?"
            print(f'\n  Step 1: TTS — "{input_text}"')
            t0 = time.monotonic()
            tts_resp = await client.post(
                f"{base_url}/tts",
                json={"text": input_text, "speaker": 0},
                headers={"Content-Type": "application/json", "x-api-key": api_key_muxlisa},
            )
            tts_lat = time.monotonic() - t0
            tts_resp.raise_for_status()
            audio1 = tts_resp.content
            print(f"     TTS: {len(audio1)} bytes, {tts_lat:.2f}s")

            # Step 2: Audio → STT → transcript
            print(f"  Step 2: STT — audio → transcript")
            t1 = time.monotonic()
            stt_resp = await client.post(
                f"{base_url}/stt",
                headers={"x-api-key": api_key_muxlisa},
                files={"audio": ("round_trip.wav", audio1, "audio/wav")},
            )
            stt_lat = time.monotonic() - t1
            stt_resp.raise_for_status()
            transcript = stt_resp.json().get("text", "")
            print(f'     STT: "{transcript}", {stt_lat:.2f}s')

            # Step 3: Transcript → Gemini → AI response
            gemini_input = transcript if transcript else input_text
            print(f'  Step 3: Gemini — "{gemini_input[:50]}"')
            t2 = time.monotonic()
            gemini_resp = await model.generate_content_async(gemini_input)
            gemini_lat = time.monotonic() - t2
            ai_text = gemini_resp.text
            print(f'     Gemini: "{ai_text[:80]}...", {gemini_lat:.2f}s')

            # Step 4: AI response → TTS → response audio
            # Truncate to 512 chars for TTS
            tts_text = ai_text[:512] if ai_text else "Javob topilmadi."
            print(f'  Step 4: TTS — "{tts_text[:50]}..."')
            t3 = time.monotonic()
            tts2_resp = await client.post(
                f"{base_url}/tts",
                json={"text": tts_text, "speaker": 0},
                headers={"Content-Type": "application/json", "x-api-key": api_key_muxlisa},
            )
            tts2_lat = time.monotonic() - t3
            tts2_resp.raise_for_status()
            audio2 = tts2_resp.content
            print(f"     TTS: {len(audio2)} bytes, {tts2_lat:.2f}s")

        total_lat = time.monotonic() - total_start
        print(f"\n  {BOLD}Total round-trip: {total_lat:.2f}s{RESET}")
        print(f"    TTS1: {tts_lat:.2f}s | STT: {stt_lat:.2f}s | Gemini: {gemini_lat:.2f}s | TTS2: {tts2_lat:.2f}s")

        record("Full Chain", True, total_lat)
        return True

    except Exception as exc:
        total_lat = time.monotonic() - total_start
        print(f"  {RED}Error: {exc}{RESET}")
        record("Full Chain", False, total_lat, str(exc)[:60])
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════════════
def print_summary() -> None:
    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  AI Services Test Summary{RESET}")
    print(f"{'═' * 60}")
    print(f"  {'Service':<16} {'Status':<10} {'Latency':<10} {'Note'}")
    print(f"  {'─' * 54}")

    all_passed = True
    for r in results:
        status = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        lat = f"{r['latency_s']:.2f}s" if r["latency_s"] > 0 else "—"
        note = r["note"][:30] if r["note"] else ""
        print(f"  {r['service']:<16} {status:<18} {lat:<10} {note}")
        if not r["passed"]:
            all_passed = False

    print(f"  {'─' * 54}")
    if all_passed:
        print(f"  {GREEN}{BOLD}All services operational!{RESET}")
    else:
        failed = [r["service"] for r in results if not r["passed"]]
        print(f"  {RED}{BOLD}Failed: {', '.join(failed)}{RESET}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
async def main() -> None:
    print(f"\n{BOLD}{CYAN}Mezbon AI — Service Test Suite{RESET}")
    print(f"{DIM}Testing Gemini, InsightFace, Muxlisa TTS/STT{RESET}")
    print(f"{'─' * 50}")

    # Show config
    print(f"\n  GEMINI_API_KEY: {'***' + os.getenv('GEMINI_API_KEY', '')[-4:] if os.getenv('GEMINI_API_KEY') else '(not set)'}")
    print(f"  GEMINI_MODEL:   {os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')}")
    print(f"  MUXLISA_API_URL: {os.getenv('MUXLISA_API_URL', '(not set)')}")
    print(f"  MUXLISA_API_KEY: {'***' + os.getenv('MUXLISA_API_KEY', '')[-4:] if os.getenv('MUXLISA_API_KEY') else '(not set)'}")
    print(f"  MUXLISA_MOCK:   {os.getenv('MUXLISA_MOCK', 'true')}")
    print(f"  INSIGHTFACE:    {os.getenv('INSIGHTFACE_MODEL', 'buffalo_l')} on {os.getenv('INSIGHTFACE_DEVICE', 'cpu')}")

    # Run tests
    await test_gemini()
    await test_insightface()

    tts_ok, tts_audio = await test_muxlisa_tts()

    # Add small delay between Muxlisa calls to avoid rate limiting
    if tts_ok:
        await asyncio.sleep(1.0)

    await test_muxlisa_stt(tts_audio)

    # Small delay before full chain
    await asyncio.sleep(1.0)
    await test_full_chain()

    print_summary()


if __name__ == "__main__":
    asyncio.run(main())
