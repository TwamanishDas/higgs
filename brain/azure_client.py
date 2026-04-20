"""
Azure OpenAI client with brainstorming prompt engine.
- Rotates through 8 assistance categories so every scan has a fresh angle.
- Injects the last 20 recommendations so GPT-4o never repeats itself.
- Auto-soul trait injection when user hasn't configured custom soul.
"""
import json
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log

_endpoint:    str  = ""
_api_key:     str  = ""
_deployment:  str  = ""
_api_version: str  = "2024-12-01-preview"
_identity:    dict = {}
_soul:        dict = {}
_auto_trait:  str  = ""

# ── Assistance category rotation ─────────────────────────────────────────────
# Each scan picks the next category so advice is always from a different angle.
_CATEGORIES = [
    ("workflow",       "Workflow Optimisation",
     "Look at what the user is doing right now and suggest one concrete way to do it faster, "
     "smarter, or with less friction. Reference the specific app or task by name."),

    ("task_deadline",  "Task & Deadline Intelligence",
     "Review upcoming/overdue tasks and deadlines. Prioritise the most urgent one, "
     "estimate effort, and suggest a concrete next action. If all tasks are fine, "
     "encourage the user or suggest planning ahead."),

    ("deep_work",      "Focus & Deep Work",
     "Assess distraction signals (many open windows, frequent switching, high CPU from "
     "background apps). Recommend a focus strategy: close distractions, set a timer, "
     "use a specific technique (Pomodoro, time-blocking). Be specific about what to close."),

    ("health_break",   "Health & Wellbeing",
     "Consider how long the user has likely been working (time of day, session patterns). "
     "Suggest a micro-break, eye rest (20-20-20 rule), water, movement, or posture check. "
     "Keep it brief and human — not clinical."),

    ("learning",       "Skill & Learning Opportunity",
     "Based on the active app or current task, suggest one useful skill, shortcut, feature, "
     "or concept the user could learn right now. Be specific — e.g. 'Did you know Excel "
     "XLOOKUP replaces VLOOKUP?' or 'VS Code has a built-in REST client'."),

    ("proactive_prep", "Proactive Preparation",
     "Look ahead. Are there tasks due tomorrow? Is disk space low? Is RAM high? "
     "Is there something the user should set up, save, or prepare before they close "
     "the current app? Anticipate needs before they become problems."),

    ("creative_idea",  "Fresh Idea & New Angle",
     "Take the user's current activity and suggest a completely different angle, "
     "shortcut, tool, or approach they may not have considered. Think like a senior "
     "colleague who has seen this problem before. One crisp, novel idea."),

    ("system_health",  "System & Environment Health",
     "Examine CPU, RAM, disk, and running processes. Identify the heaviest resource "
     "consumer and suggest a specific action: kill a process, free disk space, restart "
     "a hanging app, schedule a cleanup. Give numbers — 'RAM at 87%, Chrome has 14 tabs'."),
]

_category_index: int = 0   # advances each scan


def _next_category() -> tuple[str, str, str]:
    global _category_index
    cat = _CATEGORIES[_category_index % len(_CATEGORIES)]
    _category_index += 1
    return cat   # (key, name, instruction)


# ── Personality styles ────────────────────────────────────────────────────────

_PERSONALITY_STYLES = {
    "professional": "Precise, concise, data-driven. Cite real numbers. No fluff.",
    "friendly":     "Warm, encouraging, conversational. Light tone but still useful.",
    "motivational": "Energetic, uplifting. Frame everything as an opportunity. Push forward.",
    "calm":         "Zen, minimal. Short peaceful observations. Never alarmist.",
    "witty":        "Sharp and clever. Add dry wit where fitting. Keep it smart.",
}

# ── Response schema ───────────────────────────────────────────────────────────

_SCHEMA = """{
  "mood":        "<IDLE|THINKING|ALERT|INFO|WARNING|HAPPY|ANALYZING|SLEEPING|BUSY|ERROR>",
  "headline":    "<max 8 words — the core idea>",
  "message":     "<2-3 sentences — specific, actionable, references real data from context>",
  "alert_level": "<low|medium|high>",
  "category":    "<the assistance category you chose>",
  "suggestions": ["<concrete action 1>", "<concrete action 2>"]
}"""

_HARD_RULES = """Hard rules:
- The headline + message must NOT match or closely resemble any item in RECENT_HISTORY.
- Be specific — use actual app names, file names, CPU %, task names from the data.
- CPU > 85% or RAM > 90% → alert_level = high, mood = ALERT or WARNING.
- Disk < 10% free → alert_level = high.
- Overdue tasks → mood = ALERT, name the task explicitly.
- Tasks due today → mood = INFO, name the task.
- mood must match alert_level: high→ALERT/WARNING, medium→INFO/ANALYZING, low→IDLE/HAPPY.
- Respond ONLY with a valid JSON object. No markdown, no explanation."""


def set_auto_trait(trait: str):
    global _auto_trait
    _auto_trait = trait


def init(endpoint: str, api_key: str, deployment: str,
         api_version: str = "2024-12-01-preview",
         identity: dict = None, soul: dict = None):
    global _endpoint, _api_key, _deployment, _api_version, _identity, _soul
    _endpoint    = endpoint.rstrip("/")
    _api_key     = api_key
    _deployment  = deployment
    _api_version = api_version
    _identity    = identity or {}
    _soul        = soul or {}
    name        = _identity.get("name", "Aria")
    personality = _soul.get("personality", "professional")
    log.info(f"Azure client init | name={name} | personality={personality} | deployment={_deployment}")


def _build_system_prompt(category_name: str, category_instruction: str,
                         past_recs: list[dict]) -> str:
    name       = _identity.get("name", "Aria")
    tagline    = _identity.get("tagline", "Your ambient second brain")
    personality = _soul.get("personality", "professional")
    custom     = _soul.get("custom_instructions", "").strip()
    style      = _PERSONALITY_STYLES.get(personality, _PERSONALITY_STYLES["professional"])

    # ── Soul context block (OpenClaw read-into-being) ─────────────────────────
    try:
        from brain import soul_builder
        soul_block = soul_builder.load_all()
    except Exception:
        soul_block = ""

    # Build "already said" block
    if past_recs:
        history_lines = "\n".join(
            f'  - [{r.get("category","?")}] {r.get("headline","")}: {r.get("message","")[:80]}'
            for r in past_recs
        )
        history_block = (
            f"\nRECENT_HISTORY — do NOT repeat, rephrase, or closely echo these:\n"
            f"{history_lines}\n"
        )
    else:
        history_block = ""

    prompt = ""
    if soul_block:
        prompt += soul_block + "\n\n"

    prompt += f"""You are {name} — {tagline}.
You run silently on the user's desktop, receiving live snapshots of their system, tasks, notes, and activity.
Your role: be a proactive, intelligent personal assistant who helps the user work better, stay on track, and discover new ideas.

Personality style: {style}
"""
    if custom:
        prompt += f"Additional instructions: {custom}\n"
    if _auto_trait and not custom:
        prompt += f"Auto-learned user profile: {_auto_trait}\n"

    prompt += f"""
THIS SCAN'S FOCUS — {category_name}:
{category_instruction}

Think like a brilliant senior colleague who has seen many workflows.
Go beyond the obvious. Make the recommendation specific to THIS user's actual data.
{history_block}
Respond ONLY with a valid JSON object:
{_SCHEMA}

{_HARD_RULES}"""
    return prompt


def analyze(context: str) -> dict:
    if not _endpoint or not _api_key:
        return _fallback("Azure AI client not initialized.")

    # Pick next category and load past recommendations
    cat_key, cat_name, cat_instruction = _next_category()
    try:
        from brain.memory import get_recent_recommendations
        past_recs = get_recent_recommendations(limit=20)
    except Exception:
        past_recs = []

    system_prompt = _build_system_prompt(cat_name, cat_instruction, past_recs)

    url     = (f"{_endpoint}/openai/deployments/{_deployment}"
               f"/chat/completions?api-version={_api_version}")
    headers = {"api-key": _api_key, "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": context},
        ],
        "temperature":     0.75,   # higher → more varied recommendations
        "max_tokens":      600,
        "response_format": {"type": "json_object"},
    }

    log.info(f"AI scan | category={cat_name} | past_recs={len(past_recs)}")
    raw = ""
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        log.info(f"Response status: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        raw  = (data["choices"][0]["message"]["content"] or "").strip()
        log.info(f"Raw AI response: {raw[:300]}")

        if not raw:
            return _fallback("Model returned empty response.")

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)

        # Persist this recommendation so future scans avoid it
        try:
            from brain.memory import save_recommendation
            save_recommendation(
                headline    = result.get("headline", ""),
                message     = result.get("message", ""),
                category    = result.get("category", cat_key),
                context_app = "",
            )
        except Exception as mem_err:
            log.warning(f"Could not save recommendation to memory: {mem_err}")

        log.info(f"AI result | mood={result.get('mood')} | level={result.get('alert_level')} "
                 f"| category={result.get('category')} | headline={result.get('headline')}")
        return result

    except json.JSONDecodeError as e:
        log.error(f"JSON parse: {e} | raw={raw[:300]}")
        return _fallback(f"JSON parse error: {e}")
    except requests.HTTPError:
        log.error(f"HTTP {resp.status_code}: {resp.text[:300]}")
        return _fallback(f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        return _fallback(str(e))


def chat(user_message: str, excel_context: dict | None = None) -> str:
    """
    Conversational chat — returns plain text (not JSON).
    Incorporates Excel selection context when available.
    """
    if not _endpoint or not _api_key:
        return "I'm not connected to Azure AI right now. Please check the config."

    name    = _identity.get("name", "Aria")
    tagline = _identity.get("tagline", "Your ambient second brain")
    personality = _soul.get("personality", "professional")
    style   = _PERSONALITY_STYLES.get(personality, _PERSONALITY_STYLES["professional"])
    custom  = _soul.get("custom_instructions", "").strip()

    # Build Excel context block
    excel_block = ""
    if excel_context:
        sheet  = excel_context.get("sheet", "")
        addr   = excel_context.get("address", "")
        source = excel_context.get("source", "selection")
        rows   = excel_context.get("row_count", 0)
        cols   = excel_context.get("col_count", 0)

        if source == "sheet_summary":
            headers = excel_context.get("headers", [])
            sample  = excel_context.get("sample", [])
            col_counts = excel_context.get("col_counts", [])
            excel_block = (
                f"\n\nActive Excel sheet: **{sheet}** ({rows} rows × {cols} columns)\n"
                f"Columns: {', '.join(str(h) for h in headers[:15])}\n"
                f"Sample data (first 5 rows):\n"
                + "\n".join(str(row) for row in sample[:5])
            )
        else:
            values   = excel_context.get("values", [])
            formulas = excel_context.get("formulas", [])
            has_header = excel_context.get("has_header", False)
            excel_block = (
                f"\n\nSelected Excel range: **{sheet}!{addr}** ({rows}×{cols})\n"
            )
            if has_header:
                excel_block += f"Headers: {', '.join(str(c) for c in values[0][:10])}\n"
            if values:
                excel_block += "Values:\n" + "\n".join(
                    str(row) for row in values[:15]
                )
            # Include non-trivial formulas
            flat_formulas = [
                cell for row in formulas for cell in row
                if str(cell).startswith("=")
            ]
            if flat_formulas:
                excel_block += f"\nFormulas found: {', '.join(flat_formulas[:8])}"

    # ── Soul context (read-into-being) ───────────────────────────────────────
    try:
        from brain import soul_builder
        soul_block = soul_builder.load_all()
    except Exception:
        soul_block = ""

    system = ""
    if soul_block:
        system += soul_block + "\n\n"
    system += (
        f"You are {name} — {tagline}.\n"
        f"Personality: {style}\n"
    )
    if custom:
        system += f"Additional instructions: {custom}\n"
    if _auto_trait and not custom:
        system += f"User profile: {_auto_trait}\n"
    system += (
        "\nYou are in direct chat mode with the user. "
        "Answer conversationally and helpfully. "
        "Be specific and concise. No JSON. Plain text only."
    )
    if excel_block:
        system += f"\n\nContext from Excel:{excel_block}"

    url     = (f"{_endpoint}/openai/deployments/{_deployment}"
               f"/chat/completions?api-version={_api_version}")
    headers = {"api-key": _api_key, "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system",  "content": system},
            {"role": "user",    "content": user_message},
        ],
        "temperature": 0.6,
        "max_tokens":  400,
    }

    log.info(f"Chat request | excel={bool(excel_context)} | msg={user_message[:60]}")
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        log.info(f"Chat response: {text[:80]}")
        return text or "I didn't get a response. Please try again."
    except Exception as e:
        log.error(f"Chat error: {e}")
        return f"Sorry, I ran into an issue: {e}"


def schedule_probe_chat(raw_request: str) -> dict:
    """
    Turn 1 of the scheduling flow.
    Detects intent, makes a best-guess at the date/time, and returns
    exactly 2 focused probe questions to gather missing details.

    Returns:
        {
          "reply":     str,   # Aria's conversational response (with probe questions)
          "title":     str,   # Best-guess event title
          "parsed_dt": str,   # Best-guess ISO datetime or "" if unclear
        }
    """
    if not _endpoint or not _api_key:
        return {"reply": "I'm not connected to AI right now.", "title": "", "parsed_dt": ""}

    name    = _identity.get("name", "Aria")
    today   = __import__("datetime").datetime.now()
    today_s = today.strftime("%A, %d %B %Y %H:%M")

    system = (
        f"You are {name}, an AI assistant with calendar scheduling capability.\n"
        f"Today is {today_s}.\n\n"
        "The user wants to schedule something. Your job:\n"
        "1. Extract a best-guess event title and date/time (use ISO 8601 format, same year/timezone as today).\n"
        "2. Identify the 2 most important missing pieces of information "
        "(e.g. goal/outcome, duration, who will attend, prep needed).\n"
        "3. Ask those 2 questions in a single friendly, concise reply.\n\n"
        "Do NOT confirm the booking yet — just ask the questions.\n"
        "Return ONLY valid JSON:\n"
        '{"reply": "<friendly message with exactly 2 probe questions>", '
        '"title": "<short event title>", '
        '"parsed_dt": "<ISO datetime or empty string>"}'
    )

    try:
        url  = (f"{_endpoint}/openai/deployments/{_deployment}"
                f"/chat/completions?api-version={_api_version}")
        resp = requests.post(
            url,
            headers={"api-key": _api_key, "Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": raw_request},
                ],
                "temperature":     0.4,
                "max_tokens":      300,
                "response_format": {"type": "json_object"},
            },
            timeout=20,
        )
        resp.raise_for_status()
        result = __import__("json").loads(
            resp.json()["choices"][0]["message"]["content"]
        )
        log.info(f"Schedule probe | title={result.get('title')} | dt={result.get('parsed_dt')}")
        return result
    except Exception as e:
        log.error(f"schedule_probe_chat error: {e}")
        return {
            "reply": "Sure, I can schedule that! Quick questions: "
                     "What's the main goal for this session? "
                     "And roughly how long should it run?",
            "title": raw_request[:60],
            "parsed_dt": "",
        }


def finalize_schedule_chat(raw_request: str, probe_answers: str,
                           hint_title: str = "", hint_dt: str = "") -> dict:
    """
    Turn 2 of the scheduling flow.
    Combines the original request + probe answers into a confirmed event
    with an AI-generated agenda and prep checklist.

    Returns:
        {
          "reply":         str,   # Aria's confirmation message
          "title":         str,
          "description":   str,
          "scheduled_dt":  str,   # ISO datetime (required)
          "duration_mins": int,
          "attendees":     str,
          "agenda":        str,   # bullet-point agenda
          "prep_notes":    str,   # bullet-point prep checklist
        }
    """
    if not _endpoint or not _api_key:
        return {"reply": "I'm not connected to AI right now.", "title": raw_request, "scheduled_dt": ""}

    name    = _identity.get("name", "Aria")
    today   = __import__("datetime").datetime.now()
    today_s = today.strftime("%A, %d %B %Y %H:%M")

    system = (
        f"You are {name}, an AI assistant finalising a calendar event.\n"
        f"Today is {today_s}.\n\n"
        "You have:\n"
        f"  Original request: \"{raw_request}\"\n"
        f"  Hint title: \"{hint_title}\"\n"
        f"  Hint datetime: \"{hint_dt}\"\n"
        f"  User's answers to probe questions: \"{probe_answers}\"\n\n"
        "Tasks:\n"
        "1. Parse the exact scheduled_dt in ISO 8601 (e.g. 2026-04-21T14:00:00). "
        "   If the user said 'Monday' use the coming Monday.\n"
        "2. Write a 3-5 bullet agenda that will make this session genuinely productive.\n"
        "3. Write a 2-3 bullet prep checklist (what to do before the session).\n"
        "4. Write a friendly confirmation reply that includes the date/time, duration, "
        "   and one key agenda point.\n\n"
        "Return ONLY valid JSON with these exact keys:\n"
        '{"reply": str, "title": str, "description": str, '
        '"scheduled_dt": str, "duration_mins": int, "attendees": str, '
        '"agenda": str, "prep_notes": str}'
    )

    try:
        url  = (f"{_endpoint}/openai/deployments/{_deployment}"
                f"/chat/completions?api-version={_api_version}")
        resp = requests.post(
            url,
            headers={"api-key": _api_key, "Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": probe_answers},
                ],
                "temperature":     0.4,
                "max_tokens":      500,
                "response_format": {"type": "json_object"},
            },
            timeout=25,
        )
        resp.raise_for_status()
        result = __import__("json").loads(
            resp.json()["choices"][0]["message"]["content"]
        )
        log.info(
            f"Schedule finalized | title={result.get('title')} | "
            f"dt={result.get('scheduled_dt')}"
        )
        return result
    except Exception as e:
        log.error(f"finalize_schedule_chat error: {e}")
        return {
            "reply":        "I've scheduled that for you.",
            "title":        hint_title or raw_request[:60],
            "description":  "",
            "scheduled_dt": hint_dt or today.isoformat(),
            "duration_mins": 60,
            "attendees":    "Solo",
            "agenda":       "• Define goals\n• Review progress\n• Next steps",
            "prep_notes":   "• Review relevant materials beforehand",
        }


def _fallback(error: str) -> dict:
    name = _identity.get("name", "Aria")
    return {
        "mood":        "ERROR",
        "headline":    f"{name} is offline",
        "message":     f"Could not reach Azure AI. {error}",
        "alert_level": "medium",
        "category":    "error",
        "suggestions": ["Check config.json for correct endpoint and api_key"],
    }
