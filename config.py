import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_FILE = os.path.join(_DIR, "config.json")

_DEFAULTS = {
    "azure": {
        "endpoint": "",
        "api_key": "",
        "model": "gpt-4o",
        "deployment": "gpt-4o",
        "api_version": "2024-12-01-preview"
    },
    "widget": {
        "start_x": 1200,
        "start_y": 100,
        "size": 110,
        "opacity": 0.95
    },
    "character": {
        "type": "orb",
        "pokemon_id": 25,
        "shiny": False
    },
    "identity": {
        "name": "Aria",
        "tagline": "Your ambient second brain",
        "accent_color": "#4a9eff"
    },
    "soul": {
        "personality": "professional",
        "custom_instructions": "",
        "auto_evolve": True
    },
    "skills": {
        "system_monitor": True,
        "window_tracker": True,
        "calendar":       True,
        "obsidian_notes": True,
        "ai_brain":       True,
        "context_help":   True,
        "memory":         True,
        "office_reader":  True,   # COM: reads Excel/Word/PPT content automatically
        "browser_reader": False   # CDP: reads browser tab (needs --remote-debugging-port=9222)
    },
    "awareness": {
        "scan_interval_seconds": 30,
        "track_windows": True,
        "track_system": True,
        "track_processes": True,
        "max_processes": 10
    },
    "vault": {
        "path": "",
        "max_context_files": 8,
        "reminder_check_seconds": 60,
        "reminder_minutes_before": 15
    },
    "notifications": {
        "scan_cooldown_seconds": 300,
        "reminder_cooldown_seconds": 3600,
        "display_duration_seconds": 8
    },
    "tone": {
        "style":        "default",
        "blend_style":  "",
        "blend_weight": 30,
        "temperature":  70
    }
}


def load() -> dict:
    if os.path.exists(_CONFIG_FILE):
        with open(_CONFIG_FILE, "r") as f:
            data = json.load(f)
        merged = _DEFAULTS.copy()
        for k, v in data.items():
            if isinstance(v, dict):
                merged[k] = {**_DEFAULTS.get(k, {}), **v}
            else:
                merged[k] = v
        return merged
    return _DEFAULTS.copy()


def save(cfg: dict):
    with open(_CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
