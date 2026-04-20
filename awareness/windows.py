import ctypes
import ctypes.wintypes
import win32gui
import win32process
import win32con
import psutil
from collections import deque

_window_history: deque = deque(maxlen=10)
_last_title: str = ""


def get_active_window() -> dict:
    global _last_title
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        process_name = "unknown"
        try:
            proc = psutil.Process(pid)
            process_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        if title and title != _last_title:
            _last_title = title
            _window_history.appendleft({"title": title, "process": process_name})

        return {
            "title": title or "Desktop",
            "process": process_name,
            "pid": pid,
        }
    except Exception:
        return {"title": "unknown", "process": "unknown", "pid": -1}


def get_window_history() -> list[dict]:
    return list(_window_history)


def get_open_windows() -> list[dict]:
    windows = []

    def enum_handler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                name = proc.name()
            except Exception:
                name = "unknown"
            windows.append({"title": title, "process": name})

    win32gui.EnumWindows(enum_handler, None)
    return windows[:20]
