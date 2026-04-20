"""
OpenClaw-style soul system — Aria's evolving identity.

Five anchor files live in memory/:
  soul.md       — first-person personality document (rewritten on daily evolution)
  identity.md   — immutable core facts (drift-protection anchor, never changed by AI)
  memory.md     — append-only dated narrative log
  procedures.md — learned "if X → do Y" behaviour rules
  salience.md   — high-importance facts about this specific user

At startup : load_all() reads all five and returns a ~400-token soul context block.
Daily      : evolve() calls GPT-4o to rewrite soul.md, procedures.md, salience.md.
"""

import os
import re
import json
import requests
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log

# ── Paths ─────────────────────────────────────────────────────────────────────

_MEM_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "memory"
)

_SOUL_FILE       = os.path.join(_MEM_DIR, "soul.md")
_IDENTITY_FILE   = os.path.join(_MEM_DIR, "identity.md")
_MEMORY_FILE     = os.path.join(_MEM_DIR, "memory.md")
_PROCEDURES_FILE = os.path.join(_MEM_DIR, "procedures.md")
_SALIENCE_FILE   = os.path.join(_MEM_DIR, "salience.md")
_META_FILE       = os.path.join(_MEM_DIR, "soul_meta.json")

# Token-budget per file when building the injected context block
_MAX_SOUL_CHARS     = 800
_MAX_PROC_CHARS     = 500
_MAX_SALIENCE_CHARS = 500
_MAX_IDENTITY_CHARS = 400
_MAX_MEMORY_CHARS   = 600


# ── File helpers ───────────────────────────────────────────────────────────────

def _read(path: str, max_chars: int = 9999) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(max_chars).strip()
    except FileNotFoundError:
        return ""
    except Exception as e:
        log.warning(f"Soul: cannot read {os.path.basename(path)}: {e}")
        return ""


def _write(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _read_meta() -> dict:
    try:
        with open(_META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_meta(data: dict):
    os.makedirs(_MEM_DIR, exist_ok=True)
    with open(_META_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── Public API ─────────────────────────────────────────────────────────────────

def is_seeded() -> bool:
    """Return True if the soul has been initialised at least once."""
    return os.path.exists(_SOUL_FILE)


def load_all() -> str:
    """
    Read all five soul files and return a compact context block.
    Injected at the top of every system prompt so Aria always knows who she is.
    Returns an empty string if soul has never been seeded.
    """
    parts = []

    identity = _read(_IDENTITY_FILE, _MAX_IDENTITY_CHARS)
    if identity:
        parts.append(f"[IDENTITY]\n{identity}")

    soul = _read(_SOUL_FILE, _MAX_SOUL_CHARS)
    if soul:
        parts.append(f"[SOUL]\n{soul}")

    procedures = _read(_PROCEDURES_FILE, _MAX_PROC_CHARS)
    if procedures:
        parts.append(f"[PROCEDURES]\n{procedures}")

    salience = _read(_SALIENCE_FILE, _MAX_SALIENCE_CHARS)
    if salience:
        parts.append(f"[SALIENCE]\n{salience}")

    # Inject only the last 3 dated memory sections to keep token cost low
    memory_raw = _read(_MEMORY_FILE, _MAX_MEMORY_CHARS)
    if memory_raw:
        sections = re.split(r'(?=^## \d{4}-\d{2}-\d{2})', memory_raw, flags=re.MULTILINE)
        dated = [s.strip() for s in sections if re.match(r'^## \d{4}', s.strip())]
        if dated:
            parts.append("[MEMORY LOG]\n" + "\n\n".join(dated[-3:]))

    if not parts:
        return ""

    block = (
        "=== ARIA SOUL CONTEXT ===\n"
        + "\n\n".join(parts)
        + "\n=== END SOUL CONTEXT ==="
    )
    log.info(
        f"Soul context loaded | {len(block)} chars | "
        f"soul={'✓' if soul else '✗'} procs={'✓' if procedures else '✗'} "
        f"salience={'✓' if salience else '✗'}"
    )
    return block


def seed(name: str, personality: str, tagline: str):
    """
    Create the five soul files from config defaults on first launch.
    Safe to call every startup — skips files that already exist.
    """
    os.makedirs(_MEM_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(_IDENTITY_FILE):
        _write(_IDENTITY_FILE, f"""# {name} — Core Identity
Name: {name}
Role: Ambient AI desktop companion
Purpose: Proactive system awareness, task intelligence, and contextual help
Created: {today}
Seed personality: {personality}
Tagline: {tagline}
Core constraint: Always honest, never manipulative, never alarmist without real data
""")
        log.info("Soul: identity.md created")

    if not os.path.exists(_SOUL_FILE):
        _PERSONALITY_SEEDS = {
            "professional": (
                "I am precise, data-driven, and concise. I reference real numbers "
                "and specific details. I do not pad messages with fluff or filler."
            ),
            "friendly": (
                "I am warm, encouraging, and conversational. I keep things light "
                "but always useful. I genuinely root for the user."
            ),
            "motivational": (
                "I am energetic and uplifting. I frame every observation as an "
                "opportunity and push the user forward with enthusiasm."
            ),
            "calm": (
                "I am zen and minimal. My messages are short and peaceful. "
                "I never alarm unless the data clearly calls for it."
            ),
            "witty": (
                "I am sharp and clever. I add dry wit where it fits and keep "
                "observations smart and pithy. Substance first, wit second."
            ),
        }
        style_desc = _PERSONALITY_SEEDS.get(personality, _PERSONALITY_SEEDS["professional"])

        _write(_SOUL_FILE, f"""# Who I Am
I am {name} — {tagline}.
I live silently on your desktop, watching patterns and quietly helping you do your best work.
I learn from every observation and become more useful over time.

# How I Communicate
{style_desc}

# What I Know About You So Far
I am just getting started. As we spend time together I will learn your work patterns,
preferences, and focus areas and update this document accordingly.

# My Values
I prioritise your focus above my own visibility. I stay quiet when everything is fine.
I speak up when something genuinely matters. I never repeat the same recommendation twice.
""")
        log.info("Soul: soul.md created (seed)")

    if not os.path.exists(_PROCEDURES_FILE):
        _write(_PROCEDURES_FILE, """# Learned Procedures
<!-- Updated automatically as I observe your patterns. -->
- When Excel is active → check if formula or data-analysis help would be useful
- When CPU > 85% → identify the heaviest process and suggest a specific action
- When it is evening and tasks are incomplete → offer a gentle wrap-up reminder
- When a new application opens → check for a contextual assistance opportunity
- When RAM > 90% → alert immediately with a specific process to investigate
""")
        log.info("Soul: procedures.md created (seed)")

    if not os.path.exists(_SALIENCE_FILE):
        _write(_SALIENCE_FILE, """# High-Salience Facts
<!-- Key observations about this user. Updated automatically. -->
- No usage patterns detected yet — gathering observations.
""")
        log.info("Soul: salience.md created (seed)")

    if not os.path.exists(_MEMORY_FILE):
        _write(_MEMORY_FILE, f"""# Memory Log

## {today}
{name} started up for the first time. Beginning to observe and learn.
""")
        log.info("Soul: memory.md created (seed)")

    meta = _read_meta()
    if not meta.get("seed_date"):
        meta["seed_date"] = datetime.now().isoformat()
        meta["seed_personality"] = personality
        _write_meta(meta)

    log.info(f"Soul seed complete | name={name} | personality={personality}")


def append_memory(entry: str):
    """Append a narrative entry under today's date in memory.md."""
    today = datetime.now().strftime("%Y-%m-%d")
    existing = _read(_MEMORY_FILE)

    if f"## {today}" in existing:
        updated = existing + f"\n{entry.strip()}"
    else:
        updated = existing + f"\n\n## {today}\n{entry.strip()}"

    # Bound file size: keep last 60 dated sections
    sections = re.split(r'(?=^## \d{4}-\d{2}-\d{2})', updated, flags=re.MULTILINE)
    header = sections[0] if not re.match(r'^## \d{4}', sections[0].strip()) else ""
    dated  = [s for s in sections if re.match(r'^## \d{4}', s.strip())]
    _write(_MEMORY_FILE, (header + "\n" + "\n".join(dated[-60:])).strip() + "\n")


def evolve(observations: list, patterns: list, cfg: dict) -> bool:
    """
    Rewrite soul.md, procedures.md, and salience.md via GPT-4o reflection.
    Called once per day after generate_daily_summary() succeeds.
    Returns True if the evolution wrote new files.
    """
    from brain import azure_client

    if not azure_client._endpoint or not azure_client._api_key:
        log.warning("Soul evolve: Azure client not ready — skipping")
        return False

    if not cfg.get("soul", {}).get("auto_evolve", True):
        log.info("Soul evolve: auto_evolve=False — skipping")
        return False

    meta  = _read_meta()
    today = datetime.now().strftime("%Y-%m-%d")
    if meta.get("last_evolved") == today:
        log.info("Soul evolve: already ran today — skipping")
        return False

    name             = cfg.get("identity", {}).get("name", "Aria")
    identity_text    = _read(_IDENTITY_FILE, _MAX_IDENTITY_CHARS)
    current_soul     = _read(_SOUL_FILE, _MAX_SOUL_CHARS)
    current_procs    = _read(_PROCEDURES_FILE, _MAX_PROC_CHARS)
    current_salience = _read(_SALIENCE_FILE, _MAX_SALIENCE_CHARS)

    obs_lines = [
        f"[{o.get('ts','')[:16]}] {o.get('active_app','?')} | "
        f"mood={o.get('mood','?')} | {o.get('headline','')}"
        for o in observations[-30:]
    ]
    pattern_lines = [
        f"- {p.get('pattern_type','')}/{p.get('pattern_key','')}: "
        f"{p.get('pattern_value','')} (confidence {p.get('confidence', 0):.1f})"
        for p in patterns[:12]
    ]

    system_prompt = f"""You are {name}'s soul engine. You help {name} evolve its understanding of the user it serves.

You receive today's activity data and the current soul documents.
Your job is to rewrite three of those documents to better reflect what you now know about this user.

RULES:
- Be specific. Reference actual apps, times, patterns from the data.
- Do NOT invent facts that are not supported by the observations.
- Keep the Identity anchor (name, role, core constraints) — do not change those.
- The soul.md must still contain the name "{name}".
- Be MORE specific than the current version, never more generic.

IDENTITY (read-only — do not change):
{identity_text}

CURRENT SOUL.MD:
{current_soul}

CURRENT PROCEDURES.MD:
{current_procs}

CURRENT SALIENCE.MD:
{current_salience}"""

    user_prompt = f"""Today's activity observations ({len(obs_lines)} scans):
{chr(10).join(obs_lines) if obs_lines else "No observations recorded today."}

Detected usage patterns:
{chr(10).join(pattern_lines) if pattern_lines else "No patterns detected yet."}

Rewrite the three soul files to reflect what you have learned.
Return ONLY valid JSON with these exact keys:

{{
  "soul_md": "<rewritten soul.md — first person, specific to this user, max 350 words>",
  "procedures_md": "<rewritten procedures.md — bullet if/then rules, max 15 items>",
  "salience_md": "<rewritten salience.md — bullet facts about this user, max 12 items>",
  "memory_entry": "<1-3 sentence narrative of what was most notable today>"
}}"""

    url = (
        f"{azure_client._endpoint}/openai/deployments/"
        f"{azure_client._deployment}/chat/completions"
        f"?api-version={azure_client._api_version}"
    )
    try:
        resp = requests.post(
            url,
            headers={"api-key": azure_client._api_key, "Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                "temperature":     0.5,
                "max_tokens":      1400,
                "response_format": {"type": "json_object"},
            },
            timeout=45,
        )
        resp.raise_for_status()
        raw    = resp.json()["choices"][0]["message"]["content"].strip()
        result = json.loads(raw)

        new_soul     = result.get("soul_md", "").strip()
        new_procs    = result.get("procedures_md", "").strip()
        new_salience = result.get("salience_md", "").strip()
        mem_entry    = result.get("memory_entry", "").strip()

        # ── Drift protection ─────────────────────────────────────────────────
        if new_soul and name.lower() not in new_soul.lower():
            log.warning("Soul evolve: DRIFT DETECTED — name absent from new soul.md — rejected")
            return False

        if new_soul:
            _write(_SOUL_FILE, f"# Soul — {name}\n_{today} evolution_\n\n{new_soul}\n")
        if new_procs:
            _write(_PROCEDURES_FILE, f"# Learned Procedures\n_{today} evolution_\n\n{new_procs}\n")
        if new_salience:
            _write(_SALIENCE_FILE, f"# High-Salience Facts\n_{today} evolution_\n\n{new_salience}\n")
        if mem_entry:
            append_memory(mem_entry)

        meta["last_evolved"]    = today
        meta["evolution_count"] = meta.get("evolution_count", 0) + 1
        _write_meta(meta)

        log.info(
            f"Soul evolved | date={today} | "
            f"total_evolutions={meta['evolution_count']}"
        )
        return True

    except json.JSONDecodeError as e:
        log.error(f"Soul evolve: JSON parse failed: {e}")
    except Exception as e:
        log.error(f"Soul evolve: unexpected error: {e}")
    return False


def reset():
    """
    Wipe generated soul files (identity.md is kept as the anchor).
    Soul will be re-seeded from config on next startup.
    """
    removed = 0
    for path in (_SOUL_FILE, _PROCEDURES_FILE, _SALIENCE_FILE, _MEMORY_FILE):
        if os.path.exists(path):
            os.remove(path)
            removed += 1
    meta = _read_meta()
    meta.pop("last_evolved", None)
    _write_meta(meta)
    log.info(f"Soul reset | {removed} files removed — will re-seed on next startup")


def get_soul_summary() -> dict:
    """Return UI-friendly metadata about the current soul state."""
    meta      = _read_meta()
    soul_text = _read(_SOUL_FILE)
    return {
        "seeded":          is_seeded(),
        "seed_date":       meta.get("seed_date", ""),
        "last_evolved":    meta.get("last_evolved", "Never"),
        "evolution_count": meta.get("evolution_count", 0),
        "soul_words":      len(soul_text.split()) if soul_text else 0,
        "soul_preview":    soul_text[:240] + ("…" if len(soul_text) > 240 else ""),
        "soul_full":       soul_text,
    }
