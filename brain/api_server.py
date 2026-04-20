"""
Local REST API server — bridges the Excel Office Add-in with the Python backend.
Serves add-in HTML/JS files and receives Excel selection data + chat messages.
Runs as a daemon thread inside the main process.
"""
import json
import struct
import threading
import zlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log

# Lazy Flask import so startup doesn't fail if flask isn't installed yet
_flask_app = None

ADDIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "office_addin"
)

# Shared state
_excel_context: dict = {}
_on_excel_context_cb = None   # set by main.py — called on main thread via Qt signal
_on_chat_message_cb  = None   # set by main.py


# ── Tiny PNG generator (no Pillow needed) ────────────────────────────────────

def _make_png(size: int, r: int, g: int, b: int) -> bytes:
    """Generate a solid-colour PNG of given size."""
    def chunk(name: bytes, data: bytes) -> bytes:
        c = name + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    rows  = b"".join(b"\x00" + bytes([r, g, b] * size) for _ in range(size))
    ihdr  = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def _ensure_icons():
    """Create placeholder icon PNGs in office_addin/ if they don't exist."""
    os.makedirs(ADDIN_DIR, exist_ok=True)
    for size, fname in [(16, "icon16.png"), (32, "icon32.png"), (80, "icon80.png")]:
        path = os.path.join(ADDIN_DIR, fname)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(_make_png(size, 74, 158, 255))   # #4a9eff blue


# ── Flask app factory ─────────────────────────────────────────────────────────

def _build_app():
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS

    app = Flask(__name__)
    CORS(app)

    @app.route("/addin/<path:filename>")
    def serve_addin(filename):
        return send_from_directory(ADDIN_DIR, filename)

    @app.route("/api/excel/selection", methods=["POST"])
    def receive_excel_selection():
        global _excel_context
        data = request.get_json(force=True) or {}
        _excel_context = data
        sheet = data.get("sheet", "")
        addr  = data.get("address", "")
        log.info(f"Excel selection received | sheet={sheet} | addr={addr}")
        if _on_excel_context_cb:
            _on_excel_context_cb(data)
        return jsonify({"status": "ok"})

    @app.route("/api/chat", methods=["POST"])
    def receive_chat():
        data    = request.get_json(force=True) or {}
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"error": "empty message"}), 400
        if _on_chat_message_cb:
            _on_chat_message_cb(message, _excel_context.copy())
        return jsonify({"status": "processing"})

    @app.route("/api/excel/context", methods=["GET"])
    def get_excel_context():
        return jsonify(_excel_context)

    @app.route("/api/ping")
    def ping():
        return jsonify({"status": "ok", "service": "aria-companion"})

    return app


# ── Public API ────────────────────────────────────────────────────────────────

def init(on_excel_context=None, on_chat_message=None):
    global _on_excel_context_cb, _on_chat_message_cb
    _on_excel_context_cb = on_excel_context
    _on_chat_message_cb  = on_chat_message


def start(port: int = 5050):
    global _flask_app
    _ensure_icons()
    _flask_app = _build_app()

    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    def _run():
        _flask_app.run(
            host      = "127.0.0.1",
            port      = port,
            debug     = False,
            use_reloader = False,
        )

    t = threading.Thread(target=_run, daemon=True, name="api-server")
    t.start()
    log.info(f"API server started on http://127.0.0.1:{port}")
