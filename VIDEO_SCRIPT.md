# 2-Minute Video Script - StudySync Circuit Breaker Demo

**Student:** Aqib Bin Qamar (BSCS23178)
**Assignment:** PDC Assignment 2 - Part 3 (Fault Tolerance)
**Target length:** 1:50 - 2:00

> Tone: chill, confident, technical. Mix of English + Roman Urdu (Hinglish style).
> English: technical terms (circuit breaker, fallback, OPEN, HALF_OPEN, timeout, FastAPI, etc.).
> Roman Urdu: connectors, explanations, reactions.

---

## Setup BEFORE you hit record (don't film this)

1. Open 2 PowerShell windows side-by-side inside `PDC-Sp26-BSCS23178-Qamar`.
2. In both: `.venv\Scripts\Activate.ps1`
3. Window A -> `uvicorn app.main:app --reload`  (leave running)
4. Window B -> empty, this is your "demo" window.
5. Make font size big (Ctrl + scroll) so the recording is readable.
6. Have `app/circuit_breaker.py` open in VS Code in a third tab - you'll flash it for 2 seconds.

---

## 0:00 - 0:15 | Intro

**Show:** your face cam OR just the terminal with the project open in VS Code on the side.

> "Assalam-o-Alaikum, I'm **Aqib Bin Qamar**, roll number **BSCS23178**.
> Ye PDC Assignment 2 ka **Part 3** hai - **Fault Tolerance** wala problem.
> Scenario simple hai: StudySync ka external LLM API kabhi kabhi **60 seconds** ke liye hang ho jata hai, aur uski wajah se **poori FastAPI app freeze** ho jati hai.
> Mera fix hai - ek **Circuit Breaker** with **fallback response**."

---

## 0:15 - 0:30 | Custom header rule (MANDATORY)

**Action:** In Window B, type and run:

```powershell
curl.exe -i http://127.0.0.1:8000/
```

**Point your cursor at the `X-Student-ID` line in the response.**

> "Sabse pehle assignment ka **rule number one** - har response mein custom header hona chahiye.
> Yahan dekhein - **`X-Student-ID: BSCS23178`** - ye middleware har single response pe lagata hai, `app/main.py` mein."

---

## 0:30 - 1:10 | THE "BEFORE" - broken naive behaviour

**Action:** In Window B, run:

```powershell
python scripts/demo.py
```

The script auto-prints banners. While **STEP 2** crashes the LLM, say:

> "Ab mein mock LLM ko **crash** kar raha hoon - simulate kar raha hoon ke upstream service down ho gayi hai, 5 seconds tak hang karegi."

When **STEP 3** runs (naive endpoint, 3 calls), say:

> "Ye dekhein - `/naive/llm`, **bilkul original code**, no protection.
> Har request **timeout** ho rahi hai, **3 seconds** mein.
> Real production mein agar LLM 60 seconds hang ho, to **har FastAPI worker stuck** ho jaye ga aur poori app effectively dead ho jaye gi.
> Ye hai **cascading failure** - ek downstream sick hai, lekin poora system down lag raha hai."

**Point at the `elapsed=` numbers** - they'll show ~3s each.

---

## 1:10 - 1:45 | THE "AFTER" - circuit breaker + fallback

When **STEP 4** prints, say:

> "Ab same crashed LLM, lekin is dafa **circuit breaker** ke through.
> Pehli **3 calls** fail hoti hain - lekin user ko **error nahi**, **fallback answer** milta hai. Dekho - `fallback: true`, ek cached study tip return ho raha hai.
> **3 consecutive failures** ke baad breaker **OPEN** ho jata hai - ab next calls **LLM ko touch hi nahi karte**, instantly fallback return hota hai - **microseconds** mein."

**Point at the line:** `circuit state -> {'state': 'OPEN', ...}`

> "App **fully responsive** hai, user ko clean response mil raha hai, aur dying upstream ko **recover hone ka time** mil raha hai. Ye hai asli fix."

**Optional - 2 second flash of code in VS Code:** Switch to `app/circuit_breaker.py`, scroll to the `call()` method, say:

> "Code mein - `asyncio.wait_for` strict **2-second timeout** lagata hai, failures count karta hai, aur threshold pe state change kar deta hai. Three states - **CLOSED, OPEN, HALF_OPEN**."

---

## 1:45 - 2:00 | Recovery via HALF_OPEN

When **STEP 5** prints, say:

> "Last cheez - **recovery**. Mein ne LLM ko heal kar diya hai, **5 seconds** wait karte hain.
> Breaker **HALF_OPEN** mein jata hai, ek **probe call** allow karta hai - wo succeed hoti hai, aur breaker wapas **CLOSED** ho jata hai. System khud-ba-khud normal pe aa gaya.
> Plus, **`pytest -v`** mein 5 tests bhi hain jo ye sab automatically prove karte hain.
> Bas yehi tha fix - **Circuit Breaker + Fallback + per-call timeout**. Shukriya!"

---

## Numbers to memorize (in case of viva)

| Setting             | Value | Why                                          |
|---------------------|-------|----------------------------------------------|
| `failure_threshold` | 3     | After 3 consecutive failures, trip to OPEN   |
| `call_timeout`      | 2.0s  | Never wait longer than this for the LLM      |
| `recovery_timeout`  | 5.0s  | Time in OPEN before allowing HALF_OPEN probe |

## States cheat-sheet

- **CLOSED** - normal, sab kuch flow ho raha hai, failures count ho rahe hain.
- **OPEN** - tripped. Calls LLM tak jaati hi nahi. Direct fallback return.
- **HALF_OPEN** - probe mode. Ek call allow, succeed hui to CLOSED, fail hui to wapas OPEN.

## CAP trade-off one-liner (if asked)

> "Ye **AP** choice hai - mein consistency-of-content sacrifice kar raha hoon (fallback freshest LLM output nahi hai), taa ke API **available** rahe with **low latency**. 60-second hang ab sub-millisecond fallback ban gaya."

---

## Quick troubleshooting

- Agar `curl.exe` na chale -> `curl -i http://127.0.0.1:8000/` try karo (PowerShell alias).
- Agar `demo.py` 2 minute se zyada le raha -> `scripts/demo.py` mein `hang_seconds=5` ko `3` kar do aur recovery wait `6` ko `4` kar do.
- Agar breaker pehle se OPEN ho -> Window B mein pehle `curl.exe -X POST http://127.0.0.1:8000/circuit/reset` chala lo.

---

## Final shot-list checklist

- [ ] Face/voice intro with name + ID
- [ ] `X-Student-ID` header visible on screen
- [ ] Naive endpoint hanging / timing out (BEFORE)
- [ ] Resilient endpoint returning fallback (AFTER)
- [ ] Circuit state showing `OPEN`
- [ ] Recovery to `CLOSED` after heal
- [ ] Total length under 2:00
