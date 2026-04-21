"""
awareness/browser_reader.py
Reads the active browser tab (URL, title, and optional page text) via
Chrome DevTools Protocol (CDP).

Works with Chrome AND Edge — both support CDP on the same port.

SETUP (one-time):
  Launch Chrome with: chrome.exe --remote-debugging-port=9222
  Or Edge with:       msedge.exe --remote-debugging-port=9222

  Higgs detects the port automatically. If it's not open, the browser
  section is simply omitted from the AI context (no error shown).

Requires: websocket-client (added to requirements.txt)
"""

import socket
import json
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log

_DEBUG_PORT = 9222
_CACHE_TTL  = 20   # seconds — browser content changes more often than Office docs
_cache: dict = {}  # {"browser": (timestamp, data_dict)}


def _is_cached() -> bool:
    if "browser" in _cache:
        ts, _ = _cache["browser"]
        if time.time() - ts < _CACHE_TTL:
            return True
    return False


def _get_cached() -> dict | None:
    if "browser" in _cache:
        _, data = _cache["browser"]
        return data
    return None


def _set_cache(data: dict | None):
    _cache["browser"] = (time.time(), data)


# ── Port check ───────────────────────────────────────────────────────────────

def is_debug_port_open(port: int = _DEBUG_PORT) -> bool:
    """Fast TCP probe — returns True if something is listening on the debug port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    result = s.connect_ex(("127.0.0.1", port))
    s.close()
    return result == 0


# ── Tab listing ──────────────────────────────────────────────────────────────

def get_active_tab(port: int = _DEBUG_PORT) -> dict | None:
    """
    Fetches /json from the CDP endpoint and returns the first non-devtools tab.
    Returns {"url": str, "title": str, "ws_url": str} or None.
    """
    try:
        import urllib.request
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/json", timeout=2
        ) as resp:
            tabs = json.loads(resp.read())

        for tab in tabs:
            tab_type = tab.get("type", "")
            url = tab.get("url", "")
            # Skip devtools, extensions, and blank tabs
            if tab_type != "page":
                continue
            if url.startswith("devtools://") or url.startswith("chrome-extension://"):
                continue
            if url in ("", "about:blank", "chrome://newtab/"):
                continue
            return {
                "url":    url,
                "title":  tab.get("title", ""),
                "ws_url": tab.get("webSocketDebuggerUrl", ""),
            }
    except Exception as e:
        log.debug(f"browser_reader: tab listing failed — {e}")
    return None


# ── Page text via websocket ───────────────────────────────────────────────────

def get_page_text(ws_url: str, max_chars: int = 2000) -> str | None:
    """
    Connects to a tab's CDP websocket and evaluates document.body.innerText.
    Returns trimmed text (up to max_chars) or None if anything fails.
    """
    if not ws_url:
        return None
    try:
        import websocket  # websocket-client package

        ws = websocket.create_connection(ws_url, timeout=3)
        msg_id = 1

        # Send Runtime.evaluate
        cmd = json.dumps({
            "id":     msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression":    "document.body ? document.body.innerText : ''",
                "returnByValue": True,
            }
        })
        ws.send(cmd)

        # Read until we get our response (skip events)
        for _ in range(10):
            raw = ws.recv()
            resp = json.loads(raw)
            if resp.get("id") == msg_id:
                text = resp.get("result", {}).get("result", {}).get("value", "")
                ws.close()
                # Collapse whitespace and trim
                text = " ".join(text.split())
                return text[:max_chars]

        ws.close()
    except ImportError:
        log.warning("browser_reader: websocket-client not installed — pip install websocket-client")
    except Exception as e:
        log.debug(f"browser_reader: page text extraction failed — {e}")
    return None


# ── Main entry point ─────────────────────────────────────────────────────────

def read_browser(port: int = _DEBUG_PORT, include_page_text: bool = True) -> dict | None:
    """
    Reads the active browser tab.
    Returns {"app": "browser", "url": str, "title": str, "page_text": str|None}
    or None if the debug port isn't open.
    """
    if _is_cached():
        log.info("browser_reader: using cached browser data")
        return _get_cached()

    if not is_debug_port_open(port):
        # Silently skip — this is normal when Chrome isn't in debug mode
        return None

    tab = get_active_tab(port)
    if tab is None:
        _set_cache(None)
        return None

    page_text = None
    if include_page_text and tab["ws_url"]:
        page_text = get_page_text(tab["ws_url"])

    result = {
        "app":       "browser",
        "url":       tab["url"],
        "title":     tab["title"],
        "page_text": page_text,
    }

    _set_cache(result)
    log.info(f"browser_reader: read OK | {tab['title'][:60]} | text={'yes' if page_text else 'no'}")
    return result


# ── Chrome/Edge launcher helper ──────────────────────────────────────────────

def get_chrome_launch_command() -> str:
    """Returns the recommended Chrome launch command for copy-paste."""
    return (
        r'"C:\Program Files\Google\Chrome\Application\chrome.exe" '
        r'--remote-debugging-port=9222 --restore-last-session'
    )


def get_edge_launch_command() -> str:
    """Returns the recommended Edge launch command for copy-paste."""
    return (
        r'"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" '
        r'--remote-debugging-port=9222 --restore-last-session'
    )
