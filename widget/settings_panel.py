import os
import copy
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QSlider, QCheckBox, QTextEdit,
    QFrame, QStackedWidget, QFileDialog, QSpinBox, QScrollArea
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QIntValidator

import config
from widget.characters.pokemon_list import POKEMON

_DARK    = "#0d1117"
_SURFACE = "#161b22"
_RAISED  = "#1c2128"
_BORDER  = "#30363d"
_ACCENT  = "#4a9eff"
_TEXT    = "#e6edf3"
_MUTED   = "#8b949e"
_GREEN   = "#3fb950"
_RED     = "#ff4444"
_ORANGE  = "#ff9a00"

_STYLE = f"""
QWidget {{ background: {_DARK}; color: {_TEXT}; font-family: Segoe UI; font-size: 12px; }}
QFrame#card {{ background: {_SURFACE}; border-radius: 10px; border: 1px solid {_BORDER}; }}
QLineEdit, QTextEdit, QSpinBox, QComboBox {{
    background: {_RAISED}; color: {_TEXT}; border: 1px solid {_BORDER};
    border-radius: 6px; padding: 6px 10px; font-size: 12px;
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {_ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ width: 10px; }}
QComboBox QAbstractItemView {{
    background: {_SURFACE}; color: {_TEXT}; border: 1px solid {_BORDER}; selection-background-color: {_ACCENT};
}}
QPushButton {{
    background: {_ACCENT}; color: white; border: none;
    border-radius: 6px; padding: 7px 16px; font-size: 12px; font-weight: bold;
}}
QPushButton:hover {{ background: #6ab0ff; }}
QPushButton#ghost {{
    background: transparent; color: {_MUTED}; border: 1px solid {_BORDER};
}}
QPushButton#ghost:hover {{ color: {_TEXT}; border-color: {_TEXT}; }}
QPushButton#danger {{ background: {_RED}; }}
QPushButton#danger:hover {{ background: #ff6666; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;
    border: 1px solid {_BORDER}; background: {_RAISED};
}}
QCheckBox::indicator:checked {{ background: {_ACCENT}; border-color: {_ACCENT}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: {_SURFACE}; width: 5px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {_BORDER}; border-radius: 3px; min-height: 20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QLabel#section {{ color: {_ACCENT}; font-size: 11px; font-weight: bold; letter-spacing: 1px; }}
QLabel#hint {{ color: {_MUTED}; font-size: 10px; }}
"""


def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("section")
    return lbl


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("hint")
    lbl.setWordWrap(True)
    return lbl


def _field_row(label: str, widget: QWidget, hint: str = "") -> QVBoxLayout:
    col = QVBoxLayout()
    col.setSpacing(4)
    lbl = QLabel(label)
    lbl.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
    col.addWidget(lbl)
    col.addWidget(widget)
    if hint:
        col.addWidget(_hint(hint))
    return col


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"background: {_BORDER}; border: none; max-height: 1px;")
    return line


class SidebarButton(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(f"  {icon}  {label}", parent)
        self.setCheckable(True)
        self.setFixedHeight(40)
        self._update_style(False)

    def setChecked(self, checked):
        super().setChecked(checked)
        self._update_style(checked)

    def _update_style(self, active: bool):
        if active:
            self.setStyleSheet(f"""
                QPushButton {{ background: {_ACCENT}22; color: {_ACCENT}; border: none;
                border-left: 3px solid {_ACCENT}; border-radius: 0px;
                font-size: 12px; font-weight: bold; text-align: left; padding-left: 12px; }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {_MUTED}; border: none;
                border-left: 3px solid transparent; border-radius: 0px;
                font-size: 12px; text-align: left; padding-left: 12px; }}
                QPushButton:hover {{ color: {_TEXT}; background: {_SURFACE}; }}
            """)


class SettingsPanel(QWidget):
    saved = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(720, 560)
        self.setStyleSheet(_STYLE)
        self._cfg = config.load()
        self._draft = copy.deepcopy(self._cfg)
        self._drag_pos: QPoint | None = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"QFrame#card {{ background: {_DARK}; border-radius: 14px; border: 1px solid {_BORDER}; }}")
        outer.addWidget(card)

        main_row = QHBoxLayout(card)
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet(f"background: {_SURFACE}; border-radius: 14px 0 0 14px; border-right: 1px solid {_BORDER};")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # Sidebar header
        sb_header = QLabel(f"  ◆  Settings")
        sb_header.setFixedHeight(52)
        sb_header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        sb_header.setStyleSheet(f"color: {_ACCENT}; background: {_SURFACE}; border-bottom: 1px solid {_BORDER}; padding-left: 4px;")
        sb_layout.addWidget(sb_header)

        self._nav_btns = []
        nav_items = [
            ("🪪", "Identity"),
            ("✨", "Soul"),
            ("🎮", "Character"),
            ("🛠", "Skills"),
            ("🔗", "Azure AI"),
            ("📁", "Vault"),
            ("🔔", "Notifications"),
            ("📋", "Personal"),
            ("🎭", "Tone"),
        ]
        for i, (icon, label) in enumerate(nav_items):
            btn = SidebarButton(icon, label)
            btn.setChecked(i == 0)
            idx = i
            btn.clicked.connect(lambda _, x=idx: self._switch_page(x))
            sb_layout.addWidget(btn)
            self._nav_btns.append(btn)

        sb_layout.addStretch()

        version_lbl = QLabel("  Desktop Companion v2.0")
        version_lbl.setStyleSheet(f"color: {_MUTED}; font-size: 9px; padding: 8px;")
        sb_layout.addWidget(version_lbl)

        main_row.addWidget(sidebar)

        # ── Content area ──────────────────────────────────────────
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        # Title bar
        title_bar = QFrame()
        title_bar.setFixedHeight(52)
        title_bar.setStyleSheet(f"border-bottom: 1px solid {_BORDER};")
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(20, 0, 12, 0)
        self._page_title = QLabel("Identity")
        self._page_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        tb.addWidget(self._page_title)
        tb.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"background: transparent; color: {_MUTED}; border: none; font-size: 12px;")
        close_btn.clicked.connect(self.hide)
        tb.addWidget(close_btn)
        right.addWidget(title_bar)

        # Pages stack
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_identity())
        self._stack.addWidget(self._page_soul())
        self._stack.addWidget(self._page_character())
        self._stack.addWidget(self._page_skills())
        self._stack.addWidget(self._page_azure())
        self._stack.addWidget(self._page_vault())
        self._stack.addWidget(self._page_notifications())
        self._stack.addWidget(self._page_personal())
        self._stack.addWidget(self._page_tone())
        right.addWidget(self._stack)

        # Bottom bar
        bottom = QFrame()
        bottom.setFixedHeight(54)
        bottom.setStyleSheet(f"border-top: 1px solid {_BORDER};")
        bb = QHBoxLayout(bottom)
        bb.setContentsMargins(20, 8, 20, 8)
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {_GREEN}; font-size: 11px;")
        bb.addWidget(self._status_lbl)
        bb.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("ghost")
        cancel_btn.clicked.connect(self._cancel)
        save_btn = QPushButton("Save & Apply")
        save_btn.clicked.connect(self._save)
        bb.addWidget(cancel_btn)
        bb.addWidget(save_btn)
        right.addWidget(bottom)

        main_row.addLayout(right)

    def _scroll_wrap(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(widget)
        return scroll

    # ── Pages ──────────────────────────────────────────────────────

    def _page_identity(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(_section("Widget Identity"))
        lay.addWidget(_hint("Give your widget a name and personality. This name appears in AI responses and notifications."))
        lay.addWidget(_divider())

        self._name_edit = QLineEdit(self._draft["identity"]["name"])
        lay.addLayout(_field_row("Widget Name", self._name_edit, "e.g. Aria, Max, Nova, Byte"))

        self._tagline_edit = QLineEdit(self._draft["identity"]["tagline"])
        lay.addLayout(_field_row("Tagline", self._tagline_edit, "Short description shown in the title bar"))

        lay.addWidget(_section("Accent Colour"))
        color_row = QHBoxLayout()
        self._color_preview = QLabel()
        self._color_preview.setFixedSize(32, 32)
        self._color_preview.setStyleSheet(f"background: {self._draft['identity']['accent_color']}; border-radius: 6px;")
        self._color_edit = QLineEdit(self._draft["identity"]["accent_color"])
        self._color_edit.setMaximumWidth(120)
        self._color_edit.textChanged.connect(lambda t: self._color_preview.setStyleSheet(f"background: {t}; border-radius: 6px;"))
        color_row.addWidget(self._color_preview)
        color_row.addWidget(self._color_edit)
        color_row.addStretch()
        lay.addLayout(color_row)
        lay.addWidget(_hint("Hex color code — affects glow, rings and notification borders"))

        lay.addStretch()
        return self._scroll_wrap(w)

    def _page_soul(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        # ── Personality ───────────────────────────────────────────────────────
        lay.addWidget(_section("Personality"))
        lay.addWidget(_hint("Choose how your widget communicates. This shapes every AI response."))
        lay.addWidget(_divider())

        self._personality_combo = QComboBox()
        personalities = [
            ("professional", "Professional — precise, data-driven, no fluff"),
            ("friendly",     "Friendly — warm, encouraging, conversational"),
            ("motivational", "Motivational — energetic, uplifting, push-forward"),
            ("calm",         "Calm — zen, minimal, never alarmist"),
            ("witty",        "Witty — sharp, clever, dry wit"),
        ]
        for val, label in personalities:
            self._personality_combo.addItem(label, val)

        current = self._draft["soul"]["personality"]
        for i in range(self._personality_combo.count()):
            if self._personality_combo.itemData(i) == current:
                self._personality_combo.setCurrentIndex(i)
                break

        lay.addLayout(_field_row("Personality Style", self._personality_combo))

        # ── Custom Instructions ────────────────────────────────────────────────
        lay.addWidget(_section("Custom Instructions"))
        lay.addWidget(_hint(
            "Additional instructions added to every AI prompt. "
            "Use this to make the widget aware of your role, preferences, or focus areas."
        ))
        self._custom_edit = QTextEdit()
        self._custom_edit.setPlaceholderText(
            "e.g. I am a software engineer focused on Azure cloud projects. "
            "Remind me to take breaks every 90 minutes. "
            "Always flag if Chrome is using too much memory."
        )
        self._custom_edit.setPlainText(self._draft["soul"].get("custom_instructions", ""))
        self._custom_edit.setFixedHeight(100)
        lay.addWidget(self._custom_edit)

        # ── Soul Viewer (OpenClaw) ─────────────────────────────────────────────
        lay.addWidget(_section("Living Soul  ◆  OpenClaw Identity System"))
        lay.addWidget(_hint(
            "Aria writes her own soul document as she learns about you. "
            "It evolves daily from your activity patterns and is injected into every AI prompt."
        ))
        lay.addWidget(_divider())

        # Status row
        self._soul_status_lbl = QLabel("Loading soul status…")
        self._soul_status_lbl.setStyleSheet(f"color: {_MUTED}; font-size: 10px;")
        self._soul_status_lbl.setWordWrap(True)
        lay.addWidget(self._soul_status_lbl)

        # Auto-evolve toggle
        evolve_row = QHBoxLayout()
        evolve_lbl = QLabel("Auto-evolve daily")
        evolve_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 12px;")
        self._auto_evolve_cb = QCheckBox()
        self._auto_evolve_cb.setChecked(self._draft["soul"].get("auto_evolve", True))
        evolve_row.addWidget(evolve_lbl)
        evolve_row.addStretch()
        evolve_row.addWidget(self._auto_evolve_cb)
        lay.addLayout(evolve_row)
        lay.addWidget(_hint(
            "When enabled, Aria rewrites her soul.md once per day after the daily "
            "activity summary — becoming more tailored to you over time."
        ))

        # Soul content viewer
        self._soul_view = QTextEdit()
        self._soul_view.setReadOnly(True)
        self._soul_view.setPlaceholderText(
            "Soul not yet generated.\n"
            "Start the widget to auto-seed, or click 'Evolve Now' after 5+ scans."
        )
        self._soul_view.setFixedHeight(160)
        self._soul_view.setStyleSheet(f"""
            QTextEdit {{
                background: {_RAISED}; color: {_MUTED};
                border: 1px solid {_BORDER}; border-radius: 6px;
                padding: 8px; font-size: 10px; font-family: Consolas, monospace;
            }}
        """)
        lay.addWidget(self._soul_view)

        # Action buttons
        btn_row = QHBoxLayout()
        evolve_btn = QPushButton("⚡  Evolve Now")
        evolve_btn.setToolTip("Trigger a manual soul evolution (requires 5+ observations)")
        evolve_btn.clicked.connect(self._manual_evolve)
        reset_btn = QPushButton("↺  Reset Soul")
        reset_btn.setObjectName("danger")
        reset_btn.setToolTip("Wipe soul files and revert to seed personality")
        reset_btn.clicked.connect(self._reset_soul)
        btn_row.addWidget(evolve_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # ── Evolution Timeline ────────────────────────────────────────────────
        lay.addWidget(_section("Evolution Timeline"))
        lay.addWidget(_hint(
            "A dated log of how the soul has evolved. Each entry shows what was "
            "observed and learned on that day."
        ))

        self._timeline_view = QTextEdit()
        self._timeline_view.setReadOnly(True)
        self._timeline_view.setPlaceholderText("No evolution history yet.")
        self._timeline_view.setFixedHeight(140)
        self._timeline_view.setStyleSheet(f"""
            QTextEdit {{
                background: {_RAISED}; color: {_MUTED};
                border: 1px solid {_BORDER}; border-radius: 6px;
                padding: 8px; font-size: 10px; font-family: Consolas, monospace;
            }}
        """)
        lay.addWidget(self._timeline_view)

        lay.addStretch()

        # Populate soul viewer on next event loop tick (avoids import-time errors)
        QTimer.singleShot(200, self._refresh_soul_view)

        return self._scroll_wrap(w)

    def _refresh_soul_view(self):
        """Load current soul data into the viewer labels."""
        try:
            from brain import soul_builder
            summary = soul_builder.get_soul_summary()
            if summary["seeded"]:
                self._soul_status_lbl.setText(
                    f"Last evolved: {summary['last_evolved']}  ·  "
                    f"Evolutions: {summary['evolution_count']}  ·  "
                    f"Words: {summary['soul_words']}"
                )
                if summary["soul_full"]:
                    self._soul_view.setPlainText(summary["soul_full"])
                else:
                    self._soul_view.setPlainText("(soul.md is empty)")
            else:
                self._soul_status_lbl.setText("Soul not seeded yet — start the widget to initialise.")

            if hasattr(self, "_timeline_view"):
                entries = soul_builder.get_evolution_timeline()
                if entries:
                    lines = []
                    for e in entries:
                        lines.append(f"[{e['date']}]  {e['label']}")
                        if e["preview"]:
                            lines.append(f"  {e['preview']}")
                        lines.append("")
                    self._timeline_view.setPlainText("\n".join(lines).strip())
                else:
                    self._timeline_view.setPlainText("No evolution history yet.")
        except Exception as e:
            self._soul_status_lbl.setText(f"Could not load soul: {e}")

    def _manual_evolve(self):
        """Trigger a manual soul evolution in a background thread."""
        try:
            from brain import soul_builder, memory as brain_memory
            import threading

            self._soul_status_lbl.setText("Evolving… this may take 10-20 seconds.")
            cfg = config.load()

            def _worker():
                obs      = brain_memory.get_recent_observations(days=1)
                patterns = brain_memory.get_patterns()
                ok       = soul_builder.evolve(obs, patterns, cfg)
                # Refresh UI on main thread via a short-delay timer trick
                from PyQt6.QtCore import QTimer as _QT
                _QT.singleShot(0, lambda: self._after_evolve(ok))

            threading.Thread(target=_worker, daemon=True).start()
        except Exception as e:
            self._soul_status_lbl.setText(f"Evolve failed: {e}")

    def _after_evolve(self, ok: bool):
        if ok:
            self._soul_status_lbl.setText("Soul evolved successfully ✓")
            self._refresh_soul_view()
        else:
            self._soul_status_lbl.setText(
                "Evolution skipped — not enough observations yet, or already ran today."
            )

    def _reset_soul(self):
        """Wipe soul files and refresh the viewer."""
        try:
            from brain import soul_builder
            soul_builder.reset()
            self._soul_view.setPlainText("")
            self._soul_status_lbl.setText(
                "Soul reset. Restart the widget to re-seed from your current settings."
            )
        except Exception as e:
            self._soul_status_lbl.setText(f"Reset failed: {e}")

    def _page_character(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(_section("Character Type"))
        lay.addWidget(_hint("Choose the visual style of your desktop widget."))
        lay.addWidget(_divider())

        char_cfg = self._draft.get("character", {})

        self._char_type_combo = QComboBox()
        self._char_type_combo.addItem("🔵  Orb (default animated orb)", "orb")
        self._char_type_combo.addItem("🎮  Pokémon (animated sprite)", "pokemon")
        current_type = char_cfg.get("type", "orb")
        self._char_type_combo.setCurrentIndex(0 if current_type == "orb" else 1)
        self._char_type_combo.currentIndexChanged.connect(self._on_char_type_changed)
        lay.addLayout(_field_row("Widget Style", self._char_type_combo))

        # Pokemon section (shown only when pokemon selected)
        self._pokemon_section = QFrame()
        ps_lay = QVBoxLayout(self._pokemon_section)
        ps_lay.setContentsMargins(0, 0, 0, 0)
        ps_lay.setSpacing(12)

        ps_lay.addWidget(_section("Choose Your Pokémon"))
        ps_lay.addWidget(_hint(
            "Animated Gen 1–4 sprites are downloaded automatically on first use "
            "and cached locally in the sprites/ folder."
        ))

        self._pokemon_combo = QComboBox()
        for pid, pname in POKEMON:
            self._pokemon_combo.addItem(f"#{pid:03d}  {pname}", pid)
        current_id = char_cfg.get("pokemon_id", 25)
        for i in range(self._pokemon_combo.count()):
            if self._pokemon_combo.itemData(i) == current_id:
                self._pokemon_combo.setCurrentIndex(i)
                break
        ps_lay.addLayout(_field_row("Pokémon", self._pokemon_combo,
                                     "Sprites are sourced from the PokeAPI sprite repository"))

        self._shiny_cb = QCheckBox("  Use Shiny sprite ✨")
        self._shiny_cb.setChecked(char_cfg.get("shiny", False))
        self._shiny_cb.setStyleSheet(f"color: {_TEXT}; font-size: 12px;")
        ps_lay.addWidget(self._shiny_cb)

        # Mood preview table
        ps_lay.addWidget(_section("Mood → Sprite Mapping"))
        mood_info = [
            ("IDLE / HAPPY / INFO",      "Front animated sprite, normal"),
            ("THINKING / ANALYZING",     "Front sprite with blue tint"),
            ("ALERT / ERROR",            "Front sprite with red pulse"),
            ("WARNING",                  "Front sprite with orange tint"),
            ("SLEEPING",                 "Back animated sprite, dimmed"),
            ("BUSY",                     "Front sprite with spinner ring"),
        ]
        for mood, desc in mood_info:
            row = QHBoxLayout()
            mood_lbl = QLabel(mood)
            mood_lbl.setFixedWidth(200)
            mood_lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 10px; font-weight: bold;")
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {_MUTED}; font-size: 10px;")
            row.addWidget(mood_lbl)
            row.addWidget(desc_lbl)
            row.addStretch()
            ps_lay.addLayout(row)

        lay.addWidget(self._pokemon_section)
        self._pokemon_section.setVisible(current_type == "pokemon")

        lay.addStretch()
        return self._scroll_wrap(w)

    def _on_char_type_changed(self, idx: int):
        self._pokemon_section.setVisible(idx == 1)

    def _page_skills(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(_section("Active Skills"))
        lay.addWidget(_hint("Toggle which capabilities are active. Disabled skills are skipped during scans."))
        lay.addWidget(_divider())

        skills_cfg = self._draft["skills"]
        self._skill_checks = {}

        skill_defs = [
            ("system_monitor", "🖥  System Monitor",
             "Tracks CPU, RAM, disk and network. Alerts on high usage."),
            ("window_tracker", "🪟  Window Tracker",
             "Watches your active window and recent app history."),
            ("calendar",       "🗓  NLP Calendar",
             "Schedule events through natural language in chat — Aria asks probe questions "
             "and delivers agenda + prep notes at event time."),
            ("obsidian_notes", "📝  Obsidian Notes",
             "Feeds recent note content to the AI for contextual awareness."),
            ("ai_brain",       "🧠  AI Brain",
             "Sends context to Azure GPT-4o for insights and suggestions. Disabling turns off all AI calls."),
            ("context_help",   "💡  Contextual Help",
             "Detects what you're working on (PDF, code, language) and offers relevant assistance."),
            ("memory",         "🧬  Memory & Learning",
             "Stores daily activity, learns usage patterns, and auto-builds character traits over time."),
            ("office_reader",  "📄  Office Reader",
             "Reads content from open Excel, Word, and PowerPoint files via COM automation — "
             "no add-ins needed. AI scans reference your actual data, not just the window title."),
            ("browser_reader", "🌐  Browser Reader",
             "Reads the active browser tab via Chrome DevTools Protocol. "
             "Requires Chrome/Edge launched with --remote-debugging-port=9222 (see below)."),
        ]

        for key, label, desc in skill_defs:
            row_frame = QFrame()
            row_frame.setObjectName("card")
            row_frame.setStyleSheet(f"QFrame#card {{ background: {_SURFACE}; border-radius: 8px; border: 1px solid {_BORDER}; }}")
            row_lay = QHBoxLayout(row_frame)
            row_lay.setContentsMargins(14, 10, 14, 10)

            text_col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 12))
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {_MUTED}; font-size: 10px;")
            text_col.addWidget(lbl)
            text_col.addWidget(desc_lbl)
            row_lay.addLayout(text_col)
            row_lay.addStretch()

            cb = QCheckBox()
            cb.setChecked(skills_cfg.get(key, True))
            row_lay.addWidget(cb)
            self._skill_checks[key] = cb
            lay.addWidget(row_frame)

        # ── Browser Reader setup instructions ────────────────────────────────
        lay.addWidget(_divider())
        lay.addWidget(_section("Browser Reader Setup"))
        lay.addWidget(_hint(
            "To enable browser reading, launch Chrome or Edge with the remote debugging flag.\n"
            "Copy one of the commands below, paste it into Run (Win+R) or a terminal, and press Enter.\n"
            "You only need to do this once — Higgs detects the port automatically."
        ))

        chrome_cmd = (
            r'"C:\Program Files\Google\Chrome\Application\chrome.exe" '
            r'--remote-debugging-port=9222 --restore-last-session'
        )
        edge_cmd = (
            r'"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" '
            r'--remote-debugging-port=9222 --restore-last-session'
        )

        for browser_name, cmd in [("Chrome", chrome_cmd), ("Edge", edge_cmd)]:
            cmd_frame = QFrame()
            cmd_frame.setObjectName("card")
            cmd_frame.setStyleSheet(
                f"QFrame#card {{ background: {_RAISED}; border-radius: 8px; border: 1px solid {_BORDER}; }}"
            )
            cmd_lay = QVBoxLayout(cmd_frame)
            cmd_lay.setContentsMargins(12, 8, 12, 8)
            cmd_lay.setSpacing(4)

            hdr = QLabel(f"{browser_name} launch command:")
            hdr.setStyleSheet(f"color: {_MUTED}; font-size: 10px; font-weight: bold;")
            cmd_lay.addWidget(hdr)

            cmd_edit = QLineEdit(cmd)
            cmd_edit.setReadOnly(True)
            cmd_edit.setStyleSheet(
                f"background: {_DARK}; color: {_GREEN}; "
                f"font-family: Consolas, monospace; font-size: 9px; "
                f"border: none; padding: 4px 6px;"
            )
            cmd_lay.addWidget(cmd_edit)
            lay.addWidget(cmd_frame)

        lay.addStretch()
        return self._scroll_wrap(w)

    def _page_azure(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(_section("Azure OpenAI Connection"))
        lay.addWidget(_hint("Credentials for your Azure OpenAI deployment. These are stored locally in config.json."))
        lay.addWidget(_divider())

        az = self._draft["azure"]

        self._az_endpoint = QLineEdit(az["endpoint"])
        lay.addLayout(_field_row("Endpoint", self._az_endpoint,
                                  "e.g. https://myresource.openai.azure.com/"))

        self._az_key = QLineEdit(az["api_key"])
        self._az_key.setEchoMode(QLineEdit.EchoMode.Password)
        key_row_widget = QWidget()
        key_row = QHBoxLayout(key_row_widget)
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.addWidget(self._az_key)
        show_btn = QPushButton("👁")
        show_btn.setFixedSize(34, 34)
        show_btn.setObjectName("ghost")
        show_btn.setCheckable(True)
        show_btn.toggled.connect(lambda c: self._az_key.setEchoMode(
            QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password))
        key_row.addWidget(show_btn)
        lay.addLayout(_field_row("API Key", key_row_widget))

        self._az_deployment = QLineEdit(az["deployment"])
        lay.addLayout(_field_row("Deployment Name", self._az_deployment,
                                  "The name of your deployed model in Azure AI Foundry"))

        self._az_version = QLineEdit(az.get("api_version", "2024-12-01-preview"))
        lay.addLayout(_field_row("API Version", self._az_version,
                                  "e.g. 2024-12-01-preview"))

        lay.addStretch()
        return self._scroll_wrap(w)

    def _page_vault(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(_section("Obsidian Vault"))
        lay.addWidget(_hint("Point to your Obsidian vault folder. The widget reads .md files for tasks and notes."))
        lay.addWidget(_divider())

        vault = self._draft["vault"]

        path_widget = QWidget()
        path_row = QHBoxLayout(path_widget)
        path_row.setContentsMargins(0, 0, 0, 0)
        self._vault_path = QLineEdit(vault["path"])
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("ghost")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_vault)
        path_row.addWidget(self._vault_path)
        path_row.addWidget(browse_btn)
        lay.addLayout(_field_row("Vault Path", path_widget))

        self._max_files = QSpinBox()
        self._max_files.setRange(1, 30)
        self._max_files.setValue(vault["max_context_files"])
        lay.addLayout(_field_row("Max Notes in AI Context", self._max_files,
                                  "How many recent .md files to include in each AI scan"))

        lay.addWidget(_hint(
            "The vault path is used for Obsidian Notes context. "
            "Task reminders have been replaced by the NLP Calendar — "
            "just type 'schedule a meeting…' in the chat."
        ))

        lay.addStretch()
        return self._scroll_wrap(w)

    def _page_personal(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(_section("Personal Context"))
        lay.addWidget(_hint(
            "Tell the widget about yourself — your role, goals, preferences, or anything "
            "you want it to always remember. This is injected into every AI prompt, "
            "similar to Claude's or Gemini's memory feature."
        ))
        lay.addWidget(_divider())

        self._personal_edit = QTextEdit()
        self._personal_edit.setPlaceholderText(
            "e.g. I am a software engineer at a fintech startup. I mostly work in Python "
            "and Azure. I prefer concise, actionable advice. My current focus is shipping "
            "the payments feature by end of quarter."
        )
        self._personal_edit.setMinimumHeight(220)
        lay.addWidget(self._personal_edit)

        btn_row = QHBoxLayout()
        import_btn = QPushButton("📂  Import .md / .txt")
        import_btn.setObjectName("ghost")
        import_btn.clicked.connect(self._import_personal_info)
        save_personal_btn = QPushButton("💾  Save")
        save_personal_btn.clicked.connect(self._save_personal_info)
        btn_row.addWidget(import_btn)
        btn_row.addWidget(save_personal_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addWidget(_hint(
            "Stored in memory/personal_info.md. Takes effect on the next AI scan. "
            "Import replaces the current content with the file you choose."
        ))
        lay.addStretch()

        QTimer.singleShot(200, self._load_personal_info)
        return self._scroll_wrap(w)

    def _page_tone(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(_section("Character Style"))
        lay.addWidget(_hint(
            "Choose how the AI speaks to you. Select a primary style, optionally blend "
            "a second style, and adjust temperature to control creativity vs. focus."
        ))
        lay.addWidget(_divider())

        tone_cfg = self._draft.get("tone", {})

        # ── Tone cards (2-column grid) ────────────────────────────────────────
        _TONE_DEFS = [
            ("default",      "🤖", "Default",       "Neutral, clear, and balanced."),
            ("friendly",     "😊", "Friendly",       "Warm, chatty, conversational, light wit."),
            ("professional", "💼", "Professional",   "Polished, formal, precise. Business-ready."),
            ("candid",       "🎯", "Candid",         "Direct, honest, no small talk. Risk-first."),
            ("quirky",       "🎭", "Quirky",         "Playful, humorous, creative metaphors."),
            ("efficient",    "⚡", "Efficient",      "Concise and plain. Immediate answers only."),
            ("nerdy",        "🔬", "Nerdy",          "Deep-dive, curious, highly detailed."),
            ("cynical",      "😒", "Cynical",        "Dry, sarcastic, blunt wit."),
        ]

        self._tone_cards: dict[str, QPushButton] = {}
        current_style = tone_cfg.get("style", "default")

        grid_widget = QWidget()
        grid = QHBoxLayout()
        grid.setSpacing(8)
        col_left  = QVBoxLayout()
        col_left.setSpacing(8)
        col_right = QVBoxLayout()
        col_right.setSpacing(8)

        for i, (key, icon, name, desc) in enumerate(_TONE_DEFS):
            card = QPushButton()
            card.setCheckable(True)
            card.setChecked(key == current_style)
            card.setFixedHeight(60)
            card.setProperty("tone_key", key)

            card_inner = QVBoxLayout(card)
            card_inner.setContentsMargins(10, 6, 10, 6)
            card_inner.setSpacing(2)
            title_lbl = QLabel(f"{icon}  {name}")
            title_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 12px; font-weight: bold; background: transparent;")
            desc_lbl  = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {_MUTED}; font-size: 10px; background: transparent;")
            card_inner.addWidget(title_lbl)
            card_inner.addWidget(desc_lbl)

            self._tone_cards[key] = card
            card.clicked.connect(lambda _, k=key: self._on_tone_selected(k))
            self._apply_tone_card_style(card, key == current_style)

            if i % 2 == 0:
                col_left.addLayout(card_inner.parent().layout() if False else QVBoxLayout())
                col_left.itemAt(col_left.count() - 1).layout().deleteLater()
                col_left.addWidget(card)
            else:
                col_right.addWidget(card)

        grid.addLayout(col_left)
        grid.addLayout(col_right)
        grid_widget.setLayout(grid)
        lay.addWidget(grid_widget)

        # ── Blend ─────────────────────────────────────────────────────────────
        lay.addWidget(_section("Blend (Optional)"))
        lay.addWidget(_hint("Mix a secondary style into the primary. 0% = pure primary, 50% = equal mix."))

        blend_row = QHBoxLayout()
        self._blend_combo = QComboBox()
        self._blend_combo.addItem("None", "")
        for key, icon, name, _ in _TONE_DEFS:
            self._blend_combo.addItem(f"{icon}  {name}", key)
        current_blend = tone_cfg.get("blend_style", "")
        for i in range(self._blend_combo.count()):
            if self._blend_combo.itemData(i) == current_blend:
                self._blend_combo.setCurrentIndex(i)
                break
        blend_row.addWidget(self._blend_combo)

        self._blend_weight_lbl = QLabel(f"{tone_cfg.get('blend_weight', 30)}%")
        self._blend_weight_lbl.setFixedWidth(36)
        self._blend_weight_lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 12px; font-weight: bold;")
        self._blend_slider = QSlider(Qt.Orientation.Horizontal)
        self._blend_slider.setRange(0, 100)
        self._blend_slider.setValue(tone_cfg.get("blend_weight", 30))
        self._blend_slider.valueChanged.connect(
            lambda v: self._blend_weight_lbl.setText(f"{v}%")
        )
        blend_row.addWidget(self._blend_slider)
        blend_row.addWidget(self._blend_weight_lbl)
        lay.addLayout(blend_row)

        # ── Temperature ───────────────────────────────────────────────────────
        lay.addWidget(_section("Temperature"))
        lay.addWidget(_hint(
            "Low = focused, consistent, predictable.  "
            "High = creative, varied, more expressive."
        ))

        temp_row = QHBoxLayout()
        focused_lbl = QLabel("Focused")
        focused_lbl.setStyleSheet(f"color: {_MUTED}; font-size: 10px;")
        creative_lbl = QLabel("Creative")
        creative_lbl.setStyleSheet(f"color: {_MUTED}; font-size: 10px;")

        self._temp_val_lbl = QLabel(f"{tone_cfg.get('temperature', 70)}")
        self._temp_val_lbl.setFixedWidth(30)
        self._temp_val_lbl.setStyleSheet(f"color: {_ACCENT}; font-size: 12px; font-weight: bold;")
        self._temp_slider = QSlider(Qt.Orientation.Horizontal)
        self._temp_slider.setRange(0, 100)
        self._temp_slider.setValue(tone_cfg.get("temperature", 70))
        self._temp_slider.valueChanged.connect(
            lambda v: self._temp_val_lbl.setText(str(v))
        )

        temp_row.addWidget(focused_lbl)
        temp_row.addWidget(self._temp_slider)
        temp_row.addWidget(creative_lbl)
        temp_row.addWidget(self._temp_val_lbl)
        lay.addLayout(temp_row)

        # Preset hints below slider
        preset_row = QHBoxLayout()
        for label, val in [("Deterministic", 10), ("Balanced", 50), ("Default", 70), ("Creative", 85), ("Wild", 95)]:
            btn = QPushButton(f"{label} ({val})")
            btn.setObjectName("ghost")
            btn.setFixedHeight(24)
            btn.setStyleSheet(btn.styleSheet() + "font-size: 9px; padding: 2px 6px;")
            btn.clicked.connect(lambda _, v=val: (self._temp_slider.setValue(v)))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        lay.addLayout(preset_row)

        lay.addStretch()
        return self._scroll_wrap(w)

    def _apply_tone_card_style(self, card: QPushButton, active: bool):
        if active:
            card.setStyleSheet(f"""
                QPushButton {{
                    background: {_ACCENT}22; border: 1.5px solid {_ACCENT};
                    border-radius: 8px; text-align: left;
                }}
            """)
        else:
            card.setStyleSheet(f"""
                QPushButton {{
                    background: {_SURFACE}; border: 1px solid {_BORDER};
                    border-radius: 8px; text-align: left;
                }}
                QPushButton:hover {{ border-color: {_ACCENT}88; background: {_RAISED}; }}
            """)

    def _on_tone_selected(self, selected_key: str):
        for key, card in self._tone_cards.items():
            card.setChecked(key == selected_key)
            self._apply_tone_card_style(card, key == selected_key)

    def _page_notifications(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addWidget(_section("Notification Behaviour"))
        lay.addWidget(_hint("Control how often and how long notifications appear. Increase cooldowns to reduce interruptions."))
        lay.addWidget(_divider())

        notif = self._draft["notifications"]

        self._scan_cooldown = QSpinBox()
        self._scan_cooldown.setRange(60, 3600)
        self._scan_cooldown.setSuffix(" seconds")
        self._scan_cooldown.setValue(notif["scan_cooldown_seconds"])
        lay.addLayout(_field_row("AI Scan Notification Cooldown", self._scan_cooldown,
                                  "Minimum time between AI insight popups (default 300s = 5 min)"))

        self._reminder_cooldown = QSpinBox()
        self._reminder_cooldown.setRange(300, 86400)
        self._reminder_cooldown.setSuffix(" seconds")
        self._reminder_cooldown.setValue(notif["reminder_cooldown_seconds"])
        lay.addLayout(_field_row("Task Reminder Cooldown", self._reminder_cooldown,
                                  "How long before the same task reminder can reappear (default 3600s = 1 hr)"))

        self._display_duration = QSpinBox()
        self._display_duration.setRange(3, 60)
        self._display_duration.setSuffix(" seconds")
        self._display_duration.setValue(notif["display_duration_seconds"])
        lay.addLayout(_field_row("Popup Display Duration", self._display_duration,
                                  "How long each notification stays on screen"))

        lay.addWidget(_section("Scan Interval"))
        self._scan_interval = QSpinBox()
        self._scan_interval.setRange(10, 600)
        self._scan_interval.setSuffix(" seconds")
        self._scan_interval.setValue(self._draft["awareness"]["scan_interval_seconds"])
        lay.addLayout(_field_row("AI Scan Interval", self._scan_interval,
                                  "How often the widget runs a full system + AI scan"))

        lay.addStretch()
        return self._scroll_wrap(w)

    def _load_personal_info(self):
        try:
            from brain import soul_builder
            self._personal_edit.setPlainText(soul_builder.get_personal_info())
        except Exception:
            pass

    def _import_personal_info(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Personal Info",
            os.path.expanduser("~"),
            "Markdown & Text Files (*.md *.txt);;All Files (*)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._personal_edit.setPlainText(f.read())
                self._status_lbl.setText("File imported — click Save to apply")
            except Exception as e:
                self._status_lbl.setText(f"Import failed: {e}")

    def _save_personal_info(self):
        try:
            from brain import soul_builder
            soul_builder.save_personal_info(self._personal_edit.toPlainText().strip())
            self._status_lbl.setText("✓ Personal info saved")
        except Exception as e:
            self._status_lbl.setText(f"Save failed: {e}")

    # ── Actions ────────────────────────────────────────────────────

    def _switch_page(self, idx: int):
        titles = ["Identity", "Soul", "Character", "Skills", "Azure AI", "Vault", "Notifications", "Personal Info", "Tone & Style"]
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)
        self._stack.setCurrentIndex(idx)
        self._page_title.setText(titles[idx])
        if idx == 1:
            QTimer.singleShot(50, self._refresh_soul_view)
        if idx == 7:
            QTimer.singleShot(50, self._load_personal_info)

    def _browse_vault(self):
        path = QFileDialog.getExistingDirectory(self, "Select Obsidian Vault Folder",
                                                 self._vault_path.text() or os.path.expanduser("~"))
        if path:
            self._vault_path.setText(path.replace("/", "\\"))

    def _collect(self):
        self._draft["identity"]["name"] = self._name_edit.text().strip() or "Aria"
        self._draft["identity"]["tagline"] = self._tagline_edit.text().strip()
        self._draft["identity"]["accent_color"] = self._color_edit.text().strip()
        self._draft["soul"]["personality"] = self._personality_combo.currentData()
        self._draft["soul"]["custom_instructions"] = self._custom_edit.toPlainText().strip()
        self._draft["soul"]["auto_evolve"] = self._auto_evolve_cb.isChecked()
        if "character" not in self._draft:
            self._draft["character"] = {}
        self._draft["character"]["type"] = self._char_type_combo.currentData()
        self._draft["character"]["pokemon_id"] = self._pokemon_combo.currentData()
        self._draft["character"]["shiny"] = self._shiny_cb.isChecked()
        for key, cb in self._skill_checks.items():
            self._draft["skills"][key] = cb.isChecked()
        self._draft["azure"]["endpoint"] = self._az_endpoint.text().strip()
        self._draft["azure"]["api_key"] = self._az_key.text().strip()
        self._draft["azure"]["deployment"] = self._az_deployment.text().strip()
        self._draft["azure"]["api_version"] = self._az_version.text().strip()
        self._draft["vault"]["path"] = self._vault_path.text().strip()
        self._draft["vault"]["max_context_files"] = self._max_files.value()
        self._draft["notifications"]["scan_cooldown_seconds"] = self._scan_cooldown.value()
        self._draft["notifications"]["reminder_cooldown_seconds"] = self._reminder_cooldown.value()
        self._draft["notifications"]["display_duration_seconds"] = self._display_duration.value()
        self._draft["awareness"]["scan_interval_seconds"] = self._scan_interval.value()
        if hasattr(self, "_tone_cards"):
            selected = next((k for k, c in self._tone_cards.items() if c.isChecked()), "default")
            if "tone" not in self._draft:
                self._draft["tone"] = {}
            self._draft["tone"]["style"]        = selected
            self._draft["tone"]["blend_style"]  = self._blend_combo.currentData() or ""
            self._draft["tone"]["blend_weight"] = self._blend_slider.value()
            self._draft["tone"]["temperature"]  = self._temp_slider.value()

    def _save(self):
        self._collect()
        config.save(self._draft)
        self._cfg = copy.deepcopy(self._draft)
        try:
            from brain import azure_client
            azure_client.update_tone(self._draft.get("tone", {}))
        except Exception:
            pass
        self._status_lbl.setText("✓ Saved — restart to apply all changes")
        self.saved.emit(self._draft)

    def _cancel(self):
        self._draft = copy.deepcopy(self._cfg)
        self.hide()

    def reload(self):
        self._cfg = config.load()
        self._draft = copy.deepcopy(self._cfg)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
