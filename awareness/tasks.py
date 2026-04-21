import os
import re
from datetime import datetime, date, timedelta
from dataclasses import dataclass

# Obsidian Tasks plugin due date emoji formats
_DUE_PATTERNS = [
    re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})"),       # 📅 2026-04-18
    re.compile(r"⏰\s*(\d{4}-\d{2}-\d{2})"),         # ⏰ 2026-04-18
    re.compile(r"\[due::\s*(\d{4}-\d{2}-\d{2})\]"),  # Dataview [due:: 2026-04-18]
    re.compile(r"\(due:\s*(\d{4}-\d{2}-\d{2})\)"),   # (due: 2026-04-18)
    re.compile(r"due:\s*(\d{4}-\d{2}-\d{2})"),        # due: 2026-04-18
]

_TASK_LINE = re.compile(r"^[\s>]*- \[([ x])\]\s+(.+)$", re.MULTILINE)


@dataclass
class Task:
    title: str
    completed: bool
    due: date | None
    source_file: str
    source_name: str
    line_number: int

    @property
    def is_overdue(self) -> bool:
        return self.due is not None and self.due < date.today() and not self.completed

    @property
    def is_today(self) -> bool:
        return self.due is not None and self.due == date.today() and not self.completed

    @property
    def is_upcoming(self) -> bool:
        if self.due is None or self.completed:
            return False
        return date.today() < self.due <= date.today() + timedelta(days=7)

    @property
    def due_label(self) -> str:
        if self.due is None:
            return "No date"
        if self.is_overdue:
            delta = (date.today() - self.due).days
            return f"Overdue {delta}d"
        if self.is_today:
            return "Today"
        if self.is_upcoming:
            delta = (self.due - date.today()).days
            return f"In {delta}d"
        return self.due.strftime("%Y-%m-%d")


def _parse_due(text: str) -> date | None:
    for pattern in _DUE_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                return datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except ValueError:
                pass
    return None


def _clean_title(text: str) -> str:
    for pattern in _DUE_PATTERNS:
        text = pattern.sub("", text)
    text = re.sub(r"[📅⏰🛫✅🔁🔺⏫🔼🔽⬇️]", "", text)
    return text.strip()


def scan_vault_tasks(vault_path: str) -> list[Task]:
    if not vault_path or not os.path.isdir(vault_path):
        return []

    tasks = []
    for root, _, filenames in os.walk(vault_path):
        if ".obsidian" in root:
            continue
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for i, line in enumerate(content.splitlines(), 1):
                    m = _TASK_LINE.match(line)
                    if m:
                        completed = m.group(1).lower() == "x"
                        raw_title = m.group(2)
                        due = _parse_due(raw_title)
                        title = _clean_title(raw_title)
                        tasks.append(Task(
                            title=title,
                            completed=completed,
                            due=due,
                            source_file=path,
                            source_name=fname.replace(".md", ""),
                            line_number=i,
                        ))
            except Exception:
                pass
    return tasks


def get_due_today(vault_path: str) -> list[Task]:
    return [t for t in scan_vault_tasks(vault_path) if t.is_today]


def get_overdue(vault_path: str) -> list[Task]:
    return [t for t in scan_vault_tasks(vault_path) if t.is_overdue]


def get_upcoming(vault_path: str, days: int = 7) -> list[Task]:
    return [t for t in scan_vault_tasks(vault_path) if t.is_upcoming]


def mark_complete_in_file(task: Task) -> bool:
    try:
        with open(task.source_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        line = lines[task.line_number - 1]
        lines[task.line_number - 1] = line.replace("- [ ]", f"- [x]", 1)
        today = datetime.now().strftime("%Y-%m-%d")
        lines[task.line_number - 1] = lines[task.line_number - 1].rstrip("\n") + f" ✅ {today}\n"
        with open(task.source_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True
    except Exception:
        return False


def append_task_to_vault(vault_path: str, title: str, due: date | None = None) -> bool:
    widget_tasks_file = os.path.join(vault_path, "Widget Tasks.md")
    try:
        due_str = f" 📅 {due.strftime('%Y-%m-%d')}" if due else ""
        line = f"- [ ] {title}{due_str}\n"
        with open(widget_tasks_file, "a", encoding="utf-8") as f:
            f.write(line)
        return True
    except Exception:
        return False


def build_tasks_context(vault_path: str) -> str:
    all_tasks = scan_vault_tasks(vault_path)
    if not all_tasks:
        return "No tasks found in vault."

    overdue = [t for t in all_tasks if t.is_overdue]
    today = [t for t in all_tasks if t.is_today]
    upcoming = [t for t in all_tasks if t.is_upcoming]

    lines = []
    if overdue:
        lines.append(f"OVERDUE ({len(overdue)}):")
        for t in overdue[:5]:
            lines.append(f"  - {t.title} (due {t.due}, from {t.source_name})")
    if today:
        lines.append(f"DUE TODAY ({len(today)}):")
        for t in today:
            lines.append(f"  - {t.title} (from {t.source_name})")
    if upcoming:
        lines.append(f"UPCOMING 7 DAYS ({len(upcoming)}):")
        for t in upcoming[:5]:
            lines.append(f"  - {t.title} (due {t.due}, from {t.source_name})")

    pending_no_date = [t for t in all_tasks if not t.completed and t.due is None]
    if pending_no_date:
        lines.append(f"PENDING (no date) — {len(pending_no_date)} tasks")

    return "\n".join(lines) if lines else "All tasks completed — nothing pending."
