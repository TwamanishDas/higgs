"""
Detects what the user is working on from the active window and generates
contextual help offers — e.g., Sanskrit PDF → translation, code error → review.
"""
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log

# Maps process names (without .exe) to broad activity types
_APP_CONTEXT: dict[str, str] = {
    "code":        "coding",
    "devenv":      "coding",
    "pycharm64":   "coding",
    "pycharm":     "coding",
    "sublime_text":"coding",
    "notepad++":   "coding",
    "rider64":     "coding",
    "idea64":      "coding",
    "cmd":         "terminal",
    "powershell":  "terminal",
    "windowsterminal": "terminal",
    "winword":     "word_processing",
    "excel":       "spreadsheet",
    "powerpnt":    "presentation",
    "onenote":     "note_taking",
    "obsidian":    "note_taking",
    "outlook":     "email",
    "teams":       "communication",
    "slack":       "communication",
    "chrome":      "browsing",
    "msedge":      "browsing",
    "firefox":     "browsing",
    "acrord32":    "pdf_reading",
    "foxitreader": "pdf_reading",
    "sumatrapdf":  "pdf_reading",
    "pdfxcview":   "pdf_reading",
    "vlc":         "media",
    "spotify":     "music",
    "photoshop":   "design",
    "illustrator": "design",
    "figma":       "design",
}

# (regex_pattern, context_type) — checked against window title
_TITLE_RULES: list[tuple[str, str]] = [
    # Indian / Sanskrit languages
    (r"sanskrit|devanagari|vedic|upanishad|gita|rigveda|mahabharata"
     r"|hindi\b|telugu|tamil|kannada|malayalam|bengali|marathi|gujarati"
     r"|urdu|punjabi|odia",
     "indian_language"),

    # Financial
    (r"balance.?sheet|p&l|profit.?loss|invoice|budget|ledger"
     r"|financial.?statement|quarterly.?report|annual.?report",
     "finance"),

    # Code / debugging
    (r"traceback|exception|stacktrace|debug|error.*line \d|\.py\b"
     r"|\.js\b|\.ts\b|\.java\b|\.cs\b|\.cpp\b",
     "code_debugging"),

    # Research / academic
    (r"arxiv|ieee|springer|elsevier|nature\.com|research.?paper"
     r"|literature.?review|abstract|methodology|hypothesis",
     "research_paper"),

    # Legal
    (r"\bcontract\b|\bagreement\b|\bclause\b|\blitigation\b"
     r"|\blegal\b|\bterms.?of.?service\b|\bnda\b",
     "legal_document"),

    # Medical
    (r"\bdiagnosis\b|\bprescription\b|\bclinical\b|\bmedical.?record\b"
     r"|\bsymptom\b|\bpathology\b",
     "medical_document"),

    # Data / analytics
    (r"\bdashboard\b|\banalytics\b|\bpowerbi\b|\btableau\b"
     r"|\bdata.?model\b|\bsql\b|\bquery\b",
     "data_analytics"),
]

# Help message templates keyed by context_type
_HELP: dict[str, dict] = {
    "indian_language": {
        "headline": "Translation Help",
        "message": (
            "It looks like you're reading content in an Indian language. "
            "I can help translate, transliterate, or explain the text."
        ),
        "suggestions": ["Help me translate this", "Explain the meaning", "Dismiss"],
        "level": "low",
    },
    "code_debugging": {
        "headline": "Code Review Mode",
        "message": (
            "Looks like you're debugging or reading code. "
            "I can review logic, explain error messages, or suggest fixes."
        ),
        "suggestions": ["Review this code", "Explain the error", "Dismiss"],
        "level": "low",
    },
    "research_paper": {
        "headline": "Research Assistant",
        "message": (
            "Reading a research paper? I can summarize key findings, "
            "explain terminology, or help find related work."
        ),
        "suggestions": ["Summarize key points", "Explain a concept", "Dismiss"],
        "level": "low",
    },
    "finance": {
        "headline": "Finance Assistant",
        "message": (
            "Working on financial documents? I can help with analysis, "
            "explain accounting terms, or suggest formulas."
        ),
        "suggestions": ["Help with analysis", "Explain a term", "Dismiss"],
        "level": "low",
    },
    "legal_document": {
        "headline": "Legal Doc Assistant",
        "message": (
            "Reading a legal document? I can help explain clauses, "
            "identify key obligations, or simplify complex language."
        ),
        "suggestions": ["Explain this clause", "Summarize document", "Dismiss"],
        "level": "low",
    },
    "medical_document": {
        "headline": "Medical Info Assistant",
        "message": (
            "Reading a medical document? I can explain terminology, "
            "summarize findings, or provide general context."
        ),
        "suggestions": ["Explain this term", "Summarize findings", "Dismiss"],
        "level": "low",
    },
    "data_analytics": {
        "headline": "Data Insights Mode",
        "message": (
            "Working with data or analytics? I can help interpret metrics, "
            "suggest visualizations, or review your query logic."
        ),
        "suggestions": ["Help interpret metrics", "Review query", "Dismiss"],
        "level": "low",
    },
    "pdf_reading": {
        "headline": "PDF Assistant",
        "message": (
            "Reading a PDF? I can help summarize content, translate text, "
            "or explain complex sections."
        ),
        "suggestions": ["Summarize this PDF", "Help me understand", "Dismiss"],
        "level": "low",
    },
}


def detect_context(active_window: dict) -> dict | None:
    """
    Analyse the active window and return a contextual help offer if relevant.
    Returns None when no specific help is available.
    """
    process = (active_window.get("process") or "").lower().replace(".exe", "").strip()
    title   = (active_window.get("title")   or "").strip()

    app_type = _APP_CONTEXT.get(process, "")

    # Title-based pattern matching (most specific)
    for pattern, ctx_type in _TITLE_RULES:
        if re.search(pattern, title, re.IGNORECASE):
            help_msg = _HELP.get(ctx_type)
            if help_msg:
                log.info(
                    f"Contextual help triggered | type={ctx_type} "
                    f"| process={process} | title={title[:50]}"
                )
                return {**help_msg, "context_type": ctx_type, "app_type": app_type}

    # Fallback: app-type based (less specific)
    if app_type == "pdf_reading":
        return {**_HELP["pdf_reading"], "context_type": "pdf_reading", "app_type": app_type}

    return None
