import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log
from awareness import system as sys_awareness
from awareness import windows as win_awareness
from awareness import apps as app_awareness
from awareness import notes as notes_awareness
from awareness import tasks as tasks_awareness
from brain import memory


def build_context(cfg: dict) -> str:
    parts = []

    if cfg["awareness"]["track_system"]:
        metrics = sys_awareness.get_metrics()
        procs = sys_awareness.get_top_processes(cfg["awareness"]["max_processes"])
        log.info(f"System metrics | CPU={metrics['cpu_percent']}% RAM={metrics['ram_percent']}% Disk={metrics['disk_percent']}%")
        parts.append(f"## System Metrics\n{json.dumps(metrics, indent=2)}")
        parts.append(f"## Top Processes (by CPU)\n{json.dumps(procs, indent=2)}")

    if cfg["awareness"]["track_windows"]:
        active = win_awareness.get_active_window()
        history = win_awareness.get_window_history()
        open_wins = win_awareness.get_open_windows()
        log.info(f"Active window | title={active.get('title')} process={active.get('process')}")
        parts.append(f"## Active Window\n{json.dumps(active, indent=2)}")
        parts.append(f"## Recent Window History\n{json.dumps(history, indent=2)}")
        parts.append(f"## Open Windows (sample)\n{json.dumps(open_wins[:10], indent=2)}")

    if cfg["awareness"]["track_processes"]:
        installed = app_awareness.get_installed_apps()
        log.info(f"Installed apps count: {len(installed)}")
        parts.append(f"## Installed Apps Count\n{len(installed)} apps installed")

    vault_path = cfg.get("vault", {}).get("path", "")
    if vault_path:
        max_files = cfg["vault"].get("max_context_files", 8)

        task_ctx = tasks_awareness.build_tasks_context(vault_path)
        log.info(f"Tasks context built | vault={vault_path}")
        parts.append(f"## Obsidian Tasks\n{task_ctx}")

        notes_ctx = notes_awareness.build_notes_context(vault_path, max_files)
        log.info(f"Notes context built | files={max_files}")
        parts.append(f"## Obsidian Notes (recent)\n{notes_ctx}")

    # Memory context — learned patterns and past summaries
    mem_ctx = memory.build_memory_context(days=7)
    if mem_ctx:
        log.info("Memory context included in scan")
        parts.append(mem_ctx)

    return "\n\n".join(parts)
