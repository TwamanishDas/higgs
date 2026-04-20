"""
Analyzes memory observations to detect usage patterns, auto-build soul
traits, and generate daily summaries. Runs as background tasks.
"""
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from brain import memory
from logger import log


def analyze_patterns():
    """Detect usage patterns from the last 7 days of observations."""
    observations = memory.get_recent_observations(days=7)
    if len(observations) < 5:
        log.info("Pattern analysis skipped — not enough observations yet")
        return

    # App usage
    app_counts = Counter(
        o["active_app"].lower().replace(".exe", "")
        for o in observations if o["active_app"]
    )
    if app_counts:
        top_app = app_counts.most_common(1)[0][0]
        memory.upsert_pattern("app_usage", "most_used", top_app, 0.6)

        all_apps = " ".join(app_counts.keys())
        dev_signals = {"code", "devenv", "pycharm", "sublime", "notepad++", "git", "cmd", "powershell", "python"}
        office_signals = {"winword", "excel", "powerpnt", "onenote"}
        creative_signals = {"photoshop", "illustrator", "premiere", "blender", "figma", "canva"}

        if any(s in all_apps for s in dev_signals):
            memory.upsert_pattern("work_type", "primary", "developer/technical")
        elif any(s in all_apps for s in office_signals):
            memory.upsert_pattern("work_type", "primary", "office/knowledge-worker")
        elif any(s in all_apps for s in creative_signals):
            memory.upsert_pattern("work_type", "primary", "creative/design")
        else:
            memory.upsert_pattern("work_type", "primary", "general user", 0.3)

    # Time-of-day peak
    hour_activity: dict[int, int] = defaultdict(int)
    for o in observations:
        try:
            hour = datetime.fromisoformat(o["ts"]).hour
            hour_activity[hour] += 1
        except Exception:
            pass

    if hour_activity:
        peak = max(hour_activity, key=hour_activity.get)
        if 5 <= peak < 12:
            label = "morning worker"
        elif 12 <= peak < 18:
            label = "afternoon worker"
        else:
            label = "evening/night worker"
        memory.upsert_pattern("work_schedule", "peak_time", label)

    # Dominant mood
    mood_counts = Counter(o["mood"] for o in observations if o["mood"])
    if mood_counts:
        memory.upsert_pattern(
            "mood_history", "dominant_mood",
            mood_counts.most_common(1)[0][0]
        )

    log.info(
        f"Pattern analysis done | {len(observations)} obs | "
        f"top_app={app_counts.most_common(1)[0][0] if app_counts else 'n/a'}"
    )


def build_auto_soul(cfg: dict) -> dict:
    """
    Derive personality hints from patterns when user hasn't set custom soul.
    Returns a dict of auto-derived soul overrides (empty if user has configured soul).
    """
    soul_cfg = cfg.get("soul", {})
    if soul_cfg.get("custom_instructions", "").strip():
        return {}  # User has manual instructions — don't override

    patterns = {p["pattern_key"]: p["pattern_value"] for p in memory.get_patterns()}
    if not patterns:
        return {}

    work_type = patterns.get("primary", "")
    schedule  = patterns.get("peak_time", "")
    mood      = patterns.get("dominant_mood", "IDLE")

    if "developer" in work_type:
        auto_personality = "professional"
        trait = "technical and precise, references code and system details naturally"
    elif "office" in work_type:
        auto_personality = "professional"
        trait = "organized, task-oriented, focused on deadlines and deliverables"
    elif "creative" in work_type:
        auto_personality = "friendly"
        trait = "creative and expressive, appreciates visual and innovative thinking"
    else:
        auto_personality = "friendly"
        trait = "adaptable and curious, meets the user where they are"

    if mood in ("ALERT", "ERROR", "WARNING"):
        trait += "; vigilant and proactive about issues"
    elif mood == "HAPPY":
        trait += "; enthusiastic and encouraging"

    memory.save_soul_trait("work_style", work_type or "general",
                           "inferred from app usage patterns")
    memory.save_soul_trait("schedule", schedule or "flexible",
                           "inferred from activity timestamps")
    memory.save_soul_trait("personality_hint", trait,
                           "auto-derived from patterns")

    log.info(f"Auto soul built | personality={auto_personality} | trait={trait[:60]}")
    return {"personality": auto_personality, "_auto_trait": trait}


def generate_daily_summary(cfg: dict):
    """
    Summarize today's observations into a single daily_summaries record.
    Uses AI if available; falls back to a stat-based summary.
    Called once per day (idempotent — skipped if today already summarized).
    """
    observations = memory.get_today_observations()
    if len(observations) < 3:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    existing = memory.get_daily_summaries(1)
    if existing and existing[0]["date"] == today:
        return  # Already summarized today

    app_counts  = Counter(o["active_app"] for o in observations if o["active_app"])
    mood_counts = Counter(o["mood"]       for o in observations if o["mood"])
    dominant_mood = mood_counts.most_common(1)[0][0] if mood_counts else "IDLE"
    key_apps      = [a for a, _ in app_counts.most_common(5)]

    # Try AI summary
    summary_text = _ai_summary(observations, key_apps, cfg)

    memory.save_daily_summary(today, summary_text, key_apps,
                              len(observations), dominant_mood)
    memory.archive_old_observations(keep_days=30)
    log.info(f"Daily summary saved for {today} | scans={len(observations)}")

    # ── Soul evolution (OpenClaw) — rewrites soul.md, procedures.md, salience.md
    try:
        from brain import soul_builder
        if soul_builder.is_seeded():
            all_obs  = memory.get_recent_observations(days=1)
            patterns = memory.get_patterns()
            soul_builder.evolve(all_obs, patterns, cfg)
    except Exception as e:
        log.warning(f"Soul evolution skipped: {e}")


def _ai_summary(observations: list, key_apps: list, cfg: dict) -> str:
    """Call Azure AI to generate a natural-language day summary."""
    try:
        from brain import azure_client
        if not azure_client._endpoint:
            raise RuntimeError("Azure client not initialized")

        lines = [
            f"[{o['ts'][:16]}] App:{o['active_app']} Mood:{o['mood']} - {o['headline']}"
            for o in observations[-20:]
        ]
        prompt = (
            "Summarize this user's day in 1-2 sentences based on their desktop activity.\n"
            f"Activity log:\n" + "\n".join(lines) +
            f"\nTop apps: {', '.join(key_apps[:4])}\n\n"
            "Respond in plain text — no JSON, no bullet points. Just 1-2 sentences."
        )

        # Use a raw analyze call but expect plain text (response_format not json here)
        url = (
            f"{azure_client._endpoint}/openai/deployments/"
            f"{azure_client._deployment}/chat/completions"
            f"?api-version={azure_client._api_version}"
        )
        import requests as _requests
        resp = _requests.post(
            url,
            headers={"api-key": azure_client._api_key, "Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": "You are a concise daily activity summarizer."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 120,
            },
            timeout=20,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text or _stat_summary(observations, key_apps)
    except Exception as e:
        log.warning(f"AI daily summary failed, using stat summary: {e}")
        return _stat_summary(observations, key_apps)


def _stat_summary(observations: list, key_apps: list) -> str:
    n = len(observations)
    apps = ", ".join(key_apps[:3]) if key_apps else "various apps"
    return f"Active day with {n} monitored snapshots. Primary apps: {apps}."
