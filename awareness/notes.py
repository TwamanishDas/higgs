import os
import re
from datetime import datetime
from dataclasses import dataclass, field

_MAX_FILE_CHARS = 2000  # max chars to read per note for AI context


@dataclass
class VaultFile:
    path: str
    name: str
    modified: datetime
    content: str
    frontmatter: dict = field(default_factory=dict)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    fm = {}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            block = text[3:end].strip()
            body = text[end + 3:].strip()
            for line in block.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip()
            return fm, body
    return fm, text


def get_recent_files(vault_path: str, n: int = 10) -> list[VaultFile]:
    if not vault_path or not os.path.isdir(vault_path):
        return []

    files = []
    for root, _, filenames in os.walk(vault_path):
        # Skip obsidian hidden folder
        if ".obsidian" in root:
            continue
        for fname in filenames:
            if fname.endswith(".md"):
                full = os.path.join(root, fname)
                try:
                    mtime = os.path.getmtime(full)
                    files.append((mtime, full, fname))
                except OSError:
                    pass

    files.sort(reverse=True)
    result = []
    for mtime, path, name in files[:n]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
            fm, body = _parse_frontmatter(raw)
            result.append(VaultFile(
                path=path,
                name=name.replace(".md", ""),
                modified=datetime.fromtimestamp(mtime),
                content=body[:_MAX_FILE_CHARS],
                frontmatter=fm,
            ))
        except Exception:
            pass
    return result


def get_daily_note(vault_path: str) -> VaultFile | None:
    today = datetime.now().strftime("%Y-%m-%d")
    if not vault_path or not os.path.isdir(vault_path):
        return None

    for root, _, filenames in os.walk(vault_path):
        if ".obsidian" in root:
            continue
        for fname in filenames:
            if fname == f"{today}.md":
                path = os.path.join(root, fname)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        raw = f.read()
                    fm, body = _parse_frontmatter(raw)
                    return VaultFile(
                        path=path,
                        name=fname.replace(".md", ""),
                        modified=datetime.fromtimestamp(os.path.getmtime(path)),
                        content=body[:_MAX_FILE_CHARS],
                        frontmatter=fm,
                    )
                except Exception:
                    pass
    return None


def build_notes_context(vault_path: str, max_files: int = 8) -> str:
    if not vault_path or not os.path.isdir(vault_path):
        return "No vault path configured or folder not found."

    lines = []

    daily = get_daily_note(vault_path)
    if daily:
        lines.append(f"### Today's Daily Note ({daily.name})\n{daily.content}")

    recent = get_recent_files(vault_path, max_files)
    for f in recent:
        if daily and f.path == daily.path:
            continue
        lines.append(f"### {f.name} (modified {f.modified.strftime('%Y-%m-%d %H:%M')})\n{f.content}")

    return "\n\n".join(lines) if lines else "No notes found in vault."
