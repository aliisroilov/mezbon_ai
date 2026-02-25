# MEZBON AI — NANO MEDICAL CLINIC CUSTOMIZATION PROMPT

## MISSION

Replace ALL demo/mock data with real **Nano Medical Clinic** data. This is our first paying client. Every screen, every AI response, every database record must reflect this clinic — not "Salomatlik Plus" or generic demo data.

---

## CLIENT DATA (from Excel + logo)

### Clinic Info
```
Name:         Nano Medical Clinic
Address:      г. Ташкент, Алмазарский район, ул. Талабалар, дом 52
              (uz: Toshkent shahri, Olmazor tumani, Talabalar ko'chasi, 52-uy)
Phones:       +998 78 113 08 88 | +998 55 500 05 50 | +998 99 467 80 00
Email:        nanomediccalclinic@gmail.com
Hours Mon-Sat: 08:00 — 17:00
Hours Sunday:  Yopiq (Выходной)
Logo file:     nano-medical-logo.png (already copied to project root)
```

### Departments (inferred from doctors + services)
```
ID: endokrinologiya  | Name: Endokrinologiya   | Name_ru: Эндокринология      | Floor: 1 | Room: 101
ID: xirurgiya        | Name: Xirurgiya          | Name_ru: Хирургия             | Floor: 1 | Room: 102
ID: nevrologiya      | Name: Nevrologiya        | Name_ru: Неврология           | Floor: 2 | Room: 201
ID: kardiologiya     | Name: Kardiologiya       | Name_ru: Кардиология          | Floor: 2 | Room: 202
ID: mammologiya      | Name: Mammologiya        | Name_ru: Маммология           | Floor: 2 | Room: 203
ID: terapiya         | Name: Terapiya           | Name_ru: Терапия              | Floor: 1 | Room: 103
ID: radiologiya      | Name: Radiologiya        | Name_ru: Радиология           | Floor: 1 | Room: 104
ID: reanimatsiya     | Name: Reanimatsiya       | Name_ru: Реанимация           | Floor: 1 | Room: 105
```

### Doctors (REAL DATA — 5 doctors, one has 2 specialties)
```
1. Насирходжаев Ё.Б. (Nasirxodjaev Yo.B.)
   Specialty:    Endokrinolog-radiolog (Эндокринолог-радиолог)
   Department:   Endokrinologiya
   Experience:   28 yil (лет)
   Schedule:     Пн-Сб (Mon-Sat) 08:00-16:00

2. Арипова Н.М. (Aripova N.M.)
   Specialty:    Proktolog, yiringli jarroh (Проктолог - гнойный хирург)
   Department:   Xirurgiya
   Experience:   35 yil
   Schedule:     Пн-Сб (Mon-Sat) 09:00-16:00

3. Маликов А.В. (Malikov A.V.) — NEVROLOGIYA
   Specialty:    Nevropatolog (Невропатолог)
   Department:   Nevrologiya
   Experience:   30 yil
   Schedule:     Пн-Сб (Mon-Sat) 08:00-16:00

4. Маликов А.В. (Malikov A.V.) — KARDIOLOGIYA
   Specialty:    Kardiolog (Кардиолог)
   Department:   Kardiologiya
   Experience:   35 yil
   Schedule:     Пн-Сб (Mon-Sat) 08:00-16:00
   NOTE: Same person as #3! He works in TWO departments.
         Use ONE doctor record with TWO department associations,
         or create 2 separate doctor entries with different IDs.
         Choose whichever is simpler for the current DB schema.

5. Алимходжаева Л.Т. (Alimxodjaeva L.T.)
   Specialty:    Professor, Mammolog (Профессор Маммолог)
   Department:   Mammologiya
   Experience:   30 yil
   Schedule:     Пн-Сб (Mon-Sat) 10:00-13:00 (SHORTER hours!)
```

### Services & Prices (REAL DATA)
```
1. Konsultatsiya (Консультация)
   Description:  Birlamchi ko'rik (Первичный осмотр)
   Price:        260,000 so'm
   Duration:     30 min

2. Professor konsultatsiyasi (Консультация профессора)
   Description:  Professor tomonidan birlamchi ko'rik
   Price:        500,000 so'm
   Duration:     40 min

3. Checkup — Erkaklar (Мужской)
   Description:  Erkaklar uchun to'liq tekshiruv
   Price:        2,000,000 so'm
   Duration:     120 min

4. Checkup — Ayollar (Женский)
   Description:  Ayollar uchun to'liq tekshiruv
   Price:        2,000,000 so'm
   Duration:     120 min

5. Terapiya bo'limi — Lyuks palata (Отделение Терапии)
   Description:  Lyuks palata, ovqatlanish bilan (с питанием)
   Price:        1,500,000 so'm / kun
   Duration:     0 (inpatient — daily rate)

6. Xirurgiya bo'limi — Lyuks palata (Отделение Хирургии)
   Description:  Lyuks palata, ovqatlanish bilan
   Price:        1,200,000 so'm / kun
   Duration:     0

7. Radiologiya bo'limi (Отделение Радиологии)
   Description:  Ovqatlanish bilan (с питанием)
   Price:        1,100,000 so'm / kun
   Duration:     0

8. Reanimatsiya bo'limi (Отделение Реанимации)
   Description:  Ovqatlanish bilan
   Price:        2,100,000 so'm / kun
   Duration:     0
```

---

## FILES TO UPDATE (in priority order)

### 1. LOGO — Copy & integrate
```
Source: nano-medical-logo.png (project root)
Targets:
  → kiosk-ui/public/clinic-logo.png
  → kiosk-ui/public/nano-medical-logo.png
  → kiosk-ui/src/assets/logo.png (if exists)
```
Update ALL references to any old logo in the codebase. Search for:
- "salomatlik" (case-insensitive)
- Any hardcoded logo path
- IdleScreen, GreetingScreen — these show the clinic logo prominently

### 2. `backend/scripts/seed.py` — FULL REWRITE of data
Replace ALL "Salomatlik Plus" data with Nano Medical Clinic:

```python
CLINIC_NAME = "Nano Medical Clinic"
CLINIC_EMAIL = "nanomediccalclinic@gmail.com"
ADMIN_EMAIL = "admin@nanomedical.uz"
ADMIN_PASSWORD = "NanoAdmin2026!"

# Clinic settings
address = "Toshkent shahri, Olmazor tumani, Talabalar ko'chasi, 52-uy"
phone = "+998781130888"
settings = {
    "working_hours": {
        "mon_sat": "08:00-17:00",
        "sunday": "closed"
    },
    "phones": ["+998781130888", "+998555000550", "+998994678000"],
    "languages": ["uz", "ru"],
    "logo": "nano-medical-logo.png"
}
```

**Departments:** Use the 8 departments listed above.

**Doctors:** Use the 5 real doctors. For Malikov A.V. who has 2 specialties:
- Option A: Create 2 doctor records: `malikov-nevro` and `malikov-kardio`
- Option B: One doctor, link to 2 departments
- Choose whichever matches the existing Doctor model schema.

**Schedules:** Each doctor has their OWN hours (not uniform!):
- Nasirxodjaev: Mon-Sat 08:00-16:00
- Aripova: Mon-Sat 09:00-16:00
- Malikov (both): Mon-Sat 08:00-16:00
- Alimxodjaeva: Mon-Sat 10:00-13:00 (only 3 hours!)

**Services:** Use the 8 real services with REAL prices.

**FAQs:** Rewrite ALL to match Nano Medical:
```
Q: Klinika qaysi soatlarda ishlaydi?
A: Nano Medical Clinic dushanba-shanba kunlari soat 08:00 dan 17:00 gacha ishlaydi. Yakshanba — dam olish kuni.

Q: Klinika manzili qayerda?
A: Toshkent shahri, Olmazor tumani, Talabalar ko'chasi, 52-uy.

Q: Telefon raqamlar?
A: +998 78 113 08 88, +998 55 500 05 50, +998 99 467 80 00

Q: Konsultatsiya narxi qancha?
A: Oddiy konsultatsiya 260,000 so'm, professor konsultatsiyasi 500,000 so'm.

Q: Checkup narxi qancha?
A: Erkaklar va ayollar uchun to'liq checkup 2,000,000 so'm.

Q: Qanday shifokorlar bor?
A: Bizda endokrinolog, jarroh (proktolog), nevropatolog, kardiolog va mammolog ishlaydi.

Q: To'lov qanday usullarda qabul qilinadi?
A: Naqd pul, Uzcard, Humo, Click va Payme orqali to'lashingiz mumkin.

Q: Qabulga qanday yozilish mumkin?
A: Kiosk terminal orqali yoki telefon raqamlarimizga qo'ng'iroq qilib yozilishingiz mumkin.

Q: Lyuks palata narxi qancha?
A: Terapiya — 1,500,000, Xirurgiya — 1,200,000, Radiologiya — 1,100,000, Reanimatsiya — 2,100,000 so'm/kun. Ovqatlanish kiritilgan.

Q: Professor Alimxodjaeva qachon qabul qiladi?
A: Professor Alimxodjaeva L.T. dushanba-shanba kunlari soat 10:00 dan 13:00 gacha qabul qiladi.
```

Remove old patients/appointments/payments/tickets — create fresh ones that reference the NEW doctors.

### 3. `backend/app/ai/gemini_service.py` — Update demo data
Replace `_DEMO_DEPARTMENTS` and `_DEMO_DOCTORS` at the bottom of the file:

```python
_DEMO_DEPARTMENTS = [
    {"id": "endokrinologiya", "name": "Endokrinologiya", "description": "Endokrin tizim kasalliklari", "floor": 1, "room": "101"},
    {"id": "xirurgiya", "name": "Xirurgiya", "description": "Jarrohlik xizmatlari", "floor": 1, "room": "102"},
    {"id": "nevrologiya", "name": "Nevrologiya", "description": "Asab tizimi kasalliklari", "floor": 2, "room": "201"},
    {"id": "kardiologiya", "name": "Kardiologiya", "description": "Yurak-qon tomir kasalliklari", "floor": 2, "room": "202"},
    {"id": "mammologiya", "name": "Mammologiya", "description": "Ko'krak bezi kasalliklari", "floor": 2, "room": "203"},
    {"id": "terapiya", "name": "Terapiya", "description": "Umumiy terapevtik xizmatlar", "floor": 1, "room": "103"},
    {"id": "radiologiya", "name": "Radiologiya", "description": "Radiologik tekshiruvlar", "floor": 1, "room": "104"},
    {"id": "reanimatsiya", "name": "Reanimatsiya", "description": "Shoshilinch tibbiy yordam", "floor": 1, "room": "105"},
]

_DEMO_DOCTORS = {
    "endokrinologiya": [
        {"id": "dr-nasirxodjaev", "name": "Nasirxodjaev Yo.B.", "full_name": "Nasirxodjaev Yo'ldosh Botirovich", "specialty": "Endokrinolog-radiolog", "department_id": "endokrinologiya", "department_name": "Endokrinologiya", "experience": "28 yil", "rating": 4.9},
    ],
    "xirurgiya": [
        {"id": "dr-aripova", "name": "Aripova N.M.", "full_name": "Aripova Nargiza Mirkomilovna", "specialty": "Proktolog, yiringli jarroh", "department_id": "xirurgiya", "department_name": "Xirurgiya", "experience": "35 yil", "rating": 4.8},
    ],
    "nevrologiya": [
        {"id": "dr-malikov-nevro", "name": "Malikov A.V.", "full_name": "Malikov Abdulla Valijonovich", "specialty": "Nevropatolog", "department_id": "nevrologiya", "department_name": "Nevrologiya", "experience": "30 yil", "rating": 4.9},
    ],
    "kardiologiya": [
        {"id": "dr-malikov-kardio", "name": "Malikov A.V.", "full_name": "Malikov Abdulla Valijonovich", "specialty": "Kardiolog", "department_id": "kardiologiya", "department_name": "Kardiologiya", "experience": "35 yil", "rating": 4.9},
    ],
    "mammologiya": [
        {"id": "dr-alimxodjaeva", "name": "Prof. Alimxodjaeva L.T.", "full_name": "Alimxodjaeva Lola Toshpulatovna", "specialty": "Professor, Mammolog", "department_id": "mammologiya", "department_name": "Mammologiya", "experience": "30 yil", "rating": 5.0},
    ],
}
```

Also update `_fn_demo_search_faq` to return Nano Medical info (hours, address, prices).

### 4. `kiosk-ui/src/utils/mockData.ts` — Update frontend mock data
Replace ALL mock data:

**MOCK_DEPARTMENTS** → 8 Nano Medical departments with proper icons:
```
Endokrinologiya  🔬
Xirurgiya        🔪
Nevrologiya      🧠
Kardiologiya     🫀
Mammologiya      🩺
Terapiya         💊
Radiologiya      📡
Reanimatsiya     🚑
```

**MOCK_DOCTORS** → 5 real doctors (with Malikov appearing twice for 2 depts)

**MOCK_SERVICES** → 8 real services with real prices

**MOCK_FAQS** → Nano Medical FAQs

**MOCK_QUEUE_TICKET** → Update department/doctor references

### 5. `backend/app/ai/prompts/system_prompt.py` — Update AI persona
The AI must know it works at Nano Medical Clinic. Update the system prompt:

```
- Replace any "Salomatlik" or generic clinic name → "Nano Medical Clinic"
- Address: Toshkent, Olmazor tumani, Talabalar ko'chasi, 52
- Phones: 78 113 08 88, 55 500 05 50, 99 467 80 00
- Hours: Dush-Shanba 08:00-17:00, Yakshanba yopiq
- The AI should say "Nano Medical Clinic ga xush kelibsiz!" not generic greeting
```

### 6. `kiosk-ui/src/screens/IdleScreen.tsx` — Show Nano Medical logo
- Display `clinic-logo.png` prominently (center, ~200px width)
- Show "Nano Medical Clinic" as clinic name
- Update any welcome text

### 7. `kiosk-ui/src/screens/GreetingScreen.tsx` — Clinic branding
- Show Nano Medical logo (smaller, top area)
- Update greeting text to mention Nano Medical

### 8. `kiosk-ui/src/i18n/uz.json`, `ru.json`, `en.json`
Search and replace all occurrences of old clinic names. Add/update:
```json
{
  "clinic_name": "Nano Medical Clinic",
  "clinic_address": "Toshkent, Olmazor tumani, Talabalar ko'chasi, 52",
  "clinic_phone": "+998 78 113 08 88",
  "welcome_message": "Nano Medical Clinic ga xush kelibsiz!",
  "working_hours": "Dush-Shanba: 08:00-17:00 | Yakshanba: Yopiq"
}
```

### 9. UI Theme — Match Nano Medical brand colors
The logo uses **dark navy blue** (`#1B3A6B` approximately). Update the design system:
```
Primary color:     #1B3A6B (navy blue from logo)
Primary light:     #2A5298
Primary dark:      #0F2345
Accent:            #4A90D9 (lighter blue for buttons)
Background:        #F8FAFC (light gray-white)
```
Update in:
- `tailwind.config.ts` — custom colors
- `kiosk-ui/src/styles/globals.css` — CSS variables
- Any hardcoded teal/emerald colors → navy blue

### 10. `kiosk-ui/src/config.ts` or `.env`
```
VITE_CLINIC_NAME=Nano Medical Clinic
VITE_CLINIC_PHONE=+998781130888
```

---

## SEARCH & REPLACE CHECKLIST

Run these searches across the ENTIRE codebase and replace:
```
"Salomatlik Plus"     → "Nano Medical Clinic"
"Salomatlik"          → "Nano Medical"
"salomatlik"          → "nanomedical"
"info@salomatlik.uz"  → "nanomediccalclinic@gmail.com"
"admin@salomatlik.uz" → "admin@nanomedical.uz"
"Mirzo Ulug'bek"      → "Olmazor"
"Buyuk Ipak Yo'li 42" → "Talabalar ko'chasi, 52-uy"
"+998712345678"       → "+998781130888"
"08:00-20:00"         → "08:00-17:00"
"Chilonzor"           → "Olmazor"
```

Also search for any remaining references to old demo doctors:
```
"Rahimov", "Karimova", "Umarov", "Abdullayeva", "Toshmatov",
"Mirzayeva", "Xolmatov", "Nazarova", "Ismoilov", "Yusupova",
"Ahmadov", "Azimov", "Sobirov"
```
Replace with Nano Medical doctors where they appear in demo responses.

---

## IMPORTANT RULES

1. **Do NOT break existing functionality.** This is a data swap, not a refactor.
2. **Keep the same DB schema.** Only change the data VALUES, not table structures.
3. **Test seed.py works:** After changes, run `cd backend && python scripts/seed.py` — it must complete with zero errors.
4. **Test frontend builds:** `cd kiosk-ui && npm run build` must succeed.
5. **The AI brain must know it's Nano Medical.** Test by asking "Bu qaysi klinika?" — it should answer "Nano Medical Clinic."
6. **Every screen that shows clinic info must show Nano Medical data.**
7. **Logo must appear on: IdleScreen, GreetingScreen, and printed tickets.**
8. **Prices must be EXACT.** Konsultatsiya = 260,000, not 50,000 or 80,000.
9. **Doctor schedules must be INDIVIDUAL.** Alimxodjaeva works 10:00-13:00, NOT 08:00-17:00.
10. **i18n files must be consistent.** If uz.json says "Nano Medical", ru.json must too.

---

## VERIFICATION

After ALL changes, verify:

- [ ] `seed.py` runs without errors
- [ ] `npm run build` succeeds
- [ ] IdleScreen shows Nano Medical logo
- [ ] GreetingScreen says "Nano Medical Clinic ga xush kelibsiz"
- [ ] AI responds with Nano Medical info when asked "klinika haqida"
- [ ] Department list shows 8 Nano Medical departments (not old 5)
- [ ] Doctor list shows real doctors (Nasirxodjaev, Aripova, Malikov, Alimxodjaeva)
- [ ] Service prices match Excel (260k, 500k, 2M, etc.)
- [ ] FAQ answers reference Nano Medical address, phones, hours
- [ ] No "Salomatlik" text anywhere in the UI or AI responses
- [ ] No old demo doctor names in any response
- [ ] UI colors match navy blue brand (#1B3A6B)
- [ ] Backend logs show "Nano Medical Clinic" on startup
