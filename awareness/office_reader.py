"""
awareness/office_reader.py
Reads content from open Office applications (Excel, Word, PowerPoint)
using Win32 COM automation — zero add-ins, zero user configuration.

Requires: pywin32 (already in requirements.txt via win32gui usage)
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log

# Cache: avoids re-reading the same app within CACHE_TTL seconds
_CACHE_TTL = 30  # seconds
_cache: dict = {}   # {"process": (timestamp, data_dict)}


def _is_cached(process: str) -> bool:
    if process in _cache:
        ts, _ = _cache[process]
        if time.time() - ts < _CACHE_TTL:
            return True
    return False


def _get_cached(process: str) -> dict | None:
    if process in _cache:
        _, data = _cache[process]
        return data
    return None


def _set_cache(process: str, data: dict | None):
    _cache[process] = (time.time(), data)


# ── Excel ────────────────────────────────────────────────────────────────────

def read_excel() -> dict | None:
    """
    Attaches to a running Excel instance via COM and reads the active selection.
    Falls back to UsedRange if selection is a single cell or too large.
    Returns a dict ready to embed in the AI context, or None if Excel isn't open.
    """
    key = "excel.exe"
    if _is_cached(key):
        log.info("office_reader: using cached Excel data")
        return _get_cached(key)

    try:
        import win32com.client
        import pywintypes

        xl = win32com.client.GetActiveObject("Excel.Application")
        wb = xl.ActiveWorkbook
        if wb is None:
            _set_cache(key, None)
            return None

        ws = xl.ActiveSheet
        sel = xl.Selection

        MAX_R, MAX_C = 30, 20

        # Decide what range to read
        try:
            sel_rows = sel.Rows.Count
            sel_cols = sel.Columns.Count
            use_selection = (sel_rows * sel_cols > 1) and (sel_rows <= MAX_R) and (sel_cols <= MAX_C)
        except Exception:
            use_selection = False

        if use_selection:
            rng = sel
        else:
            # Fall back to used range capped at MAX_R × MAX_C
            ur = ws.UsedRange
            rng = ws.Range(
                ws.Cells(ur.Row, ur.Column),
                ws.Cells(
                    min(ur.Row + ur.Rows.Count - 1, ur.Row + MAX_R - 1),
                    min(ur.Column + ur.Columns.Count - 1, ur.Column + MAX_C - 1),
                )
            )

        row_count = rng.Rows.Count
        col_count = rng.Columns.Count

        # Pull values and formulas
        raw_vals = rng.Value
        raw_fmls = rng.Formula

        # Normalise to list-of-lists (COM returns a tuple-of-tuples, or a scalar for 1×1)
        def normalise(raw, r, c):
            if r == 1 and c == 1:
                return [[raw]]
            if r == 1:
                return [list(raw)]
            return [list(row) for row in raw]

        values   = normalise(raw_vals, row_count, col_count)
        formulas = normalise(raw_fmls, row_count, col_count)

        # Convert COM types to plain Python
        def clean_val(v):
            if v is None:
                return None
            try:
                import pywintypes as pwt
                if isinstance(v, pwt.TimeType):
                    return str(v)
            except Exception:
                pass
            return v

        values   = [[clean_val(v) for v in row] for row in values]
        formulas = [[str(f) if f else "" for f in row] for row in formulas]

        result = {
            "app":        "excel",
            "workbook":   wb.Name,
            "sheet":      ws.Name,
            "address":    rng.Address,
            "row_count":  row_count,
            "col_count":  col_count,
            "values":     values,
            "formulas":   formulas,
        }

        _set_cache(key, result)
        log.info(f"office_reader: Excel read OK | {ws.Name} {rng.Address} ({row_count}×{col_count})")
        return result

    except Exception as e:
        # pywintypes.com_error is the expected failure when Excel isn't open
        if "com_error" not in type(e).__name__.lower() and "dispatch" not in str(e).lower():
            log.warning(f"office_reader: Excel read error — {e}")
        _set_cache(key, None)
        return None


# ── Word ─────────────────────────────────────────────────────────────────────

def read_word() -> dict | None:
    """
    Attaches to a running Word instance via COM and reads the active document text.
    Returns up to 2000 chars of body text plus any current selection.
    """
    key = "winword.exe"
    if _is_cached(key):
        log.info("office_reader: using cached Word data")
        return _get_cached(key)

    try:
        import win32com.client

        wd = win32com.client.GetActiveObject("Word.Application")
        doc = wd.ActiveDocument
        if doc is None:
            _set_cache(key, None)
            return None

        MAX_CHARS = 2000

        full_text = (doc.Content.Text or "").strip()
        char_count = len(full_text)
        body_text = full_text[:MAX_CHARS]
        if len(full_text) > MAX_CHARS:
            body_text += "…"

        # Get selected text if any
        sel_text = ""
        try:
            sel = wd.Selection
            sel_text = (sel.Text or "").strip()
            if sel_text == full_text:
                sel_text = ""   # whole-doc selection is noise
        except Exception:
            pass

        result = {
            "app":        "word",
            "document":   doc.Name,
            "char_count": char_count,
            "text":       body_text,
            "selection":  sel_text[:500] if sel_text else "",
        }

        _set_cache(key, result)
        log.info(f"office_reader: Word read OK | {doc.Name} ({char_count} chars)")
        return result

    except Exception as e:
        if "com_error" not in type(e).__name__.lower():
            log.warning(f"office_reader: Word read error — {e}")
        _set_cache(key, None)
        return None


# ── PowerPoint ───────────────────────────────────────────────────────────────

def read_powerpoint() -> dict | None:
    """
    Attaches to a running PowerPoint instance via COM and reads the active slide text.
    """
    key = "powerpnt.exe"
    if _is_cached(key):
        log.info("office_reader: using cached PowerPoint data")
        return _get_cached(key)

    try:
        import win32com.client

        ppt = win32com.client.GetActiveObject("PowerPoint.Application")
        prs = ppt.ActivePresentation
        if prs is None:
            _set_cache(key, None)
            return None

        slide_count = prs.Slides.Count
        slide_num = 1
        try:
            slide_num = ppt.ActiveWindow.View.Slide.SlideIndex
        except Exception:
            pass

        slide = prs.Slides(slide_num)

        # Collect text from all shapes on the slide
        texts = []
        for shape in slide.Shapes:
            try:
                if shape.HasTextFrame:
                    t = shape.TextFrame.TextRange.Text.strip()
                    if t:
                        texts.append(t)
            except Exception:
                pass

        slide_text = " | ".join(texts)[:1500]

        result = {
            "app":           "powerpoint",
            "presentation":  prs.Name,
            "slide_number":  slide_num,
            "slide_count":   slide_count,
            "slide_text":    slide_text,
        }

        _set_cache(key, result)
        log.info(f"office_reader: PPT read OK | {prs.Name} slide {slide_num}/{slide_count}")
        return result

    except Exception as e:
        if "com_error" not in type(e).__name__.lower():
            log.warning(f"office_reader: PowerPoint read error — {e}")
        _set_cache(key, None)
        return None


# ── Router ───────────────────────────────────────────────────────────────────

_PROCESS_MAP = {
    "excel.exe":    read_excel,
    "winword.exe":  read_word,
    "powerpnt.exe": read_powerpoint,
}


def read_active_office(process_name: str) -> dict | None:
    """
    Routes to the correct reader based on the active process name.
    Returns None if the process isn't a supported Office app.
    """
    key = (process_name or "").lower().strip()
    reader = _PROCESS_MAP.get(key)
    if reader is None:
        return None
    return reader()
